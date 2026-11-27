"""Llaves personales (fase 4): código por préstamo para el cliente y usuario + PIN para el equipo."""
from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from cuotaflex import almacen, cuentas, llaves
from cuotaflex.api import main as api
from cuotaflex.api.routers import admin


def _carga(token: str) -> dict:
    cuerpo = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_AUTH", "1")
    monkeypatch.setenv("CUOTAFLEX_SECRETO", "secreto-de-prueba")
    monkeypatch.delenv("CUOTAFLEX_PIN_GENERAL", raising=False)
    monkeypatch.delenv("CUOTAFLEX_REGISTRO", raising=False)
    monkeypatch.setattr(llaves, "CACHE_EQUIPO_S", 0)
    almacen.vaciar_memoria()
    cuentas.borrar_todo()
    llaves.olvidar_intentos()
    admin.reset(sembrar=True)  # préstamos de demo 2 (Rosa) y 4 (Luis)
    yield TestClient(api.app)
    almacen.vaciar_memoria()
    cuentas.borrar_todo()
    llaves.olvidar_intentos()


def _pin_general(http, rol: str) -> str:
    return http.post("/auth/login", json={"rol": rol, "pin": {"asesor": "1111", "cliente": "2222",
                                                              "supervisor": "3333"}[rol]}).json()["token"]


def _codigo(http, lid: int) -> str:
    r = http.get(f"/motor/prestamos/{lid}/llave", headers=_h(_pin_general(http, "asesor")))
    assert r.status_code == 200, r.text
    return r.json()["codigo"]


# ---------------------------------------------------------------- cliente

def test_el_cliente_entra_con_su_codigo_y_solo_ve_su_prestamo(http):
    codigo = _codigo(http, 2)
    assert len(codigo) == 6 and codigo.isdigit()
    r = http.post("/auth/cliente", json={"prestamo": 2, "codigo": codigo})
    assert r.status_code == 200
    token = r.json()["token"]
    carga = _carga(token)
    assert carga["rol"] == "cliente" and carga["prestamo"] == 2 and carga["nombre"] == "Rosa Salazar"
    assert http.get("/cliente/prestamos/2", headers=_h(token)).status_code == 200
    assert http.get("/fineract-provider/api/v1/loans/2", headers=_h(token)).status_code == 200
    assert http.get("/cliente/el-nino", headers=_h(token)).status_code == 200
    otro = http.get("/cliente/prestamos/4", headers=_h(token))
    assert otro.status_code == 403 and "propio préstamo" in otro.json()["detail"]
    assert http.get("/fineract-provider/api/v1/loans/4", headers=_h(token)).status_code == 403
    assert http.post("/cliente/demo-seed", headers=_h(token)).status_code == 403
    assert http.post("/cliente/el-nino", json={"activo": True}, headers=_h(token)).status_code == 403
    assert http.get("/motor/prestamos", headers=_h(token)).status_code == 403
    perfil = http.get("/auth/yo", headers=_h(token)).json()
    assert perfil["metodo"] == "codigo" and perfil["prestamo"] == 2


def test_codigo_incorrecto_y_bloqueo_tras_varios_intentos(http):
    codigo = _codigo(http, 2)
    malo = "000000" if codigo != "000000" else "111111"
    r = http.post("/auth/cliente", json={"prestamo": 2, "codigo": malo})
    assert r.status_code == 401 and r.json()["campo"] == "codigo"
    assert http.post("/auth/cliente", json={"prestamo": 999, "codigo": codigo}).status_code == 401
    for _ in range(llaves.MAX_INTENTOS - 1):
        http.post("/auth/cliente", json={"prestamo": 2, "codigo": malo})
    bloqueado = http.post("/auth/cliente", json={"prestamo": 2, "codigo": codigo})
    assert bloqueado.status_code == 429  # ni con el código correcto, hasta que pase la ventana


def test_codigo_nuevo_corta_el_anterior_y_sus_sesiones(http):
    viejo = _codigo(http, 2)
    sesion = http.post("/auth/cliente", json={"prestamo": 2, "codigo": viejo}).json()["token"]
    asesor = _pin_general(http, "asesor")
    nuevo = http.post("/motor/prestamos/2/llave/regenerar", headers=_h(asesor)).json()["codigo"]
    assert nuevo != viejo
    r = http.get("/cliente/prestamos/2", headers=_h(sesion))
    assert r.status_code == 401 and "ya no es válido" in r.json()["detail"]
    assert http.post("/auth/cliente", json={"prestamo": 2, "codigo": viejo}).status_code == 401
    assert http.post("/auth/cliente", json={"prestamo": 2, "codigo": nuevo}).status_code == 200


def test_codigos_de_demo_no_cambian_al_reiniciar(http):
    antes = (_codigo(http, 2), _codigo(http, 4))
    admin.reset(sembrar=True)
    assert (_codigo(http, 2), _codigo(http, 4)) == antes
    assert antes[0] != antes[1]


def test_prestamos_nuevos_tienen_llave_propia(http):
    asesor = _pin_general(http, "asesor")
    cid = http.post("/fineract-provider/api/v1/clients", headers=_h(asesor), json={
        "nombre": "Marta Ríos", "rubro": "bodega", "ventas_medias": 5000, "margen": 0.3, "gasto_familiar": 900,
        "dias_atraso_max": 0}).json()["clientId"]
    lid = http.post("/fineract-provider/api/v1/loans", headers=_h(asesor), json={
        "clientId": cid, "principal": 3000, "numberOfRepayments": 12, "mesPrimeraCuota": 3}).json()["loanId"]
    p = api.DB["loans"][lid]
    assert len(p["llaveUid"]) == 16 and p["llaveVersion"] == 1
    assert http.post("/auth/cliente", json={"prestamo": lid, "codigo": _codigo(http, lid)}).status_code == 200


def test_solo_asesor_y_supervisor_ven_el_codigo(http):
    cliente = _pin_general(http, "cliente")
    assert http.get("/motor/prestamos/2/llave", headers=_h(cliente)).status_code == 403
    sup = _pin_general(http, "supervisor")
    assert http.get("/motor/prestamos/2/llave", headers=_h(sup)).json()["cliente"] == "Rosa Salazar"
    assert http.get("/motor/prestamos/77/llave", headers=_h(sup)).status_code == 404


def test_cuenta_de_cliente_se_vincula_con_el_codigo(http):
    r = http.post("/auth/registro", json={"rol": "cliente", "nombre": "Rosa Salazar", "correo": "rosa@ejemplo.pe",
                                          "contrasena": "arroz2026"})
    token = r.json()["token"]
    bloqueado = http.get("/cliente/prestamos/2", headers=_h(token))
    assert bloqueado.status_code == 403 and "Vincula" in bloqueado.json()["detail"]
    assert http.get("/cliente/el-nino", headers=_h(token)).status_code == 200
    codigo = _codigo(http, 2)
    assert http.post("/auth/vincular", json={"prestamo": 2, "codigo": "123"}, headers=_h(token)).status_code == 401
    v = http.post("/auth/vincular", json={"prestamo": 2, "codigo": codigo}, headers=_h(token))
    assert v.status_code == 200 and _carga(v.json()["token"])["prestamo"] == 2
    assert http.get("/cliente/prestamos/2", headers=_h(v.json()["token"])).status_code == 200
    # al volver a ingresar con correo, la sesión ya trae su préstamo
    otra = http.post("/auth/ingresar", json={"correo": "rosa@ejemplo.pe", "contrasena": "arroz2026"}).json()["token"]
    assert _carga(otra)["prestamo"] == 2
    assert http.get("/cliente/prestamos/4", headers=_h(otra)).status_code == 403
    assert http.post("/auth/vincular", json={"prestamo": 2, "codigo": codigo}).status_code == 401  # sin sesión


# ---------------------------------------------------------------- equipo

def test_supervisor_agrega_personas_y_cada_una_entra_con_su_pin(http):
    sup = _pin_general(http, "supervisor")
    r = http.post("/equipo", json={"nombre": "Ana Torres Rojas", "rol": "asesor"}, headers=_h(sup))
    assert r.status_code == 201
    ana, pin = r.json()["persona"], r.json()["pin"]
    assert ana["usuario"] == "ana.torres" and ana["activo"] and len(pin) == 6 and "hash" not in ana
    otra = http.post("/equipo", json={"nombre": "Ana Torres Díaz", "rol": "supervisor"}, headers=_h(sup)).json()
    assert otra["persona"]["usuario"] == "ana.torres2"
    lista = http.get("/equipo", headers=_h(sup)).json()
    assert [p["usuario"] for p in lista["personas"]] == ["ana.torres", "ana.torres2"]
    assert lista["almacen"]["tipo"] == "memoria" and lista["pin_general"] is True

    entra = http.post("/auth/personal", json={"usuario": " Ana.Torres ", "pin": pin, "rol": "asesor"})
    assert entra.status_code == 200
    token = entra.json()["token"]
    assert _carga(token)["nombre"] == "Ana Torres Rojas"
    assert http.get("/motor/prestamos", headers=_h(token)).status_code == 200
    assert http.get("/equipo", headers=_h(token)).status_code == 403  # un asesor no administra el equipo
    assert http.get("/auth/yo", headers=_h(token)).json()["metodo"] == "personal"
    mal_rol = http.post("/auth/personal", json={"usuario": "ana.torres", "pin": pin, "rol": "supervisor"})
    assert mal_rol.status_code == 403 and "asesor" in mal_rol.json()["detail"]
    assert http.post("/auth/personal", json={"usuario": "ana.torres", "pin": "000000"}).status_code == 401
    assert http.post("/auth/personal", json={"usuario": "nadie", "pin": pin}).status_code == 401


def test_desactivar_o_cambiar_pin_corta_la_sesion(http):
    sup = _pin_general(http, "supervisor")
    pin = http.post("/equipo", json={"nombre": "Luis Paz", "rol": "asesor"}, headers=_h(sup)).json()["pin"]
    token = http.post("/auth/personal", json={"usuario": "luis.paz", "pin": pin}).json()["token"]
    assert http.post("/equipo/luis.paz/estado", json={"activo": False}, headers=_h(sup)).status_code == 200
    cortada = http.get("/motor/prestamos", headers=_h(token))
    assert cortada.status_code == 401 and "desactivado" in cortada.json()["detail"]
    desactivado = http.post("/auth/personal", json={"usuario": "luis.paz", "pin": pin})
    assert desactivado.status_code == 403
    http.post("/equipo/luis.paz/estado", json={"activo": True}, headers=_h(sup))
    token = http.post("/auth/personal", json={"usuario": "luis.paz", "pin": pin}).json()["token"]
    nuevo = http.post("/equipo/luis.paz/pin", headers=_h(sup)).json()["pin"]
    assert nuevo != pin
    assert http.get("/motor/prestamos", headers=_h(token)).status_code == 401
    assert http.post("/auth/personal", json={"usuario": "luis.paz", "pin": pin}).status_code == 401
    assert http.post("/auth/personal", json={"usuario": "luis.paz", "pin": nuevo}).status_code == 200
    assert http.post("/equipo/nadie/pin", headers=_h(sup)).status_code == 404


def test_supervisor_no_se_desactiva_a_si_mismo(http):
    sup = _pin_general(http, "supervisor")
    pin = http.post("/equipo", json={"nombre": "Carla Mejía", "rol": "supervisor"}, headers=_h(sup)).json()["pin"]
    carla = http.post("/auth/personal", json={"usuario": "carla.mejia", "pin": pin}).json()["token"]
    r = http.post("/equipo/carla.mejia/estado", json={"activo": False}, headers=_h(carla))
    assert r.status_code == 409


def test_validaciones_al_agregar(http):
    sup = _pin_general(http, "supervisor")
    corto = http.post("/equipo", json={"nombre": "A", "rol": "asesor"}, headers=_h(sup))
    assert corto.status_code == 400 and corto.json()["campo"] == "nombre"  # mismo criterio que las cuentas
    assert http.post("/equipo", json={"nombre": "Ana Torres", "rol": "cliente"}, headers=_h(sup)).status_code == 422


def test_pin_general_apagado(http, monkeypatch):
    sup = _pin_general(http, "supervisor")
    pin = http.post("/equipo", json={"nombre": "Rosa Vega", "rol": "supervisor"}, headers=_h(sup)).json()["pin"]
    monkeypatch.setenv("CUOTAFLEX_PIN_GENERAL", "0")
    assert http.post("/auth/login", json={"rol": "supervisor", "pin": "3333"}).status_code == 403
    assert http.get("/equipo", headers=_h(sup)).status_code == 401  # las sesiones con PIN general caen
    personal = http.post("/auth/personal", json={"usuario": "rosa.vega", "pin": pin}).json()["token"]
    assert http.get("/equipo", headers=_h(personal)).status_code == 200
    config = http.get("/auth/config").json()
    assert config["pin_general"] is False and config["llaves"] == {"cliente": "codigo", "equipo": "usuario_pin"}


def test_pines_personales_no_son_triviales():
    for _ in range(300):
        pin = llaves._pin_nuevo()
        assert len(pin) == 6 and len(set(pin)) >= 3 and pin not in ("123456", "654321", "012345", "987654")
