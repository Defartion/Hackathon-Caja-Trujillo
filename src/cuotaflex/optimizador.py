"""Optimización del cronograma de cuotas (programación entera mixta con CVXPY).

Decide el monto de cada cuota para que:
- el valor presente de las cuotas cierre exactamente el crédito (rentabilidad preservada),
- cada cuota quepa en la capacidad de pago del escenario conservador (p25),
- ninguna cuota baje del piso ni supere el techo (evita cuotas globo),
- el número de meses con cuota reducida esté acotado por política.
"""
from __future__ import annotations

import math

import cvxpy as cp
import numpy as np

from .config import cargar_parametros, cuota_francesa, factores_descuento


def optimizar_cronograma(principal: float, tem: float, capacidad: np.ndarray,
                         par: dict | None = None, suavidad: float = 0.02) -> dict:
    """capacidad: monto máximo pagable por mes (ya aplicado el ratio de política)."""
    par = par or cargar_parametros()
    fx = par["flexibilidad"]
    n = len(capacidad)
    ref = cuota_francesa(principal, tem, n)
    piso, techo = fx["cuota_minima_pct"] * ref, fx["cuota_maxima_mult"] * ref
    umbral = (1 - fx["tolerancia_reduccion"]) * ref
    max_red = fx["max_meses_reducidos_anio"] * math.ceil(n / 12)

    c = cp.Variable(n)
    deficit = cp.Variable(n, nonneg=True)
    z = cp.Variable(n, boolean=True)
    d = factores_descuento(tem, n)
    restricciones = [
        d @ c == principal,
        c >= piso, c <= techo,
        c - deficit <= capacidad,
        c >= umbral - (umbral - piso) * z,
        cp.sum(z) <= max_red,
    ]
    # Prioridad 1: que nada exceda la capacidad. Prioridad 2: parecerse a la cuota fija.
    objetivo = cp.Minimize(cp.sum(deficit) / ref * 100 + suavidad * cp.sum(cp.abs(c - ref)) / ref)
    prob = cp.Problem(objetivo, restricciones)
    try:
        prob.solve(solver=cp.HIGHS)
    except Exception:
        prob.solve()
    if c.value is None:
        return {"estado": prob.status, "cuotas": np.full(n, ref), "deficit_total": float("nan"), "cuota_fija": ref}
    cuotas = np.asarray(c.value).round(2)
    # ajuste de redondeo en la última cuota para cerrar el VP exacto
    cuotas[-1] += round((principal - d @ cuotas) / d[-1], 2)
    return {
        "estado": prob.status,
        "cuotas": cuotas,
        "cuota_fija": round(ref, 2),
        "deficit_total": round(float(np.sum(np.maximum(cuotas - capacidad, 0))), 2),
        "meses_reducidos": int(np.sum(cuotas < umbral - 0.5)),
    }
