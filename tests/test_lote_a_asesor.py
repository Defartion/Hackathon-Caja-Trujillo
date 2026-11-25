from fastapi.testclient import TestClient

from cuotaflex.api.main import app
from cuotaflex.config import cargar_parametros

c = TestClient(app)


def _cliente(i=0):
    return c.get("/motor/cartera-demo?n=5&semilla=11").json()[i]


def test_cartera_demo():
    r = c.get("/motor/cartera-demo?n=8&semilla=3")
    assert r.status_code == 200
    filas = r.json()
    assert len(filas) == 3 + 8  # Los casos estrella no se descuentan de n.
    assert all(len(f["historial_ventas"]) == 24 for f in filas)
    assert all("indice_estacionalidad" in f for f in filas)
    assert c.get("/motor/cartera-demo?n=500").status_code == 422


def test_propuesta_completa():
    r = c.post("/motor/propuesta", json=_cliente())
    assert r.status_code == 200, r.text
    d = r.json()
    plazo = d["propuesta"]["plazo"]
    assert len(d["propuesta"]["cronograma"]) == plazo
    assert set(d["pronostico"]) == {"p10", "p25", "p50", "p90"}
    assert all(len(v) == plazo for v in d["pronostico"].values())
    assert len(d["capacidad"]) == plazo
    for e in ("fija", "cuotaflex"):
        assert 0 <= d["comparativa"][e]["mora30"] <= 1
        assert 0 <= d["comparativa"][e]["default"] <= 1


def test_propuesta_sin_historial():
    cli = _cliente(1)
    cli.pop("historial_ventas")
    r = c.post("/motor/propuesta", json=cli)
    assert r.status_code == 200, r.text
    assert len(r.json()["historial_ventas"]) == 24


def test_propuesta_determinista_y_no_altera_config():
    antes = cargar_parametros()["flexibilidad"].copy()
    cli = _cliente(2)
    a, b = c.post("/motor/propuesta", json=cli).json(), c.post("/motor/propuesta", json=cli).json()
    assert a["comparativa"] == b["comparativa"]
    assert a["propuesta"]["cronograma"] == b["propuesta"]["cronograma"]
    assert cargar_parametros()["flexibilidad"] == antes


def test_rubro_invalido():
    cli = _cliente()
    cli["rubro"] = "minería"
    assert c.post("/motor/propuesta", json=cli).status_code == 422
