"""Cliente HTTP para Apache Fineract 1.12.1."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import date
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import uuid4

import httpx

from ..config import tea_a_tem

API_PATH = "/fineract-provider/api/v1"
FECHA = {"dateFormat": "yyyy-MM-dd", "locale": "en"}
ASOCIACIONES = {"associations": "repaymentSchedule"}


class FineractError(Exception):
    def __init__(self, mensaje: str, status_code: int | None = None):
        super().__init__(mensaje)
        self.status_code = status_code


def url_api(base_url: str) -> str:
    try:
        url = urlsplit(base_url.strip())
        url.port  # Valida el puerto antes de crear el cliente HTTP.
    except ValueError as exc:
        raise FineractError("FINERACT_URL no es válida.") from exc
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.query
        or url.fragment
    ):
        raise FineractError("FINERACT_URL debe ser una URL HTTP(S) sin credenciales.")
    ruta = url.path.rstrip("/")
    if ruta.endswith("/fineract-provider"):
        ruta += "/api/v1"
    elif not ruta.endswith("/api/v1"):
        ruta += API_PATH
    return urlunsplit((url.scheme, url.netloc, ruta, "", ""))


def fecha_fineract(valor: str | list[int]) -> date:
    """Fineract suele devolver LocalDate como un arreglo [año, mes, día]."""
    if isinstance(valor, str):
        return date.fromisoformat(valor)
    return date(*valor)


def periodos_reembolso(cronograma: dict) -> list[dict]:
    """La fila de desembolso carece de número de cuota."""
    return [fila for fila in cronograma["periods"] if (fila.get("period") or 0) > 0]


class FineractClient:
    def __init__(
        self,
        base_url: str,
        tenant: str,
        usuario: str,
        clave: str,
        verify_ssl: bool,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = url_api(base_url)
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"Fineract-Platform-TenantId": tenant, "Accept": "application/json"},
            auth=(usuario, clave),
            verify=verify_ssl,
            timeout=15.0,
            transport=transport,
        )

    @classmethod
    def desde_entorno(cls) -> FineractClient:
        variables = ("FINERACT_URL", "FINERACT_TENANT", "FINERACT_USER", "FINERACT_PASSWORD")
        url, tenant, usuario, clave = (os.environ.get(variable) for variable in variables)
        if not all((url, tenant, usuario, clave)):
            faltantes = ", ".join(variable for variable in variables if not os.environ.get(variable))
            raise FineractError(f"Falta configurar {faltantes}.")
        verify = os.environ.get("FINERACT_VERIFY_SSL", "true").strip().lower()
        if verify not in {"true", "false", "1", "0"}:
            raise FineractError("FINERACT_VERIFY_SSL debe ser true, false, 1 o 0.")
        return cls(url, tenant, usuario, clave, verify in {"true", "1"})

    def __enter__(self) -> FineractClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._http.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> Any:
        # La misma clave evita duplicar un comando si se pierde la primera respuesta.
        headers = {"Idempotency-Key": str(uuid4())} if method.upper() in {"POST", "PUT", "DELETE"} else {}
        for intento in range(2):
            try:
                respuesta = self._http.request(method, path, params=params, json=json, headers=headers)
                break
            except httpx.TransportError as exc:
                if intento == 1:
                    raise FineractError("No se pudo conectar con Fineract.") from exc

        try:
            cuerpo = respuesta.json() if respuesta.content else {}
        except ValueError as exc:
            if respuesta.is_success:
                raise FineractError("Fineract devolvió una respuesta que no es JSON.") from exc
            cuerpo = {}

        if not respuesta.is_success:
            cuerpo = cuerpo if isinstance(cuerpo, dict) else {}
            mensajes = [
                error["defaultUserMessage"]
                for error in (cuerpo.get("errors") or [])
                if isinstance(error, dict) and error.get("defaultUserMessage")
            ]
            mensaje = "; ".join(mensajes) or cuerpo.get("defaultUserMessage") or respuesta.reason_phrase
            raise FineractError(f"Fineract HTTP {respuesta.status_code}: {mensaje}", respuesta.status_code)
        return cuerpo

    def estado(self) -> str | None:
        self.request("GET", "/offices")
        try:
            info_url = self.base_url.removesuffix("/api/v1") + "/actuator/info"
            info = self.request("GET", info_url)
            git = info.get("git") or {}
            etiqueta = (git.get("closest") or {}).get("tag") or {}
            if str((etiqueta.get("commit") or {}).get("count")) == "0":
                return etiqueta.get("name")
            return (info.get("build") or {}).get("version") or (git.get("build") or {}).get("version")
        except FineractError:
            return None

    def crear_cliente(self, datos: dict) -> int:
        cuerpo = {**FECHA, **datos}
        for campo in ("activationDate", "submittedOnDate"):
            if isinstance(cuerpo.get(campo), date):
                cuerpo[campo] = cuerpo[campo].isoformat()
        return int(self.request("POST", "/clients", json=cuerpo)["clientId"])

    def crear_prestamo(
        self,
        client_id: int,
        product_id: int,
        principal: float,
        plazo: int,
        tea: float,
        fecha_desembolso: date,
        *,
        external_id: str | None = None,
        fecha_primera_cuota: date | None = None,
        loan_officer_id: int | None = None,
    ) -> int:
        cuerpo = {
            **FECHA,
            "clientId": client_id,
            "productId": product_id,
            "loanType": "individual",
            "principal": principal,
            "loanTermFrequency": plazo,
            "loanTermFrequencyType": 2,
            "numberOfRepayments": plazo,
            "repaymentEvery": 1,
            "repaymentFrequencyType": 2,
            "interestRatePerPeriod": round(100 * tea_a_tem(tea), 10),
            "interestType": 0,
            "interestCalculationPeriodType": 1,
            "amortizationType": 1,
            "transactionProcessingStrategyCode": "mifos-standard-strategy",
            "expectedDisbursementDate": fecha_desembolso.isoformat(),
            "submittedOnDate": fecha_desembolso.isoformat(),
        }
        if external_id is not None:
            cuerpo["externalId"] = external_id
        if fecha_primera_cuota is not None:
            cuerpo["repaymentsStartingFromDate"] = fecha_primera_cuota.isoformat()
        if loan_officer_id is not None:
            cuerpo["loanOfficerId"] = loan_officer_id
        return int(self.request("POST", "/loans", json=cuerpo)["loanId"])

    def calcular_cronograma(self, loan_id: int) -> dict:
        """Pide a Fineract una vista previa para un préstamo pendiente de aprobación."""
        return self.request(
            "POST",
            f"/loans/{loan_id}/schedule",
            params={"command": "calculateLoanSchedule"},
            json={**FECHA, "exceptions": {}},
        )

    def agregar_variaciones(self, loan_id: int, cuotas: Sequence[float]) -> dict:
        cronograma = self.obtener_prestamo(loan_id)["repaymentSchedule"]
        periodos = periodos_reembolso(cronograma)
        if [periodo["period"] for periodo in periodos] != list(range(1, len(cuotas) + 1)):
            raise FineractError("El plazo del cronograma de Fineract difiere del simulado.")
        cambios = [
            {
                "dueDate": fecha_fineract(periodo["dueDate"]).isoformat(),
                "installmentAmount": float(cuota),
            }
            for periodo, cuota in zip(periodos[:-1], cuotas[:-1])
        ]
        if not cambios:
            return {}
        return self.request(
            "POST",
            f"/loans/{loan_id}/schedule",
            params={"command": "addVariations"},
            json={**FECHA, "exceptions": {"modifiedinstallments": cambios}},
        )

    def eliminar_variaciones(self, loan_id: int) -> dict:
        return self.request(
            "POST", f"/loans/{loan_id}/schedule", params={"command": "deleteVariations"}, json={}
        )

    def aprobar(self, loan_id: int, fecha: date) -> dict:
        return self._comando_prestamo(loan_id, "approve", {"approvedOnDate": fecha.isoformat()})

    def desembolsar(self, loan_id: int, fecha: date) -> dict:
        return self._comando_prestamo(loan_id, "disburse", {"actualDisbursementDate": fecha.isoformat()})

    def _comando_prestamo(self, loan_id: int, comando: str, datos: dict) -> dict:
        return self.request("POST", f"/loans/{loan_id}", params={"command": comando}, json={**FECHA, **datos})

    def pagar(self, loan_id: int, monto: float, fecha: date) -> dict:
        return self.request(
            "POST",
            f"/loans/{loan_id}/transactions",
            params={"command": "repayment"},
            json={**FECHA, "transactionAmount": monto, "transactionDate": fecha.isoformat()},
        )

    def obtener_prestamo(self, loan_id: int) -> dict:
        return self.request("GET", f"/loans/{loan_id}", params=ASOCIACIONES)

    def buscar_cliente(self, external_id: str) -> dict | None:
        return self._buscar("clients", external_id)

    def buscar_prestamo(self, external_id: str) -> dict | None:
        return self._buscar("loans", external_id, ASOCIACIONES)

    def _buscar(self, recurso: str, external_id: str, params: dict | None = None) -> dict | None:
        try:
            return self.request("GET", f"/{recurso}/external-id/{quote(external_id, safe='')}", params=params)
        except FineractError as exc:
            if exc.status_code != 404:
                raise
            return None
