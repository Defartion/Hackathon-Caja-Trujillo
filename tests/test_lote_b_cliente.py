from copy import deepcopy
from datetime import date

import pytest
from fastapi.testclient import TestClient

from cuotaflex.agente import MESES_ES
from cuotaflex.api import main as api
from cuotaflex.config import factores_descuento, tea_a_tem


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(api, "DB", {"clients": {}, "loans": {}})
    with TestClient(api.app) as cliente:
        cliente.post("/cliente/el-nino", json={"activo": False})
        yield cliente
        cliente.post("/cliente/el-nino", json={"activo": False})


def _seed(cliente, producto):
    respuesta = cliente.post("/cliente/demo-seed", params={"producto": producto} if producto else None)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["loanId"]


@pytest.mark.parametrize("producto", [None, "aplazamiento"])
def test_demo_seed_entrega_un_prestamo_activo_de_12_cuotas(cliente, producto):
    prestamo = cliente.get(f"/cliente/prestamos/{_seed(cliente, producto)}").json()
    assert prestamo["estado"] == "Active"
    assert prestamo["principal"] == 6000
    assert prestamo["producto"] == (producto or "estacional")
    assert prestamo["totalCuotas"] == len(prestamo["cronograma"]) == 12
    assert prestamo["proximaCuota"]["numero"] == 1
    assert prestamo["proximaCuota"]["mes"] == MESES_ES[date.today().month - 1]
    assert prestamo["cronograma"][0]["estado"] == "proxima"
    assert prestamo["cronograma"][1]["estado"] == "pendiente"


def test_prestamo_creado_por_el_core_usa_sus_cuotas_vigentes(cliente):
    client_id = cliente.post(f"{api.BASE}/clients", json={
        "nombre": "Cliente de integración", "rubro": "bodega", "ventas_medias": 7000,
        "margen": 0.35, "gasto_familiar": 1000,
    }).json()["clientId"]
    loan_id = cliente.post(f"{api.BASE}/loans", json={
        "clientId": client_id, "principal": 6000, "numberOfRepayments": 12, "mesPrimeraCuota": 5,
    }).json()["loanId"]
    core = f"{api.BASE}/loans/{loan_id}"
    assert cliente.post(f"{core}/schedule", params={"command": "addVariations"},
                        json={"cuotas": [615] * 12}).status_code == 200
    assert cliente.post(core, params={"command": "approve"}).status_code == 200
    assert cliente.post(core, params={"command": "disburse"}).status_code == 200
    prestamo = cliente.get(f"/cliente/prestamos/{loan_id}").json()
    assert prestamo["nombre"] == "Cliente de integración"
    assert prestamo["proximaCuota"]["mes"] == "jun"
    assert prestamo["proximaCuota"]["monto"] == 615


def test_preview_conserva_estado_y_valor_presente_y_coincide_con_confirmacion(cliente):
    loan_id = _seed(cliente, "aplazamiento")
    prestamo = f"/cliente/prestamos/{loan_id}"
    original = deepcopy(api.DB["loans"][loan_id])
    entrada = {"installment": 2}
    respuesta = cliente.post(f"{prestamo}/aplazamiento/preview", json=entrada)
    assert respuesta.status_code == 200, respuesta.text
    assert api.DB["loans"][loan_id] == original

    preview = respuesta.json()
    montos = [fila["cuota"] for fila in preview["cronogramaNuevo"]]
    assert montos[0] == original["cuotas"][0]
    assert preview["nuevaCuota"] < preview["cuotaActual"]
    assert preview["incrementoCuotasSiguientes"] > 0
    assert preview["costoAdicionalTotal"] == round(sum(montos) - sum(original["cuotas"]), 2)
    assert preview["costoAdicionalTotal"] > 0
    descuentos = factores_descuento(tea_a_tem(original["tea"]), len(montos))
    assert descuentos @ montos == pytest.approx(original["principal"], abs=1)

    assert cliente.post(f"{prestamo}/aplazamiento", json=entrada).status_code == 200
    actualizado = cliente.get(prestamo).json()
    assert actualizado["cronograma"] == preview["cronogramaNuevo"]
    assert actualizado["aplazamientosRestantes"] == original["aplazamientosRestantes"] - 1


def test_aplazamiento_rechaza_cuotas_pagadas_y_la_ultima(cliente):
    prestamo = f"/cliente/prestamos/{_seed(cliente, 'aplazamiento')}"
    assert cliente.post(f"{prestamo}/pagar").status_code == 200
    for numero in (1, 12):
        for ruta in ("aplazamiento/preview", "aplazamiento"):
            assert cliente.post(f"{prestamo}/{ruta}", json={"installment": numero}).status_code == 400


def test_aplazamiento_pide_otra_vista_previa_si_cambia_el_cronograma(cliente):
    loan_id = _seed(cliente, "aplazamiento")
    aplazamiento = f"/cliente/prestamos/{loan_id}/aplazamiento"
    entrada = {"installment": 3}
    previa = cliente.post(f"{aplazamiento}/preview", json=entrada).json()
    assert cliente.post(aplazamiento, json={"installment": 1}).status_code == 200

    antes = deepcopy(api.DB["loans"][loan_id])
    respuesta = cliente.post(aplazamiento, json={**entrada, "revision": previa["revision"]})
    assert respuesta.status_code == 409, respuesta.text
    assert api.DB["loans"][loan_id] == antes

    nueva_previa = cliente.post(f"{aplazamiento}/preview", json=entrada).json()
    assert nueva_previa["costoAdicionalTotal"] != previa["costoAdicionalTotal"]
    respuesta = cliente.post(aplazamiento, json={**entrada, "revision": nueva_previa["revision"]})
    assert respuesta.status_code == 200, respuesta.text


def test_aplazamiento_no_gasta_otra_oportunidad_en_una_cuota_ya_minima(cliente):
    prestamo = f"/cliente/prestamos/{_seed(cliente, 'aplazamiento')}"
    entrada = {"installment": 1}
    assert cliente.post(f"{prestamo}/aplazamiento", json=entrada).status_code == 200
    antes = cliente.get(prestamo).json()
    for ruta in ("aplazamiento/preview", "aplazamiento"):
        assert cliente.post(f"{prestamo}/{ruta}", json=entrada).status_code == 409
    assert cliente.get(prestamo).json() == antes


def test_aplazamiento_devuelve_conflicto_al_agotar_las_oportunidades(cliente):
    prestamo = f"/cliente/prestamos/{_seed(cliente, 'aplazamiento')}"
    for numero in (1, 2):
        assert cliente.post(f"{prestamo}/aplazamiento", json={"installment": numero}).status_code == 200
    assert cliente.get(prestamo).json()["aplazamientosRestantes"] == 0
    for ruta in ("aplazamiento/preview", "aplazamiento"):
        assert cliente.post(f"{prestamo}/{ruta}", json={"installment": 3}).status_code == 409


def test_el_nino_activa_el_alivio_una_vez_por_cuota(cliente):
    prestamo = f"/cliente/prestamos/{_seed(cliente, None)}"
    antes = cliente.get(prestamo).json()
    assert cliente.post(f"{prestamo}/alivio-el-nino").status_code == 409
    assert cliente.get("/cliente/el-nino").json() == {"activo": False, "desde": None, "fuente": "demo"}

    estado = cliente.post("/cliente/el-nino", json={"activo": True}).json()
    assert estado == {"activo": True, "desde": date.today().isoformat(), "fuente": "demo"}
    assert cliente.get("/cliente/el-nino").json() == estado
    assert cliente.get(prestamo).json()["elNino"]["puedeAplicar"]

    assert cliente.post(f"{prestamo}/alivio-el-nino").status_code == 200
    despues = cliente.get(prestamo).json()
    assert despues["proximaCuota"]["monto"] <= antes["proximaCuota"]["monto"]
    assert despues["elNino"]["alivioDisponible"] == antes["elNino"]["alivioDisponible"] - 1
    assert despues["aplazamientosRestantes"] == antes["aplazamientosRestantes"]
    assert not despues["elNino"]["puedeAplicar"]
    assert cliente.post(f"{prestamo}/alivio-el-nino").status_code == 409
    assert cliente.post(f"{prestamo}/pagar").status_code == 200
    assert cliente.get(prestamo).json()["elNino"]["puedeAplicar"]


def test_el_nino_rechaza_un_prestamo_sin_clausula(cliente):
    prestamo = f"/cliente/prestamos/{_seed(cliente, 'aplazamiento')}"
    cliente.post("/cliente/el-nino", json={"activo": True})
    assert cliente.post(f"{prestamo}/alivio-el-nino").status_code == 409


def test_pagar_registra_el_monto_vigente_y_avanza_hasta_terminar(cliente):
    loan_id = _seed(cliente, "aplazamiento")
    prestamo = f"/cliente/prestamos/{loan_id}"
    assert cliente.post(f"{prestamo}/aplazamiento", json={"installment": 1}).status_code == 200
    primera = cliente.get(prestamo).json()["proximaCuota"]
    assert cliente.post(f"{prestamo}/pagar").status_code == 200
    assert api.DB["loans"][loan_id]["pagos"][0]["monto"] == primera["monto"]
    despues = cliente.get(prestamo).json()
    assert despues["cuotasPagadas"] == 1
    assert despues["proximaCuota"]["numero"] == 2
    assert despues["cronograma"][0]["estado"] == "pagada"

    for _ in range(11):
        assert cliente.post(f"{prestamo}/pagar").status_code == 200
    assert cliente.get(prestamo).json()["proximaCuota"] is None
    assert cliente.post(f"{prestamo}/pagar").status_code == 409
