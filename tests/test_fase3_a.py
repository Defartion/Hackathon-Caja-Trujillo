"""Fase 3 · Lote A: persistencia por instantánea, roles con PIN, reinicio de la demo y espejo automático."""
from itertools import count

import pytest
from fastapi.testclient import TestClient

from cuotaflex import persistencia
from cuotaflex.api import main as api
from cuotaflex.api.routers import auth, espejo_automatico

BASE = api.BASE


@pytest.fixture
def cliente_http():
    return TestClient(api.app)


@pytest.fixture
def con_persistencia(tmp_path, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_PERSISTENCIA", "1")
    monkeypatch.setenv("CUOTAFLEX_DB", str(tmp_path / "demo.db"))
    respaldo = {k: dict(v) for k, v in api.DB.items()}
    yield tmp_path / "demo.db"
    for k, v in respaldo.items():
        api.DB[k].clear()
        api.DB[k].update(v)


def test_persistencia_sobrevive_al_reinicio(cliente_http, con_persistencia):
    seed = cliente_http.post("/cliente/demo-seed?producto=aplazamiento").json()
    lid = seed["loanId"]
    r = cliente_http.post(f"/cliente/prestamos/{lid}/aplazamiento", json={"installment": 2})
    assert r.status_code == 200, r.text
    cuotas = list(api.DB["loans"][lid]["cuotas"])
    assert con_persistencia.exists()

    # "Reinicio": se vacía la memoria y se vuelve a cargar desde SQLite
    for tabla in api.DB.values():
        tabla.clear()
    api._ids = count(1)
    api.cargar_instantanea()
    assert api.DB["loans"][lid]["cuotas"] == cuotas
    assert api.DB["loans"][lid]["status"]["value"] == "Active"
    assert api.siguiente_id() > max(api.DB["loans"])  # el contador continúa, no reusa IDs


def test_instantanea_serializa_tipos_de_numpy(con_persistencia):
    import numpy as np

    db = {"clients": {1: {"x": np.float64(1.5), "b": np.bool_(True)}}, "loans": {2: {"v": np.arange(3)}}}
    persistencia.guardar(db, 3)
    nuevo = {"clients": {}, "loans": {}}
    assert persistencia.cargar(nuevo) == 3
    assert nuevo["clients"][1] == {"x": 1.5, "b": True} and nuevo["loans"][2]["v"] == [0, 1, 2]


def test_sin_auth_todo_funciona_como_antes(cliente_http, monkeypatch):
    monkeypatch.delenv("CUOTAFLEX_AUTH", raising=False)
    assert cliente_http.get("/auth/config").json()["auth"] is False
    assert cliente_http.get("/motor/cartera-demo?n=2").status_code == 200


def test_auth_exige_token_y_rol(cliente_http, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_AUTH", "1")
    assert cliente_http.get("/auth/config").json()["auth"] is True
    assert cliente_http.get("/motor/cartera-demo?n=2").status_code == 401
    assert cliente_http.post("/auth/login", json={"rol": "asesor", "pin": "0000"}).status_code == 401

    def token(rol, pin):
        return {"Authorization": "Bearer " + cliente_http.post("/auth/login", json={"rol": rol, "pin": pin}).json()["token"]}

    asesor, cliente, supervisor = token("asesor", "1111"), token("cliente", "2222"), token("supervisor", "3333")
    assert cliente_http.get("/motor/cartera-demo?n=2", headers=asesor).status_code == 200
    assert cliente_http.get("/motor/cartera-demo?n=2", headers=cliente).status_code == 403
    assert cliente_http.get("/simulacion/parametros-editables", headers=asesor).status_code == 403
    assert cliente_http.get("/simulacion/parametros-editables", headers=supervisor).status_code == 200
    assert cliente_http.get("/cliente/el-nino", headers=cliente).status_code == 200
    assert cliente_http.post(f"{BASE}/clients", headers=cliente, json={}).status_code == 403
    # CORS: también la respuesta 401 lleva el encabezado para el navegador
    r = cliente_http.get("/motor/cartera-demo", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 401 and r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_token_manipulado_o_vencido_no_sirve():
    t = auth.emitir_token("supervisor")
    assert auth.verificar_token(t) == "supervisor"
    cuerpo, firma = t.split(".")
    assert auth.verificar_token(cuerpo + "." + firma[:-2] + "xx") is None
    assert auth.verificar_token(auth.emitir_token("asesor", ahora=0)) is None


def test_reset_deja_la_demo_limpia(cliente_http, con_persistencia):
    cliente_http.post("/cliente/demo-seed")
    r = cliente_http.post("/admin/reset?sembrar=false").json()
    assert r["prestamos"] == 0 and api.DB["loans"] == {} and api.DB["clients"] == {}
    r = cliente_http.post("/admin/reset").json()
    assert r["prestamos"] == 2 and len(r["sembrados"]) == 2


def test_espejo_automatico_no_rompe_el_desembolso_sin_fineract(cliente_http, monkeypatch):
    monkeypatch.setenv("CORE_ESPEJO", "1")
    monkeypatch.setenv("FINERACT_URL", "http://127.0.0.1:9")  # puerto cerrado: Fineract "apagado"
    llamadas = []
    monkeypatch.setattr(espejo_automatico, "programar",
                        lambda ruta, sincrono=False: llamadas.append(ruta) or True)
    seed = cliente_http.post("/cliente/demo-seed").json()  # aprueba y desembolsa por dentro (sin HTTP)
    cid = cliente_http.post(f"{BASE}/clients", json={"nombre": "X", "rubro": "bodega", "ventas_medias": 6000,
                                                      "gasto_familiar": 900}).json()["clientId"]
    lid = cliente_http.post(f"{BASE}/loans", json={"clientId": cid, "principal": 3000}).json()["loanId"]
    assert cliente_http.post(f"{BASE}/loans/{lid}?command=approve").status_code == 200
    assert cliente_http.post(f"{BASE}/loans/{lid}?command=disburse").status_code == 200
    assert llamadas == [f"{BASE}/loans/{lid}"]
    assert seed["loanId"] != lid


def test_espejo_registra_el_error_si_fineract_no_responde(monkeypatch):
    monkeypatch.setenv("CORE_ESPEJO", "1")
    from cuotaflex.api.routers import core_fineract

    def falla(_):
        raise RuntimeError("Fineract no disponible")

    monkeypatch.setattr(core_fineract, "crear_espejo", falla)
    r = espejo_automatico.replicar(123)
    assert r["ok"] is False and "no disponible" in r["error"]
    assert espejo_automatico.programar(f"{BASE}/loans/7", sincrono=True) is True
    monkeypatch.setenv("CORE_ESPEJO", "0")
    assert espejo_automatico.programar(f"{BASE}/loans/7") is False
