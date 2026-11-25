"""Fase 4 · Lote A: costos de la Caja, prelación, constructor por etapas, estrés y contrato."""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from cuotaflex.api.main import app
from cuotaflex.config import cargar_parametros
from cuotaflex.datos import generar_cartera
from cuotaflex.plan import proponer_plan
from cuotaflex.plan.adaptador import ciclo_desde_pronostico
from cuotaflex.plan.constructor import construir, cuota_fija
from cuotaflex.plan.costos import Estado, Seguros, aplicar_periodo, factor_interes, simular_cuotas, tcea, vencimientos
from cuotaflex.pronostico import pronosticar

FIX = Path(__file__).parent / "fixtures" / "contratos"
SIN_SEG = Seguros()


def _sol():
    sol = json.loads((FIX / "plan_proponer_solicitud.json").read_text(encoding="utf-8"))
    sol["ciclo"] = json.loads((FIX / "ciclo_estimar_respuesta.json").read_text(encoding="utf-8"))
    return sol


def test_ted_base_360_por_dias_exactos():
    assert factor_interes(0.45, 31) == pytest.approx(1.45 ** (31 / 360) - 1)
    assert factor_interes(0.45, 360) == pytest.approx(0.45)
    mov, _ = aplicar_periodo(Estado(1000.0), 0, 28, 0.45, SIN_SEG)
    assert mov["interes"] == pytest.approx(1000 * (1.45 ** (28 / 360) - 1))


def test_vencimientos_fin_de_mes():
    assert vencimientos(date(2027, 1, 31), 3) == [date(2027, 2, 28), date(2027, 3, 31), date(2027, 4, 30)]


def test_prelacion_y_pendientes_sin_capitalizar():
    seg = Seguros(desgravamen_tasa_mensual=0.001)
    e0 = Estado(1000.0)
    mov, e1 = aplicar_periodo(e0, 5.0, 30, 0.45, seg)          # no alcanza ni para seguros + interés
    assert mov["pago_seguros"] == pytest.approx(1.0) and mov["capital"] == 0
    assert e1.saldo_capital == 1000.0 and e1.pendiente_interes > 0
    mov2, e2 = aplicar_periodo(e1, 0.0, 30, 0.45, seg)          # el pendiente no genera interés
    assert mov2["interes"] == pytest.approx(mov["interes"])
    assert e2.pendiente_interes == pytest.approx(e1.pendiente_interes + mov2["interes"])
    _, e3 = aplicar_periodo(e2, e2.deuda + 50, 30, 0.45, seg)   # primero los pendientes, luego capital
    assert e3.pendiente_interes == 0 and e3.pendiente_seguros == 0 and e3.saldo_capital < 1000


def test_conservacion_de_pagos():
    seg = Seguros(0.00077, 0.0003, 20000)
    filas = simular_cuotas(5000, 0.45, date(2026, 12, 1), [0, 0, 800, 1500, 900, 400, 1200, 900], seg)
    pagado = sum(f.cuota for f in filas)
    generado = 5000 + sum(f.interes + f.seguro_desgravamen + f.seguro_multirriesgo for f in filas)
    assert pagado == pytest.approx(generado, abs=0.01) and filas[-1].saldo_deuda == pytest.approx(0, abs=1e-6)


def test_tcea_igual_a_tea_sin_seguros_en_cuota_fija():
    filas = cuota_fija(10000, 0.45, date(2026, 12, 1), 12, SIN_SEG)
    assert tcea(10000, date(2026, 12, 1), filas) == pytest.approx(0.45, abs=0.001)


def test_contrato_identico_al_ejemplo():
    r = proponer_plan(_sol())
    ref = json.loads((FIX / "plan_proponer_respuesta.json").read_text(encoding="utf-8"))
    for k in ("factible", "plan", "plan_cuota_fija", "estres", "ajustes_sugeridos", "supuestos"):
        assert k in r
    assert set(ref["plan"]["resumen"]) <= set(r["plan"]["resumen"])
    assert set(ref["plan"]["periodos"][0]) <= set(r["plan"]["periodos"][0])
    assert set(ref["estres"][0]["adaptado"]) <= set(r["estres"][0]["adaptado"])
    json.dumps(r)  # serializable sin tipos de NumPy


def test_rosa_cuotas_en_cosecha_y_cumple_factor():
    r = proponer_plan(_sol())
    plan, fija = r["plan"], r["plan_cuota_fija"]
    assert r["factible"] and plan["resumen"]["cumple_factor"] and not fija["resumen"]["cumple_factor"]
    assert plan["periodos"][-1]["saldo_deuda"] == 0
    assert all(p["cuota"] == 0 for p in plan["periodos"] if p["etapa"] == "valle")
    assert plan["resumen"]["interes_total"] < fija["resumen"]["interes_total"]
    base = next(e for e in r["estres"] if e["escenario"] == "base")
    assert base["adaptado"]["etapas_sobre_factor"] == 0
    for e in r["estres"]:
        assert e["adaptado"]["monto_sobre_capacidad"] <= e["fija"]["monto_sobre_capacidad"] + 0.01


def test_propiedad_ningun_plan_factible_supera_el_factor():
    par = cargar_parametros()
    cli, hist = generar_cartera(60, semilla=4, par=par)
    q = pronosticar(cli.assign(plazo=24), hist)
    for c in cli.to_dict("records"):
        ciclo = ciclo_desde_pronostico(c, q[c["cliente_id"]], date(2026, 12, 1), par, meses=c["plazo"])
        for factor in (0.65, 0.85):
            r = proponer_plan({"monto": c["principal"], "tea": c["tea"], "fecha_desembolso": "2026-12-01",
                               "plazo_meses": c["plazo"], "producto": {"factor": factor}, "ciclo": ciclo,
                               "seguros": {"desgravamen": {"activo": True, "tasa_mensual": 0.00077}}})
            if r["factible"]:
                for p in r["plan"]["periodos"]:
                    if p["cuota"] > 0:
                        assert p["un_esperada"] > 0 and p["cuota"] <= factor * p["un_esperada"] + 0.01
                assert r["plan"]["periodos"][-1]["saldo_deuda"] == 0
            else:
                assert r["ajustes_sugeridos"]


def test_no_factible_sugiere_ajustes_que_funcionan():
    sol = _sol()
    sol["monto"] = 30000
    r = proponer_plan(sol)
    assert not r["factible"] and r["plan"] is None and r["plan_cuota_fija"]
    tipos = {a["tipo"]: a for a in r["ajustes_sugeridos"]}
    assert "reducir_monto" in tipos
    sol["monto"] = tipos["reducir_monto"]["monto_maximo"]
    assert proponer_plan(sol)["factible"]


def test_producto_del_catalogo_y_validaciones():
    c = TestClient(app)
    sol = _sol()
    sol["producto"] = {"id": "inclusion"}
    r = c.post("/plan/proponer", json=sol)
    assert r.status_code == 200 and "0.65" in " ".join(r.json()["supuestos"])
    sol["producto"] = {"factor": 0.85, "tope_tea": 0.40}
    assert c.post("/plan/proponer", json=sol).status_code == 422
    sol.pop("ciclo")
    assert c.post("/plan/proponer", json=sol).status_code == 422


def test_rapido():
    import time
    t = time.time()
    proponer_plan(_sol())
    assert time.time() - t < 2.0
