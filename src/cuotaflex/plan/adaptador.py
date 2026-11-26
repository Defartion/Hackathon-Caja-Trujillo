"""Adaptador: arma un `ciclo` con la forma del contrato a partir del pronóstico de la fase 2.

Sirve para medir la cartera sintética y para la demo mientras el modelo de ciclo del lote B no
esté integrado. La UN esperada es ventas × margen − gasto familiar − otras cuotas (ya descontada la
carga familiar y las otras deudas, como pide la FAQ).
"""
from __future__ import annotations

from datetime import date

import numpy as np

from .costos import sumar_meses


def ciclo_desde_pronostico(cli: dict, q: np.ndarray, desembolso: date, par: dict, meses: int | None = None) -> dict:
    meses = meses or q.shape[1]
    q = q[:, :meses]
    un = lambda v: v * cli["margen"] - cli["gasto_familiar"] - cli["otras_cuotas"]
    p50 = un(q[2])
    med = float(np.median(p50))
    periodos = []
    for k in range(meses):
        f = sumar_meses(desembolso, k + 1)
        etapa = "cima" if p50[k] >= 1.25 * med else ("valle" if p50[k] <= 0.75 * med or p50[k] <= 0 else "normal")
        periodos.append({"periodo": f"{f.year}-{f.month:02d}", "etapa": etapa, "ventas_p50": round(float(q[2][k]), 2),
                         "un_p10": round(float(un(q[0][k])), 2), "un_p50": round(float(p50[k]), 2), "un_p90": round(float(un(q[3][k])), 2)})
    caida = par["el_nino"]["caida_ingresos"].get(cli["rubro"], 0.05)
    escenarios = [
        {"id": "base", "nombre": "Esperado", "un": [p["un_p50"] for p in periodos]},
        {"id": "el_nino", "nombre": f"El Niño costero (ventas −{caida:.0%})", "un": [round(float(un(v * (1 - caida))), 2) for v in q[2]]},
        {"id": "retraso", "nombre": "Temporada alta 1 mes tarde", "un": [periodos[0]["un_p50"]] + [p["un_p50"] for p in periodos[:-1]]},
        {"id": "caida_precios", "nombre": "Ventas −20%", "un": [round(float(un(v * 0.8)), 2) for v in q[2]]},
    ]
    return {"cliente_id": cli["cliente_id"], "sector": cli["rubro"], "actividad": cli["rubro"], "zona": {"departamento": "La Libertad",
            "provincia": cli.get("region"), "distrito": None}, "fecha_inicio": desembolso.isoformat(), "meses": meses,
            "periodos": periodos, "escenarios": escenarios,
            "supuestos": ["Ciclo derivado del pronóstico de la fase 2 (adaptador provisional hasta integrar el lote B)"],
            "fuentes": [], "calidad": {"metodo": "adaptador_pronostico_fase2", "cobertura_p10_p90_backtest": 0.795}}
