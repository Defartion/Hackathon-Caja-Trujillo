import copy

import pytest
from fastapi.testclient import TestClient

from cuotaflex import simulacion
from cuotaflex.api.main import app
from cuotaflex.api.routers import simulacion as ruta_sim
from cuotaflex.config import cargar_parametros

c = TestClient(app)

RUTAS = {
    "flexibilidad.max_aplazamientos", "flexibilidad.cuota_minima_pct", "flexibilidad.cuota_maxima_mult",
    "flexibilidad.recargo_spread_tea", "flexibilidad.requisito_dias_atraso_max",
    "capacidad_pago.ratio_cuota_excedente_max", "capacidad_pago.ratio_deuda_total_max",
    "el_nino.probabilidad_anual", "el_nino.meses_alivio", "simulacion.fuga_caja_mensual",
}
PEQUENA = {"n_clientes": 30, "n_escenarios": 20, "semilla": 7}


@pytest.fixture(autouse=True)
def secuencial(monkeypatch):
    """Por defecto, todo en el proceso de la prueba (sin procesos trabajadores)."""
    monkeypatch.setenv("CUOTAFLEX_SIM_PROCESOS", "0")


def correr(**cuerpo):
    r = c.post("/simulacion/correr", json={**PEQUENA, **cuerpo})
    assert r.status_code == 200, r.text
    return r.json()


def test_parametros_editables_devuelve_las_10_rutas():
    r = c.get("/simulacion/parametros-editables")
    assert r.status_code == 200
    filas = r.json()
    assert {f["ruta"] for f in filas} == RUTAS and len(filas) == 10
    par = cargar_parametros()
    for f in filas:
        assert {"etiqueta", "minimo", "maximo", "paso", "valor", "ayuda"} <= set(f)
        seccion, clave = f["ruta"].split(".")
        assert f["valor"] == par[seccion][clave]
        assert f["minimo"] <= f["valor"] <= f["maximo"]


def test_escenarios_predefinidos_usan_rutas_editables():
    esc = {e["id"]: e for e in c.get("/simulacion/escenarios").json()}
    assert {"base", "el_nino", "sin_flexibilidad", "ahorrador", "estricta"} == set(esc)
    assert esc["base"]["cambios"] == {}
    assert esc["el_nino"]["cambios"] == {"el_nino.probabilidad_anual": 1.0}
    assert esc["sin_flexibilidad"]["cambios"]["flexibilidad.cuota_minima_pct"] == 0.95
    for e in esc.values():
        assert set(e["cambios"]) <= RUTAS


def test_correr_devuelve_resumen_histograma_y_dispersion():
    d = correr(cambios={"flexibilidad.max_aplazamientos": 3})
    assert {"fija", "cuotaflex", "delta"} <= set(d["resumen"])
    h = d["histograma_vpn"]
    assert len(h["bordes"]) == 21 and len(h["fija"]) == 20 and len(h["cuotaflex"]) == 20
    assert sum(h["fija"]) == sum(h["cuotaflex"]) == 30
    assert len(d["dispersion"]) == 30
    assert all(0 <= p["mora_fija"] <= 1 and 0 <= p["mora_flex"] <= 1 for p in d["dispersion"])
    assert set(d["parametros_usados"]) == RUTAS
    assert d["parametros_usados"]["flexibilidad.max_aplazamientos"] == 3
    assert d["duracion_s"] >= 0 and d["desde_cache"] is False


@pytest.mark.parametrize("cuerpo", [
    {"cambios": {"credito.tea_base": 0.9}},                   # ruta no editable
    {"cambios": {"el_nino.probabilidad_anual": 1.5}},         # fuera del rango válido
    {"cambios": {"flexibilidad.max_aplazamientos": 2.5}},     # debe ser entero
    {"n_clientes": 601},
    {"n_escenarios": 301},
])
def test_consulta_no_permitida_responde_422(cuerpo):
    assert c.post("/simulacion/correr", json={**PEQUENA, **cuerpo}).status_code == 422


def test_la_configuracion_global_no_se_altera():
    antes = copy.deepcopy(cargar_parametros())
    cambios = {"flexibilidad.max_aplazamientos": 4, "flexibilidad.cuota_minima_pct": 0.95,
               "el_nino.probabilidad_anual": 1.0, "simulacion.fuga_caja_mensual": 0.0}
    d = correr(semilla=11, cambios=cambios)
    assert cargar_parametros() == antes
    for ruta, valor in cambios.items():
        assert d["parametros_usados"][ruta] == valor


def test_segunda_llamada_identica_sale_de_la_cache(monkeypatch):
    llamadas = []
    original = simulacion.comparar_cartera

    def contar(*a, **k):
        llamadas.append(a)
        return original(*a, **k)

    monkeypatch.setattr(simulacion, "comparar_cartera", contar)
    cuerpo = {"semilla": 99, "replanificar": False, "cambios": {"flexibilidad.cuota_minima_pct": 0.4}}
    a = correr(**cuerpo)
    b = c.post("/simulacion/correr", json=dict(reversed(list({**PEQUENA, **cuerpo}.items())))).json()  # otro orden
    assert len(llamadas) == 1
    assert a["desde_cache"] is False and b["desde_cache"] is True
    assert a["resumen"] == b["resumen"]


def test_la_cache_guarda_como_maximo_50_corridas(monkeypatch):
    det_res = simulacion.comparar_cartera(10, 5, 1)
    monkeypatch.setattr(simulacion, "comparar_cartera", lambda *a, **k: det_res)  # corridas instantáneas
    for semilla in range(1000, 1000 + ruta_sim.MAX_CACHE + 5):
        correr(semilla=semilla)
    assert len(ruta_sim._cache) == ruta_sim.MAX_CACHE


def test_paralelo_da_exactamente_el_resultado_secuencial(monkeypatch):
    cuerpo = {"n_clientes": 60, "n_escenarios": 15, "semilla": 5, "cambios": {"el_nino.probabilidad_anual": 1.0}}
    secuencial = correr(**cuerpo)
    ruta_sim._cache.clear()
    monkeypatch.setenv("CUOTAFLEX_SIM_PROCESOS", "2")
    try:
        paralelo = correr(**cuerpo)
    finally:
        ruta_sim._descartar_pool()
    rend = paralelo["rendimiento"]
    assert rend["modo"] == "paralelo" and rend["procesos"] == 2
    assert rend["cronogramas_recalculados"] == 0 and rend["cronogramas_de_memoria"] > 0
    for k in ("resumen", "histograma_vpn", "dispersion"):
        assert paralelo[k] == secuencial[k]


def test_ano_el_nino_el_alivio_reduce_el_default():
    d = correr(n_clientes=80, n_escenarios=40, semilla=2026, cambios={"el_nino.probabilidad_anual": 1.0})
    assert d["resumen"]["cuotaflex"]["default_pct"] < d["resumen"]["fija"]["default_pct"]
