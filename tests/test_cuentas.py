"""Cuentas con correo y contraseña: registro, ingreso, política por rol y persistencia."""
import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from cuotaflex import cuentas, persistencia
from cuotaflex.api import main as api
from cuotaflex.api.routers import auth

ROSA = {"rol": "cliente", "nombre": "Rosa Quispe", "correo": "Rosa@Ejemplo.pe", "contrasena": "arroz2026"}


@pytest.fixture
def http(monkeypatch):
    monkeypatch.delenv("CUOTAFLEX_REGISTRO", raising=False)
    cuentas.borrar_todo()
    yield TestClient(api.app)
    cuentas.borrar_todo()


def _carga(token: str) -> dict:
    cuerpo = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))


def test_config_informa_quien_puede_registrarse(http):
    r = http.get("/auth/config").json()
    assert r["registro"] == {"asesor": "codigo", "cliente": "libre", "supervisor": "codigo"}
    assert "auth" in r and r["roles"] == ["asesor", "cliente", "supervisor"]


def test_cliente_crea_su_cuenta_y_queda_con_sesion(http, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_AUTH", "1")
    r = http.post("/auth/registro", json=ROSA)
    assert r.status_code == 201, r.text
    datos = r.json()
    assert datos["rol"] == "cliente" and datos["usuario"]["correo"] == "rosa@ejemplo.pe"
    assert "hash" not in datos["usuario"] and "contrasena" not in json.dumps(datos)
    carga = _carga(datos["token"])
    assert carga["nombre"] == "Rosa Quispe" and carga["rol"] == "cliente" and carga["id"] == datos["usuario"]["id"]
    assert auth.verificar_token(datos["token"]) == "cliente"
    cabecera = {"Authorization": f"Bearer {datos['token']}"}
    assert http.get("/cliente/el-nino", headers=cabecera).status_code == 200
    assert http.get("/motor/cartera-demo?n=2", headers=cabecera).status_code == 403  # sigue siendo rol cliente


def test_no_se_repite_el_correo(http):
    assert http.post("/auth/registro", json=ROSA).status_code == 201
    r = http.post("/auth/registro", json={**ROSA, "correo": " rosa@EJEMPLO.pe "})
    assert r.status_code == 409 and r.json()["campo"] == "correo"


def test_asesor_y_supervisor_necesitan_el_pin_de_su_rol(http, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_AUTH", "1")
    base = {"nombre": "Ana Torres", "correo": "ana@caja.pe", "contrasena": "asesora123"}
    sin = http.post("/auth/registro", json={**base, "rol": "asesor"})
    assert sin.status_code == 403 and sin.json()["campo"] == "codigo"
    malo = http.post("/auth/registro", json={**base, "rol": "asesor", "codigo": "0000"})
    assert malo.status_code == 403
    ok = http.post("/auth/registro", json={**base, "rol": "asesor", "codigo": "1111"})
    assert ok.status_code == 201
    tok = {"Authorization": f"Bearer {ok.json()['token']}"}
    assert http.get("/motor/cartera-demo?n=2", headers=tok).status_code == 200
    monkeypatch.setenv("PIN_SUPERVISOR", "9876")
    sup = http.post("/auth/registro", json={**base, "correo": "jefa@caja.pe", "rol": "supervisor", "codigo": "9876"})
    assert sup.status_code == 201 and sup.json()["rol"] == "supervisor"


@pytest.mark.parametrize("cambio, campo", [
    ({"contrasena": "corta1"}, "contrasena"),
    ({"contrasena": "solamenteletras"}, "contrasena"),
    ({"correo": "rosa-sin-arroba"}, "correo"),
    ({"nombre": "R"}, "nombre"),
])
def test_valida_los_datos_con_mensajes_claros(http, cambio, campo):
    r = http.post("/auth/registro", json={**ROSA, **cambio})
    assert r.status_code == 400 and r.json()["campo"] == campo
    assert isinstance(r.json()["detail"], str) and r.json()["detail"]


def test_ingresar_con_correo_y_contrasena(http):
    http.post("/auth/registro", json=ROSA)
    ok = http.post("/auth/ingresar", json={"correo": "ROSA@ejemplo.pe", "contrasena": "arroz2026", "rol": "cliente"})
    assert ok.status_code == 200 and ok.json()["usuario"]["nombre"] == "Rosa Quispe"
    mala = http.post("/auth/ingresar", json={"correo": "rosa@ejemplo.pe", "contrasena": "arroz2027"})
    nadie = http.post("/auth/ingresar", json={"correo": "nadie@ejemplo.pe", "contrasena": "arroz2026"})
    assert mala.status_code == nadie.status_code == 401
    assert mala.json()["detail"] == nadie.json()["detail"]  # no revela qué correos existen
    otra_app = http.post("/auth/ingresar", json={"correo": "rosa@ejemplo.pe", "contrasena": "arroz2026", "rol": "asesor"})
    assert otra_app.status_code == 403 and "cliente" in otra_app.json()["detail"]


def test_bloquea_tras_varios_intentos_fallidos(http):
    http.post("/auth/registro", json=ROSA)
    for _ in range(cuentas.MAX_INTENTOS):
        assert http.post("/auth/ingresar", json={"correo": ROSA["correo"], "contrasena": "x1234567"}).status_code == 401
    r = http.post("/auth/ingresar", json={"correo": ROSA["correo"], "contrasena": ROSA["contrasena"]})
    assert r.status_code == 429


def test_politica_codigo_y_registro_cerrado(http, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_REGISTRO", "codigo")
    assert http.get("/auth/config").json()["registro"]["cliente"] == "codigo"
    assert http.post("/auth/registro", json=ROSA).status_code == 403
    assert http.post("/auth/registro", json={**ROSA, "codigo": "2222"}).status_code == 201
    monkeypatch.setenv("CUOTAFLEX_REGISTRO", "no")
    assert set(http.get("/auth/config").json()["registro"].values()) == {"no"}
    assert http.post("/auth/registro", json={**ROSA, "correo": "otra@ejemplo.pe", "codigo": "2222"}).status_code == 403
    # quien ya tiene cuenta sigue entrando
    assert http.post("/auth/ingresar", json={"correo": ROSA["correo"], "contrasena": ROSA["contrasena"]}).status_code == 200


def test_el_pin_sigue_igual(http):
    tok = http.post("/auth/login", json={"rol": "supervisor", "pin": "3333"}).json()["token"]
    assert set(_carga(tok)) == {"rol", "exp"}
    assert http.post("/auth/login", json={"rol": "supervisor", "pin": "0000"}).status_code == 401


def test_cuentas_persisten_y_el_reinicio_de_la_demo_no_las_borra(http, tmp_path, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_PERSISTENCIA", "1")
    monkeypatch.setenv("CUOTAFLEX_DB", str(tmp_path / "demo.db"))
    respaldo = {k: dict(v) for k, v in api.DB.items()}
    try:
        assert http.post("/auth/registro", json=ROSA).status_code == 201
        with sqlite3.connect(persistencia.ruta_db()) as con:
            correo, h = con.execute("SELECT correo, hash FROM cuentas").fetchone()
        assert correo == "rosa@ejemplo.pe" and ROSA["contrasena"] not in h and h.split("$")[0] in ("scrypt", "pbkdf2")
        assert http.post("/admin/reset?sembrar=false").status_code == 200
        r = http.post("/auth/ingresar", json={"correo": ROSA["correo"], "contrasena": ROSA["contrasena"]})
        assert r.status_code == 200
    finally:
        for k, v in respaldo.items():
            api.DB[k].clear()
            api.DB[k].update(v)


def test_hash_verifica_ambos_formatos():
    h = cuentas.hashear("clave1234")
    assert cuentas.verificar("clave1234", h) and not cuentas.verificar("clave1235", h)
    import hashlib

    sal = b"0123456789abcdef"
    viejo = "pbkdf2$1000$" + cuentas._b64(sal) + "$" + cuentas._b64(hashlib.pbkdf2_hmac("sha256", b"clave1234", sal, 1000))
    assert cuentas.verificar("clave1234", viejo) and not cuentas.verificar("otra", viejo)
    assert not cuentas.verificar("clave1234", "formato$desconocido")
