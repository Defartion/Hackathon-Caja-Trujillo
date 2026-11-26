"""El cliente elige qué cuota paga; cronograma con vencimientos y desglose; detalle del préstamo para el asesor."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from cuotaflex import cronograma as crono
from cuotaflex import cuentas
from cuotaflex.api import main as api


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setattr(api, "DB", {"clients": {}, "loans": {}})
    cuentas.borrar_todo()
    with TestClient(api.app) as cliente:
        yield cliente
    cuentas.borrar_todo()


def _prestamo(http) -> int:
    return http.post("/cliente/demo-seed").json()["loanId"]


def test_el_cliente_adelanta_una_cuota_y_la_proxima_sigue_siendo_la_primera(http):
    lid = _prestamo(http)
    ruta = f"/cliente/prestamos/{lid}"
    r = http.post(f"{ruta}/pagar", json={"cuota": 4})
    assert r.status_code == 200 and r.json()["cuota"] == 4
    datos = http.get(ruta).json()
    estados = [f["estado"] for f in datos["cronograma"]]
    assert estados[:5] == ["proxima", "pendiente", "pendiente", "pagada", "pendiente"]
    assert datos["proximaCuota"]["numero"] == 1 and datos["cuotasPagadas"] == 1
    assert api.DB["loans"][lid]["pagos"][-1] == {"monto": datos["cronograma"][3]["cuota"], "fecha": str(date.today()),
                                                 "cuota": 4}
    assert http.post(f"{ruta}/pagar", json={"cuota": 4}).status_code == 409
    assert http.post(f"{ruta}/pagar", json={"cuota": 13}).status_code == 400
    # Sin cuerpo paga la próxima, como antes; al completar el hueco las cuotas seguidas se juntan.
    for esperada in (1, 2, 3):
        assert http.post(f"{ruta}/pagar").json()["cuota"] == esperada
    prestamo = api.DB["loans"][lid]
    assert prestamo["cuotasPagadas"] == 4 and prestamo["cuotasAdelantadas"] == []
    assert http.get(ruta).json()["proximaCuota"]["numero"] == 5


def test_la_ultima_cuota_pagada_por_adelantado_termina_el_credito(http):
    lid = _prestamo(http)
    ruta = f"/cliente/prestamos/{lid}"
    for n in [12, *range(1, 12)]:
        assert http.post(f"{ruta}/pagar", json={"cuota": n}).status_code == 200
    datos = http.get(ruta).json()
    assert datos["proximaCuota"] is None and datos["cuotasPagadas"] == 12
    assert http.post(f"{ruta}/pagar").status_code == 409


def test_cronograma_con_vencimiento_a_fin_de_mes_y_desglose(http):
    lid = _prestamo(http)
    http.post(f"/cliente/prestamos/{lid}/pagar")
    datos = http.get(f"/cliente/prestamos/{lid}").json()
    filas = datos["cronograma"]
    fechas = [date.fromisoformat(f["fecha"]) for f in filas]
    assert fechas == sorted(fechas) and fechas[0] >= date.today().replace(day=1)
    assert all((d.replace(day=28) + (d - d.replace(day=28))).month == d.month for d in fechas)
    assert all(abs(f["capital"] + f["interes"] - f["cuota"]) < 0.02 for f in filas)
    assert abs(filas[-1]["saldo"]) < 1 and filas[0]["saldo"] < datos["principal"]
    assert filas[0]["fechaPago"] == str(date.today()) and filas[1]["fechaPago"] is None
    assert datos["proximaCuota"]["fecha"] == filas[1]["fecha"]
    assert datos["fechaDesembolso"] == str(date.today())
    assert datos["cuotaFijaReferencia"] > 0


def test_resumen_para_el_inicio_del_cliente(http):
    lid = _prestamo(http)
    http.post(f"/cliente/prestamos/{lid}/pagar")
    datos = http.get(f"/cliente/prestamos/{lid}").json()
    res, filas = datos["resumen"], datos["cronograma"]
    assert res["totalAPagar"] == pytest.approx(sum(f["cuota"] for f in filas), abs=0.01)
    assert res["totalPagado"] == pytest.approx(filas[0]["cuota"], abs=0.01)
    assert res["porPagar"] == pytest.approx(res["totalAPagar"] - res["totalPagado"], abs=0.02)
    assert res["saldoCapital"] == pytest.approx(filas[0]["saldo"], abs=0.02)
    assert res["cuotasPendientes"] == 11
    assert res["cuotaMayor"]["monto"] >= res["cuotaMenor"]["monto"]
    assert res["proximoVencimiento"] == filas[1]["fecha"] and res["diasParaVencer"] >= 0


def test_vencimientos_sin_fecha_de_desembolso_y_primer_mes_anterior():
    prestamo = {"cuotas": [100.0] * 3, "fechaDesembolso": "2026-11-26",
                "propuesta": {"cronograma": [{"mes": "ene"}, {"mes": "feb"}, {"mes": "mar"}]}}
    assert crono.fechas_vencimiento(prestamo) == [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)]
    prestamo["propuesta"]["cronograma"][0]["mes"] = "nov"
    assert crono.fechas_vencimiento(prestamo)[0] == date(2026, 11, 30)


def test_detalle_del_prestamo_para_el_asesor(http, monkeypatch):
    lid = _prestamo(http)
    http.post(f"/cliente/prestamos/{lid}/pagar", json={"cuota": 3})
    d = http.get(f"/motor/prestamos/{lid}").json()
    assert d["estado"] == "Active" and d["plazo"] == len(d["cronograma"]) == d["totalCuotas"] == 12
    assert d["cliente"]["nombre"] == "Rosa Salazar" and d["cliente"]["rubro"] == "agricultura"
    assert d["pagos"] == [{"fecha": str(date.today()), "monto": d["cronograma"][2]["cuota"], "cuota": 3}]
    assert d["cuotasPagadas"] == 1 and d["resumen"]["cuotasPendientes"] == 11
    assert d["cuotaMinima"] <= d["cuotaMaxima"] and d["explicacion"]
    assert http.get("/motor/prestamos/9999").status_code == 404
    monkeypatch.setenv("CUOTAFLEX_AUTH", "1")
    tok = http.post("/auth/login", json={"rol": "cliente", "pin": "2222"}).json()["token"]
    assert http.get(f"/motor/prestamos/{lid}", headers={"Authorization": f"Bearer {tok}"}).status_code == 403


def test_perfil_de_la_sesion(http):
    reg = http.post("/auth/registro", json={"rol": "cliente", "nombre": "Rosa Quispe", "correo": "rosa@ejemplo.pe",
                                            "contrasena": "arroz2026"}).json()
    yo = http.get("/auth/yo", headers={"Authorization": f"Bearer {reg['token']}"}).json()
    assert yo["sesion"] and yo["metodo"] == "cuenta" and yo["correo"] == "rosa@ejemplo.pe"
    assert yo["nombre"] == "Rosa Quispe" and yo["creado"]
    pin = http.post("/auth/login", json={"rol": "asesor", "pin": "1111"}).json()["token"]
    yo_pin = http.get("/auth/yo", headers={"Authorization": f"Bearer {pin}"}).json()
    assert yo_pin["metodo"] == "pin" and yo_pin["rol"] == "asesor" and yo_pin["correo"] is None
    assert http.get("/auth/yo").json() == {"sesion": False}
    assert http.get("/auth/yo", headers={"Authorization": "Bearer roto.token"}).json() == {"sesion": False}
