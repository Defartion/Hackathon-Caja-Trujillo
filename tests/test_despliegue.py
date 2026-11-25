"""Despliegue en una sola URL (server.py): API en /api, apps en /asesor, /cliente y /tablero."""
import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def servidor(monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_SEMBRAR_DEMO", "0")
    sys.modules.pop("server", None)
    import server
    return TestClient(importlib.reload(server).app, follow_redirects=False)


def test_rutas_de_las_apps_y_la_api(servidor):
    assert servidor.get("/").headers["location"] == "/asesor/"
    assert servidor.get("/tablero").headers["location"] == "/tablero/"
    assert servidor.get("/api/auth/config").status_code == 200
    assert servidor.get("/otra/cosa").status_code == 404
    for app in ("asesor", "cliente", "tablero"):
        r = servidor.get(f"/{app}/")
        assert r.status_code in (200, 503)  # 503 solo si no se compilaron las apps en public/
    r = servidor.get("/asesor/no/existe/../../../server.py")
    assert r.status_code in (200, 404, 503) and "def estatico" not in r.text  # nunca sirve archivos fuera de public/


def test_login_funciona_bajo_el_prefijo_api(servidor, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_AUTH", "1")
    assert servidor.get("/api/auth/config").json()["auth"] is True
    assert servidor.get("/api/motor/cartera-demo?n=2").status_code == 401
    tok = servidor.post("/api/auth/login", json={"rol": "asesor", "pin": "1111"}).json()["token"]
    assert servidor.get("/api/motor/cartera-demo?n=2", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
