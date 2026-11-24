"""Fase 2 · Lote A: calibración, selección por simulación, recargo por producto y contratos."""
import copy
import time

import numpy as np
from fastapi.testclient import TestClient

from cuotaflex.agente import AgenteAsesor
from cuotaflex.api.main import app
from cuotaflex.config import cargar_parametros
from cuotaflex.datos import generar_cartera
from cuotaflex.politica import recargo_producto
from cuotaflex.seleccion import elegir, escenarios_desde_pronostico
from cuotaflex.simulacion import comparar_cartera

PAR = cargar_parametros()


def test_cartera_calibrada_en_rango_objetivo():
    _, s = comparar_cartera(200, 100, semilla=2026)
    assert 7 <= s["fija"]["mora30_pct"] <= 13, s["fija"]
    assert 2.5 <= s["fija"]["default_pct"] <= 6, s["fija"]


def test_comparar_cartera_mantiene_contrato():
    _, s = comparar_cartera(30, 20, semilla=5, metodo_pronostico="perfil", par=copy.deepcopy(PAR), replanificar=False)
    assert {"fija", "cuotaflex", "delta", "por_rubro", "mix_productos"} <= set(s)
    assert {"mora30_pct", "default_pct", "margen_neto_total", "cartera", "margen_sobre_cartera_pct"} <= set(s["fija"])


def test_cuotaflex_no_empeora_a_la_cartera():
    _, s = comparar_cartera(200, 100, semilla=11)
    assert s["cuotaflex"]["default_pct"] < s["fija"]["default_pct"]
    assert s["cuotaflex"]["margen_sobre_cartera_pct"] > s["fija"]["margen_sobre_cartera_pct"]


def test_seleccion_nunca_elige_mas_default_que_fija():
    clientes, hist = generar_cartera(25, semilla=13)
    ag = AgenteAsesor()
    for c in clientes.to_dict("records"):
        p = ag.proponer(c, hist)
        sel = [b for b in p["bitacora"] if b["paso"] == "seleccion"]
        if sel:
            cand = sel[0]["candidatos"]
            assert cand[p["producto"]]["default"] <= cand["fija"]["default"]
            assert p["producto"] == sel[0]["elegido"]
        assert p["valido"]


def test_regla_de_eleccion():
    m = {"fija": {"default": .05, "mora30": .1, "vpn": 100},
         "aplazamiento": {"default": .02, "mora30": .05, "vpn": 90},   # pierde 10% de VPN: no factible
         "estacional": {"default": .03, "mora30": .06, "vpn": 98}}
    assert elegir(m, 5) == "estacional"
    assert elegir(m, 15) == "aplazamiento"


def test_caso_calzado_fase1_ya_no_empeora():
    c = TestClient(app)
    cli = next(x for x in c.get("/motor/cartera-demo?n=30&semilla=7").json() if x["cliente_id"] == "C00000")
    d = c.post("/motor/propuesta", json=cli).json()["comparativa"]
    assert d["cuotaflex"]["default"] <= d["fija"]["default"]
    assert d["cuotaflex"]["mora30"] <= d["fija"]["mora30"]


def test_propuesta_individual_rapida():
    c = TestClient(app)
    cart = c.get("/motor/cartera-demo?n=30&semilla=7").json()
    c.post("/motor/propuesta", json=cart[0])  # calentamiento
    for cli in cart[1:6]:
        t = time.time()
        assert c.post("/motor/propuesta", json=cli).status_code == 200
        assert time.time() - t < 2.0


def test_recargo_por_producto_y_clave_historica():
    par = copy.deepcopy(PAR)
    par["recargo"] = {"estacional": None, "aplazamiento": None}
    par["flexibilidad"]["recargo_spread_tea"] = 0.03
    assert recargo_producto(par, "estacional") == 0.03 and recargo_producto(par, "fija") == 0.0
    par["recargo"]["estacional"] = 0.0
    assert recargo_producto(par, "estacional") == 0.0 and recargo_producto(par, "aplazamiento") == 0.03


def test_escenarios_desde_pronostico_respetan_cuantiles():
    q = np.array([[80.0] * 6, [90.0] * 6, [100.0] * 6, [125.0] * 6])
    v = escenarios_desde_pronostico(q, 20000, np.random.default_rng(0))
    assert abs(np.median(v) - 100) < 2
    cob = np.mean((v >= 80) & (v <= 125))
    assert 0.75 < cob < 0.85
