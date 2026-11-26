"""Cifras para concepto y pitch: Cuota/UN por etapa, cuota fija vs. plan por etapas (fase 4, lote A).

Mismo monto, TEA y plazo que pidió cada cliente sintético. UN esperada de cada mes según el pronóstico.
Salida: resultados/factor_por_etapa.md y .json.  Uso: python scripts/factor_por_etapa.py [--clientes 600]
"""
import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
warnings.filterwarnings("ignore")

from cuotaflex.config import cargar_parametros  # noqa: E402
from cuotaflex.datos import generar_cartera  # noqa: E402
from cuotaflex.plan import proponer_plan  # noqa: E402
from cuotaflex.plan.adaptador import ciclo_desde_pronostico  # noqa: E402
from cuotaflex.pronostico import pronosticar  # noqa: E402

DESEMBOLSO = date(2026, 12, 1)
SEGUROS = {"desgravamen": {"activo": True, "tasa_mensual": 0.00077}, "multirriesgo": {"activo": False}}


def main(n):
    par = cargar_parametros()
    cli, hist = generar_cartera(n, 2026, par=par)
    q = pronosticar(cli.assign(plazo=24), hist)
    filas = []
    for c in cli.to_dict("records"):
        ciclo = ciclo_desde_pronostico(c, q[c["cliente_id"]], DESEMBOLSO, par, meses=c["plazo"])
        for factor in (0.65, 0.85):
            r = proponer_plan({"monto": c["principal"], "tea": c["tea"], "fecha_desembolso": DESEMBOLSO.isoformat(),
                               "plazo_meses": c["plazo"], "producto": {"factor": factor, "max_meses_gracia": 4},
                               "seguros": SEGUROS, "ciclo": ciclo, "comparar_cuota_fija": True})
            fija, plan = r["plan_cuota_fija"]["resumen"], (r["plan"] or {}).get("resumen")
            est = {e["escenario"]: e for e in r["estres"]}
            filas.append({"rubro": c["rubro"], "factor": factor, "factible": r["factible"],
                          "fija_viola": not fija["cumple_factor"], "fija_etapas": fija["etapas_sobre_factor"],
                          "plan_viola": (not plan["cumple_factor"]) if plan else None,
                          "fija_interes": fija["interes_total"], "plan_interes": plan["interes_total"] if plan else None,
                          "fija_tcea": fija["tcea"], "plan_tcea": plan["tcea"] if plan else None,
                          "plan_gracia": plan["meses_gracia"] if plan else None,
                          "monto_max": next((a["monto_maximo"] for a in r["ajustes_sugeridos"] if a["tipo"] == "reducir_monto"), None),
                          "principal": c["principal"],
                          **{f"fija_{k}": est[k]["fija"]["etapas_sobre_factor"] > 0 for k in est},
                          **{f"plan_{k}": (est[k]["adaptado"]["etapas_sobre_factor"] > 0) if est[k]["adaptado"] else None for k in est},
                          **{f"fijaexc_{k}": est[k]["fija"]["monto_sobre_capacidad"] for k in est},
                          **{f"planexc_{k}": est[k]["adaptado"]["monto_sobre_capacidad"] if est[k]["adaptado"] else None for k in est}})
    d = pd.DataFrame(filas)
    res = {}
    for factor, g in d.groupby("factor"):
        f = g[g.factible]
        res[str(factor)] = {
            "clientes": len(g), "factibles_pct": round(100 * g.factible.mean(), 1),
            "fija_viola_pct": round(100 * g.fija_viola.mean(), 1),
            "plan_viola_pct_factibles": round(100 * f.plan_viola.mean(), 1) if len(f) else None,
            "fija_viola_pct_en_factibles": round(100 * f.fija_viola.mean(), 1) if len(f) else None,
            "estres_pct_factibles": {k: {"fija": round(100 * f[f"fija_{k}"].mean(), 1), "plan": round(100 * f[f"plan_{k}"].mean(), 1),
                                         "exceso_fija": round(f[f"fijaexc_{k}"].mean(), 0), "exceso_plan": round(f[f"planexc_{k}"].mean(), 0)}
                                     for k in ("el_nino", "retraso", "caida_precios")},
            "interes_medio": {"fija": round(f.fija_interes.mean(), 0), "plan": round(f.plan_interes.mean(), 0)},
            "tcea_media": {"fija": round(100 * f.fija_tcea.mean(), 2), "plan": round(100 * f.plan_tcea.mean(), 2)},
            "gracia_media": round(f.plan_gracia.mean(), 2),
            "no_factibles_monto_max_vs_pedido_pct": round(100 * (g[~g.factible].monto_max.fillna(0) / g[~g.factible].principal).mean(), 1) if (~g.factible).any() else None,
            "por_rubro": {r: {"factible_pct": round(100 * x.factible.mean(), 1), "fija_viola_pct": round(100 * x.fija_viola.mean(), 1)}
                          for r, x in g.groupby("rubro")},
        }
    out = RAIZ / "resultados"
    (out / "factor_por_etapa.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    L = ["# Cuota / Utilidad Neta por etapa: cuota fija vs. plan por etapas", "",
         f"{n} clientes sintéticos (semilla 2026), mismo monto, TEA y plazo que pidieron; desembolso {DESEMBOLSO:%d/%m/%Y}; "
         "TED base 360 por días exactos, desgravamen 0.077% mensual, prelación seguros → interés → capital; "
         "UN esperada de cada mes según el pronóstico (adaptador provisional hasta integrar el modelo de ciclo del lote B). "
         "El plan cumple el factor como restricción dura en el escenario esperado y, además, minimiza el monto que excedería la "
         "capacidad en los escenarios adversos (robustez).", ""]
    for factor, r in res.items():
        L += [f"## Factor {factor}", "",
              "| Métrica | Cuota fija | Plan por etapas |", "|---|---:|---:|",
              f"| Clientes con alguna etapa sobre el factor (todos) | {r['fija_viola_pct']}% | 0% en los planes propuestos |",
              f"| Clientes con plan factible al monto pedido | — | {r['factibles_pct']}% |",
              f"| En los factibles: clientes con alguna etapa sobre el factor | {r['fija_viola_pct_en_factibles']}% | {r['plan_viola_pct_factibles']}% |"]
        for k, nombre in (("el_nino", "El Niño"), ("retraso", "Temporada alta 1 mes tarde"), ("caida_precios", "Ventas −20%")):
            e = r["estres_pct_factibles"][k]
            L.append(f"| Escenario {nombre}: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ {e['exceso_fija']:,.0f} | S/ {e['exceso_plan']:,.0f} |")
            L.append(f"| Escenario {nombre}: clientes con alguna etapa sobre el factor | {e['fija']}% | {e['plan']}% |")
        L += [f"| Interés total medio (factibles) | S/ {r['interes_medio']['fija']:,.0f} | S/ {r['interes_medio']['plan']:,.0f} |",
              f"| TCEA media (factibles) | {r['tcea_media']['fija']}% | {r['tcea_media']['plan']}% |",
              f"| Meses de gracia promedio | — | {r['gracia_media']} |", ""]
        if r["no_factibles_monto_max_vs_pedido_pct"] is not None:
            L += [f"Cuando no hay plan factible al monto pedido, el motor sugiere en promedio un monto máximo del "
                  f"{r['no_factibles_monto_max_vs_pedido_pct']}% de lo solicitado, o un plazo mayor.", ""]
        L += ["| Rubro | Plan factible | Cuota fija sobre el factor |", "|---|---:|---:|"]
        L += [f"| {rub} | {v['factible_pct']}% | {v['fija_viola_pct']}% |" for rub, v in r["por_rubro"].items()]
        L.append("")
    (out / "factor_por_etapa.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=600)
    main(ap.parse_args().clientes)
