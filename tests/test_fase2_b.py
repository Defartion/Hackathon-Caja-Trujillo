"""Pruebas del espejo de CuotaFlex con Apache Fineract 1.12.1."""
from __future__ import annotations

import json
import os
import runpy
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from cuotaflex.api import main as api
from cuotaflex.api.routers import core_fineract
from cuotaflex.config import tea_a_tem
from cuotaflex.datos import PERFILES
from cuotaflex.integraciones.fineract import FineractClient, FineractError

BASE = "https://fineract.test/fineract-provider/api/v1"
FECHA = date(2026, 11, 23)
FECHA_FORMATO = {"locale": "en", "dateFormat": "yyyy-MM-dd"}


def _cliente(transport: httpx.MockTransport) -> FineractClient:
    return FineractClient(BASE, "demo", "asesor", "clave", False, transport=transport)


@pytest.fixture
def api_cuotaflex(monkeypatch):
    monkeypatch.setattr(api, "DB", {"clients": {}, "loans": {}})
    with TestClient(api.app) as cliente:
        yield cliente


def test_cliente_envia_autenticacion_y_parametros_de_prestamo():
    enviados = []

    def responder(solicitud):
        assert solicitud.headers["Fineract-Platform-TenantId"] == "demo"
        assert solicitud.headers["Authorization"] == "Basic YXNlc29yOmNsYXZl"
        assert solicitud.extensions["timeout"]["read"] == 15
        assert solicitud.method == "POST"
        enviados.append((str(solicitud.url), json.loads(solicitud.content)))
        id_recurso = 20 + len(enviados)
        campo_id = "clientId" if solicitud.url.path.endswith("/clients") else "loanId"
        return httpx.Response(200, json={campo_id: id_recurso, "resourceId": id_recurso})

    datos_cliente = {
        "officeId": 1,
        "legalFormId": 1,
        "firstname": "Rosa",
        "lastname": "Salazar",
        "active": True,
        "activationDate": FECHA,
    }
    with _cliente(httpx.MockTransport(responder)) as cliente:
        assert cliente.crear_cliente(datos_cliente) == 21
        assert cliente.crear_prestamo(
            21, 4, 6000, 12, 0.35, FECHA,
            external_id="cuotaflex-demo-1", fecha_primera_cuota=date(2026, 12, 23),
        ) == 22

    url_cliente, cuerpo_cliente = enviados[0]
    assert url_cliente == f"{BASE}/clients"
    assert cuerpo_cliente == {**datos_cliente, **FECHA_FORMATO, "activationDate": "2026-11-23"}

    url_prestamo, cuerpo_prestamo = enviados[1]
    assert url_prestamo == f"{BASE}/loans"
    tasa = cuerpo_prestamo.pop("interestRatePerPeriod")
    assert float(tasa) == pytest.approx(100 * tea_a_tem(0.35))
    campos = {
        **FECHA_FORMATO,
        "clientId": 21,
        "productId": 4,
        "principal": 6000,
        "loanType": "individual",
        "loanTermFrequency": 12,
        "loanTermFrequencyType": 2,
        "numberOfRepayments": 12,
        "repaymentEvery": 1,
        "repaymentFrequencyType": 2,
        "interestType": 0,
        "amortizationType": 1,
        "interestCalculationPeriodType": 1,
        "transactionProcessingStrategyCode": "mifos-standard-strategy",
        "submittedOnDate": "2026-11-23",
        "expectedDisbursementDate": "2026-11-23",
        "repaymentsStartingFromDate": "2026-12-23",
        "externalId": "cuotaflex-demo-1",
    }
    assert {clave: cuerpo_prestamo[clave] for clave in campos} == campos


def test_variaciones_usan_vencimiento_original_y_dejan_que_fineract_calcule_la_ultima():
    cronograma = {"periods": [
        {"dueDate": [2026, 11, 23], "principalDisbursed": 6000},
        {"period": 1, "dueDate": [2026, 12, 23], "totalDueForPeriod": 500},
        {"period": 2, "dueDate": [2027, 1, 23], "totalDueForPeriod": 500},
        {"period": 3, "dueDate": [2027, 2, 23], "totalDueForPeriod": 500},
    ]}
    comandos = []

    def responder(solicitud):
        if solicitud.method == "GET":
            assert solicitud.url.path.endswith("/loans/37")
            assert "repaymentSchedule" in solicitud.url.params["associations"].split(",")
            return httpx.Response(200, json={"id": 37, "repaymentSchedule": cronograma})
        assert solicitud.method == "POST"
        assert solicitud.url.path.endswith("/loans/37/schedule")
        comando = solicitud.url.params["command"]
        comandos.append((comando, json.loads(solicitud.content)))
        return httpx.Response(200, json=cronograma if comando == "calculateLoanSchedule" else {"loanId": 37})

    with _cliente(httpx.MockTransport(responder)) as cliente:
        assert cliente.calcular_cronograma(37) == cronograma
        cliente.agregar_variaciones(37, [380.25, 570.50, 601.21])
        cliente.eliminar_variaciones(37)

    assert comandos == [
        ("calculateLoanSchedule", {**FECHA_FORMATO, "exceptions": {}}),
        ("addVariations", {
            **FECHA_FORMATO,
            "exceptions": {"modifiedinstallments": [
                {"dueDate": "2026-12-23", "installmentAmount": 380.25},
                {"dueDate": "2027-01-23", "installmentAmount": 570.50},
            ]},
        }),
        ("deleteVariations", {}),
    ]


def test_aprobacion_desembolso_y_pago_envian_los_campos_de_fecha_de_fineract():
    enviados = []

    def responder(solicitud):
        assert solicitud.method == "POST"
        enviados.append((
            solicitud.url.path, solicitud.url.params["command"], json.loads(solicitud.content),
        ))
        return httpx.Response(200, json={"loanId": 37, "resourceId": 42})

    with _cliente(httpx.MockTransport(responder)) as cliente:
        cliente.aprobar(37, FECHA)
        cliente.desembolsar(37, FECHA)
        cliente.pagar(37, 380.25, FECHA)

    raiz = "/fineract-provider/api/v1/loans/37"
    assert enviados == [
        (raiz, "approve", {**FECHA_FORMATO, "approvedOnDate": "2026-11-23"}),
        (raiz, "disburse", {**FECHA_FORMATO, "actualDisbursementDate": "2026-11-23"}),
        (f"{raiz}/transactions", "repayment", {
            **FECHA_FORMATO, "transactionDate": "2026-11-23", "transactionAmount": 380.25,
        }),
    ]


def test_error_de_fineract_conserva_sus_mensajes_en_una_sola_solicitud():
    solicitudes = []

    def responder(solicitud):
        solicitudes.append(solicitud)
        return httpx.Response(400, json={
            "defaultUserMessage": "Failed data validation rules.",
            "errors": [
                {"defaultUserMessage": "Client is not active."},
                {"defaultUserMessage": "Principal exceeds the product maximum."},
            ],
        })

    with _cliente(httpx.MockTransport(responder)) as cliente:
        with pytest.raises(FineractError) as error:
            cliente.crear_prestamo(21, 4, 6000, 12, 0.35, FECHA)
    assert "Client is not active." in str(error.value)
    assert "Principal exceeds the product maximum." in str(error.value)
    assert len(solicitudes) == 1


def test_error_de_red_reintenta_una_mutacion_con_la_misma_clave():
    solicitudes = []

    def responder(solicitud):
        solicitudes.append(solicitud)
        if len(solicitudes) == 1:
            raise httpx.ConnectError("Conexión interrumpida", request=solicitud)
        return httpx.Response(200, json={"loanId": 37})

    with _cliente(httpx.MockTransport(responder)) as cliente:
        cliente.desembolsar(37, FECHA)
    primera, segunda = solicitudes
    assert primera.content == segunda.content
    assert primera.headers["Idempotency-Key"] == segunda.headers["Idempotency-Key"]


def test_estado_no_disponible_con_fineract_apagado(api_cuotaflex, monkeypatch):
    monkeypatch.setenv("FINERACT_URL", BASE)

    def sin_servidor(solicitud):
        raise httpx.ConnectError("Conexión rechazada", request=solicitud)

    monkeypatch.setattr(
        core_fineract.FineractClient, "desde_entorno",
        lambda: _cliente(httpx.MockTransport(sin_servidor)),
    )
    estado = api_cuotaflex.get("/core/estado")

    assert estado.status_code == 200, estado.text
    estado = estado.json()
    assert estado["fineract"] == "no disponible"
    assert estado["version"] is None
    assert estado["url"] == BASE
    assert api_cuotaflex.get("/motor/parametros").status_code == 200


@pytest.mark.parametrize(
    ("mes", "hoy", "desembolso"),
    [
        ("mar", date(2026, 11, 23), date(2026, 2, 1)),
        ("ene", date(2026, 1, 15), date(2025, 12, 1)),
        ("dic", date(2026, 11, 23), date(2026, 11, 1)),
    ],
)
def test_fecha_de_desembolso_conserva_el_mes_de_la_primera_cuota(mes, hoy, desembolso):
    simulado = {"propuesta": {"cronograma": [{"mes": mes}]}}
    assert core_fineract._fecha_desembolso(simulado, hoy) == desembolso


@pytest.mark.fineract
@pytest.mark.skipif(not os.getenv("FINERACT_URL"), reason="FINERACT_URL no configurada")
def test_espejo_estacional_en_fineract_real(api_cuotaflex, monkeypatch, tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "seed_fineract.py"
    sembrar = runpy.run_path(str(script))["sembrar"]
    with FineractClient.desde_entorno() as cliente:
        ids = sembrar(cliente)
        assert sembrar(cliente) == ids

        ruta_ids = tmp_path / "ids.json"
        ruta_ids.write_text(json.dumps(ids), encoding="utf-8")
        monkeypatch.setattr(core_fineract, "RUTA_IDS", ruta_ids)

        estado = api_cuotaflex.get("/core/estado")
        assert estado.status_code == 200, estado.text
        assert estado.json()["fineract"] == "conectado", estado.text
        mes = date.today().month - 1
        cliente_simulado = api_cuotaflex.post(f"{api.BASE}/clients", json={
            "nombre": "Rosa Salazar",
            "rubro": "agricultura",
            "ventas_medias": 7000,
            "margen": 0.35,
            "gasto_familiar": 1000,
            "historial_ventas": [float(7000 * PERFILES["agricultura"][(mes + i) % 12]) for i in range(-24, 0)],
        })
        assert cliente_simulado.status_code == 200, cliente_simulado.text
        origen = api_cuotaflex.post(f"{api.BASE}/loans", json={
            "clientId": cliente_simulado.json()["clientId"], "principal": 6000,
            "numberOfRepayments": 12, "mesPrimeraCuota": mes,
            "productoPreferido": "estacional",  # Pide la modalidad estacional para probar su espejo.
        })
        assert origen.status_code == 200, origen.text
        assert origen.json()["producto"] == "estacional"
        loan_id = origen.json()["loanId"]

        ruta = f"/core/espejo/{loan_id}"
        pendiente = api_cuotaflex.post(ruta)
        assert pendiente.status_code == 200, pendiente.text
        id_real = pendiente.json()["fineractLoanId"]
        cronograma = cliente.calcular_cronograma(id_real)
        assert len([periodo for periodo in cronograma["periods"] if periodo.get("period")]) == 12

        for comando in ("approve", "disburse"):
            cambio = api_cuotaflex.post(f"{api.BASE}/loans/{loan_id}", params={"command": comando})
            assert cambio.status_code == 200, cambio.text
        respuesta = api_cuotaflex.post(ruta)
        assert respuesta.status_code == 200, respuesta.text
        espejo = respuesta.json()
        assert len(espejo["cuotas"]) == 12
        assert len({cuota["simulado"] for cuota in espejo["cuotas"]}) > 1
        assert espejo["diferenciaMaximaSinUltima"] <= 0.05
        assert all(abs(cuota["diferencia"]) <= 0.05 for cuota in espejo["cuotas"][:-1])
        assert espejo["fineractClientId"] > 0

        assert espejo["fineractLoanId"] == id_real
        prestamo = cliente.obtener_prestamo(id_real)
        assert prestamo["status"]["active"] is True
        assert prestamo["currency"]["code"] == "PEN"
        assert prestamo["timeline"]["actualDisbursementDate"]
        primera = next(fila for fila in prestamo["repaymentSchedule"]["periods"] if fila.get("period") == 1)
        assert primera["dueDate"][1] == mes + 1

        lectura = api_cuotaflex.get(ruta)
        assert lectura.status_code == 200, lectura.text
        assert lectura.json()["cuotas"] == espejo["cuotas"]

        repetida = api_cuotaflex.post(ruta)
        assert repetida.status_code == 200, repetida.text
        assert repetida.json()["fineractLoanId"] == id_real

        pago = cliente.pagar(id_real, 1, date.today())
        assert pago["resourceId"] > 0
