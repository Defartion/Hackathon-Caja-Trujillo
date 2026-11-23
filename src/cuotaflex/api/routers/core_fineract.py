"""Espejo del core simulado de CuotaFlex en Apache Fineract."""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ...agente import MESES_ES
from ...config import desglose_cronograma, tea_a_tem
from ...integraciones.fineract import (
    FineractClient,
    FineractError,
    fecha_fineract,
    periodos_reembolso,
    url_api,
)

router = APIRouter(prefix="/core", tags=["fineract"])
RUTA_IDS = Path(__file__).resolve().parents[4] / "infra/fineract/ids.json"
# El core reinicia sus IDs al arrancar. Un identificador por proceso evita colisiones.
_instancia = uuid4().hex
_escritura_espejo = Lock()
_centimo = Decimal("0.01")


def _prestamo_simulado(loan_id: int) -> tuple[dict, dict]:
    from ..main import DB

    prestamo = DB["loans"].get(loan_id)
    if prestamo is None:
        raise HTTPException(404, "Préstamo simulado no encontrado.")
    cliente = DB["clients"].get(prestamo["clientId"])
    if cliente is None:
        raise HTTPException(404, "Cliente simulado no encontrado.")
    return {**prestamo, "cuotas": tuple(prestamo["cuotas"])}, cliente


def _ids() -> tuple[int, int, int]:
    try:
        datos = json.loads(RUTA_IDS.read_text(encoding="utf-8"))
        return int(datos["officeId"]), int(datos["staffId"]), int(datos["productId"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(503, "Ejecuta scripts/seed_fineract.py para preparar Fineract.") from exc


def _comparacion(simulado: dict, fino: dict) -> dict:
    cuotas = simulado["cuotas"]
    cronograma = fino["repaymentSchedule"]
    periodos = periodos_reembolso(cronograma)
    if [fila["period"] for fila in periodos] != list(range(1, len(cuotas) + 1)):
        raise FineractError("El plazo del cronograma de Fineract difiere del simulado.")
    filas = []
    for cuota, periodo in zip(cuotas, periodos):
        real = periodo["totalDueForPeriod"]
        diferencia = abs(Decimal(str(cuota)) - Decimal(str(real))).quantize(_centimo)
        filas.append(
            {
                "periodo": periodo["period"],
                "simulado": cuota,
                "fineract": real,
                "diferencia": float(diferencia),
            }
        )

    detalle_simulado = desglose_cronograma(simulado["principal"], tea_a_tem(simulado["tea"]), cuotas)
    return {
        "simuladoLoanId": simulado["id"],
        "fineractLoanId": fino["id"],
        "fineractClientId": fino["clientId"],
        "estadoSimulado": simulado["status"]["value"],
        "estadoFineract": fino["status"]["value"],
        "diferenciaMaxima": max((fila["diferencia"] for fila in filas), default=0.0),
        "diferenciaMaximaSinUltima": max((fila["diferencia"] for fila in filas[:-1]), default=0.0),
        "cuotas": filas,
        "cronogramaSimulado": detalle_simulado,
        "cronogramaFineract": cronograma,
    }


def _error_core(exc: FineractError) -> HTTPException:
    status = 503 if exc.status_code in {None, 401, 403, 503} else 502
    return HTTPException(status, str(exc))


@router.get("/estado")
def estado_fineract():
    url = None
    try:
        if configurada := os.environ.get("FINERACT_URL"):
            url = url_api(configurada)
        with FineractClient.desde_entorno() as client:
            return {"fineract": "conectado", "version": client.estado(), "url": url}
    except FineractError:
        return {"fineract": "no disponible", "version": None, "url": url}


@router.post("/espejo/{loan_id}")
def crear_espejo(loan_id: int):
    with _escritura_espejo:
        simulado, cliente = _prestamo_simulado(loan_id)
        office_id, staff_id, product_id = _ids()
        loan_external_id = f"cf-{_instancia}-prestamo-{loan_id}"
        try:
            with FineractClient.desde_entorno() as client:
                fino = client.buscar_prestamo(loan_external_id)
                if fino is None:
                    fino = _crear_prestamo(client, simulado, cliente, office_id, staff_id, product_id, loan_external_id)
                return _actualizar_espejo(client, simulado, fino)
        except FineractError as exc:
            raise _error_core(exc) from exc


def _fecha_desembolso(simulado: dict, hoy: date) -> date:
    # El core guarda el mes inicial, sin año. Usamos el último mes de desembolso posible.
    cronograma = simulado.get("propuesta", {}).get("cronograma")
    primer_mes = cronograma[0].get("mes") if cronograma else None
    if primer_mes not in MESES_ES:
        return hoy
    mes_desembolso = (MESES_ES.index(primer_mes) - 1) % 12 + 1
    anio = hoy.year - (mes_desembolso > hoy.month)
    return date(anio, mes_desembolso, 1)


def _crear_prestamo(client, simulado, cliente, office_id, staff_id, product_id, loan_external_id):
    hoy = date.today()
    fecha = _fecha_desembolso(simulado, hoy)
    client_external_id = f"cf-{_instancia}-cliente-{cliente['id']}"
    existente = client.buscar_cliente(client_external_id)
    if existente is None:
        oficina = client.request("GET", f"/offices/{office_id}")
        apertura = fecha_fineract(oficina["openingDate"])
        activacion = max(apertura, date(hoy.year - 1, 1, 1))
        client_id = client.crear_cliente(
            {
                "officeId": office_id,
                "staffId": staff_id,
                "fullname": cliente["nombre"],
                "legalFormId": 1,  # Persona natural.
                "active": True,
                "activationDate": activacion,
                "externalId": client_external_id,
            }
        )
    else:
        client_id = existente["id"]
    fino_id = client.crear_prestamo(
        client_id,
        product_id,
        simulado["principal"],
        simulado["numberOfRepayments"],
        simulado["tea"],
        fecha,
        external_id=loan_external_id,
        loan_officer_id=staff_id,
    )
    return client.obtener_prestamo(fino_id)


def _actualizar_espejo(client: FineractClient, simulado: dict, fino: dict) -> dict:
    comparacion = _comparacion(simulado, fino)
    estado = fino["status"]
    esperado = simulado["status"]["value"]
    fino_id = fino["id"]
    fecha = fecha_fineract(fino["timeline"]["expectedDisbursementDate"])

    variar = estado["pendingApproval"] and comparacion["diferenciaMaximaSinUltima"] > 0
    aprobar = estado["pendingApproval"] and esperado in {"Approved", "Active"}
    desembolsar = esperado == "Active" and (aprobar or estado["waitingForDisbursal"])
    if variar:
        client.agregar_variaciones(fino_id, simulado["cuotas"])
    if aprobar:
        client.aprobar(fino_id, fecha)
    if desembolsar:
        client.desembolsar(fino_id, fecha)
    if variar or aprobar or desembolsar:
        return _comparacion(simulado, client.obtener_prestamo(fino_id))
    return comparacion


@router.get("/espejo/{loan_id}")
def ver_espejo(loan_id: int):
    simulado, _ = _prestamo_simulado(loan_id)
    try:
        with FineractClient.desde_entorno() as client:
            fino = client.buscar_prestamo(f"cf-{_instancia}-prestamo-{loan_id}")
            if fino is None:
                raise HTTPException(404, "El préstamo simulado aún no tiene espejo.")
            return _comparacion(simulado, fino)
    except FineractError as exc:
        raise _error_core(exc) from exc
