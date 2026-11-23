"""Prepara la oficina, el asesor y el producto de CuotaFlex en Fineract."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cuotaflex.config import cargar_parametros, tea_a_tem  # noqa: E402
from cuotaflex.integraciones.fineract import FineractClient, FineractError  # noqa: E402

ARCHIVO_IDS = RAIZ / "infra" / "fineract" / "ids.json"
ASESOR_EXTERNO = "cuotaflex-asesor-demo"
PRODUCTO_EXTERNO = "cuotaflex-microempresa"
PRODUCTO_NOMBRE = "CuotaFlex Microempresa"
DIAS_MINIMOS = 5
DIAS_MAXIMOS = 90


def _activar_pen(client: FineractClient) -> None:
    monedas = client.request("GET", "/currencies")
    habilitadas = [moneda["code"] for moneda in monedas["selectedCurrencyOptions"]]
    if "PEN" not in habilitadas:
        client.request("PUT", "/currencies", json={"currencies": [*habilitadas, "PEN"]})


def _asesor(client: FineractClient, oficina_id: int) -> int:
    personal = client.request("GET", "/staff", params={"officeId": oficina_id, "status": "all"})
    asesor = next((persona for persona in personal if persona.get("externalId") == ASESOR_EXTERNO), None)
    if asesor is not None:
        if not (asesor["isActive"] and asesor["isLoanOfficer"]):
            raise ValueError("El asesor CuotaFlex existente debe estar activo y habilitado para préstamos.")
        return int(asesor["id"])

    asesor_creado = client.request(
        "POST",
        "/staff",
        json={
            "officeId": oficina_id,
            "firstname": "Asesor",
            "lastname": "CuotaFlex",
            "externalId": ASESOR_EXTERNO,
            "isLoanOfficer": True,
            "isActive": True,
            "joiningDate": date.today().isoformat(),
            "locale": "en",
            "dateFormat": "yyyy-MM-dd",
        },
    )
    return int(asesor_creado["resourceId"])


def _producto(client: FineractClient) -> int:
    productos = client.request("GET", "/loanproducts")
    producto = next(
        (
            item
            for item in productos
            if item.get("externalId") == PRODUCTO_EXTERNO or item["name"] == PRODUCTO_NOMBRE
        ),
        None,
    )
    if producto is not None:
        if not (
            producto["currency"]["code"] == "PEN"
            and producto["currency"]["decimalPlaces"] == 2
            and producto["allowVariableInstallments"]
            and producto["minimumGap"] == DIAS_MINIMOS
            and producto["maximumGap"] == DIAS_MAXIMOS
            and producto["interestType"]["id"] == 0
            and producto["amortizationType"]["id"] == 1
            and producto["interestCalculationPeriodType"]["id"] == 1
            and producto["interestRateFrequencyType"]["id"] == 2
            and producto["repaymentFrequencyType"]["id"] == 2
        ):
            raise ValueError("El producto CuotaFlex existente tiene una configuración incompatible.")
        return int(producto["id"])

    credito = cargar_parametros()["credito"]
    producto_creado = client.request(
        "POST",
        "/loanproducts",
        json={
            "name": PRODUCTO_NOMBRE,
            "shortName": "CFMX",
            "externalId": PRODUCTO_EXTERNO,
            "description": "Crédito de demostración con cuotas mensuales variables en soles.",
            "locale": "en",
            "currencyCode": "PEN",
            "digitsAfterDecimal": 2,
            "inMultiplesOf": 0,
            "principal": 10000,
            "numberOfRepayments": credito["plazos_meses"][0],
            "repaymentEvery": 1,
            "repaymentFrequencyType": 2,  # Meses.
            "interestRatePerPeriod": round(100 * tea_a_tem(credito["tea_base"]), 8),
            "interestRateFrequencyType": 2,  # Tasa efectiva mensual.
            "interestType": 0,  # Saldo decreciente.
            "amortizationType": 1,  # Cuota francesa antes de aplicar las variaciones.
            "interestCalculationPeriodType": 1,  # Mismo periodo que el pago.
            "allowPartialPeriodInterestCalcualtion": True,  # Nombre de la API 1.12.1.
            "daysInMonthType": 30,
            "daysInYearType": 360,
            "isInterestRecalculationEnabled": False,
            "transactionProcessingStrategyCode": "mifos-standard-strategy",
            "loanScheduleType": "CUMULATIVE",
            "loanScheduleProcessingType": "HORIZONTAL",
            "accountingRule": 1,  # Sin contabilidad para esta demostración.
            "allowVariableInstallments": True,
            "minimumGap": DIAS_MINIMOS,
            "maximumGap": DIAS_MAXIMOS,
        },
    )
    return int(producto_creado["resourceId"])


def sembrar(client: FineractClient) -> dict[str, int]:
    """Reutiliza los datos de demostración ya registrados en el tenant."""
    oficinas = client.request("GET", "/offices")
    oficina = next((item for item in oficinas if item.get("hierarchy") == "."), None)
    if oficina is None:
        raise ValueError("Fineract no devolvió la oficina principal del tenant.")
    oficina_id = int(oficina["id"])
    _activar_pen(client)
    return {
        "officeId": oficina_id,
        "staffId": _asesor(client, oficina_id),
        "productId": _producto(client),
    }


def _guardar_ids(ids: dict[str, int], destino: Path) -> None:
    archivo = NamedTemporaryFile(mode="w", encoding="utf-8", dir=destino.parent, delete=False)
    temporal = Path(archivo.name)
    try:
        with archivo:
            json.dump(ids, archivo, indent=2)
            archivo.write("\n")
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)


def main() -> int:
    try:
        with FineractClient.desde_entorno() as client:
            ids = sembrar(client)
        _guardar_ids(ids, ARCHIVO_IDS)
    except (FineractError, ValueError, OSError) as error:
        print(f"No se pudo preparar Fineract: {error}", file=sys.stderr)
        return 1
    print(f"IDs de CuotaFlex guardados en {ARCHIVO_IDS}")
    print(json.dumps(ids, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
