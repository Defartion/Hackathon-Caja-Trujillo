"""Constructor del plan de pagos desde el ciclo económico (fase 4, FAQ NEG-01).

Programación entera mixta (CVXPY + HiGHS) sobre una grilla mensual:
- Restricción dura de capacidad: cuota_t ≤ factor × UN_t (UN_t ≤ 0 ⇒ cuota_t = 0).
- Prelación: solo se amortiza capital en un periodo si no queda nada pendiente (seguros + interés).
- Lo pendiente no capitaliza: el interés y los seguros se generan solo sobre el saldo de capital.
- La deuda queda en 0 al final del plazo; a lo más `max_meses_gracia` periodos con pendientes.
- Objetivo: mínimo costo total (interés + seguros), lo que equivale a amortizar el máximo en la cima.
  Desempate suave: menos meses de gracia y cuotas menos bruscas.
Si no hay plan factible, propone el monto máximo y el plazo mínimo que sí lo son.
"""
from __future__ import annotations

import math
from datetime import date

import cvxpy as cp
import numpy as np

from .costos import Periodo, Seguros, factor_interes, simular_cuotas, tcea, vencimientos

HOLGURA = 0.50          # S/ de margen bajo el tope, para que el redondeo a céntimos nunca supere el factor
PLAZO_MAXIMO = 36
PESO_ESTRES = 2.0       # S/ de penalidad por cada S/ que la cuota exceda la capacidad en un escenario adverso (promedio)


def _extender(un: list[float], n: int) -> list[float]:
    """Si el plazo supera el ciclo, repite el patrón anual (UN de 12 meses antes)."""
    un = list(un)
    while len(un) < n:
        un.append(un[len(un) - 12] if len(un) >= 12 else un[-1])
    return un[:n]


def _resolver(monto: float, tea: float, desembolso: date, un: list[float], factor: float, seguros: Seguros,
              max_gracia: int, adversos: list[list[float]] | None = None, peso_estres: float = PESO_ESTRES) -> np.ndarray | None:
    """Base: restricción dura con la UN esperada. Adversos: penalidad (robustez) por exceder factor × UN_adversa."""
    n = len(un)
    fechas = vencimientos(desembolso, n)
    dias = np.diff([desembolso.toordinal()] + [f.toordinal() for f in fechas])
    tasa = np.array([factor_interes(tea, int(d)) + seguros.desgravamen_tasa_mensual / 30 * d for d in dias])
    fijo = np.array([seguros.multirriesgo(int(d)) for d in dias])
    tope = np.array([max(factor * u - HOLGURA, 0.0) if u > 0 else 0.0 for u in un])
    if tope.sum() < monto:
        return None
    M = monto * 3 + fijo.sum() + 1
    K = cp.Variable(n + 1)                 # saldo de capital al cierre de cada periodo
    cap = cp.Variable(n, nonneg=True)      # amortización de capital
    y = cp.Variable(n, nonneg=True)        # pago de cargos (seguros + interés, incluidos pendientes)
    P = cp.Variable(n + 1, nonneg=True)    # cargos pendientes
    g = cp.Variable(n, boolean=True)       # 1 = periodo con pendientes (gracia)
    cargos = cp.multiply(tasa, K[:-1]) + fijo
    c = y + cap
    restr = [K[0] == monto, P[0] == 0, K[1:] == K[:-1] - cap, P[1:] == P[:-1] + cargos - y,
             K >= 0, c <= tope, P[1:] <= M * g, cap <= M * (1 - g), cp.sum(g) <= max_gracia,
             K[n] == 0, P[n] == 0]
    escala = max(monto, 1.0)
    penal_estres = 0
    if adversos:
        caps = np.array([[max(factor * u, 0.0) for u in _extender(a, n)] for a in adversos])
        exceso = cp.Variable(caps.shape, nonneg=True)
        restr.append(exceso >= cp.vstack([c] * len(adversos)) - caps)
        penal_estres = peso_estres * cp.sum(exceso) / len(adversos)
    objetivo = cp.Minimize(cp.sum(cargos) + penal_estres + 1e-3 * escala * cp.sum(g) / n + 1e-4 * cp.sum(cp.abs(cp.diff(c))))
    prob = cp.Problem(objetivo, restr)
    try:
        prob.solve(solver=cp.HIGHS)
    except Exception:
        return None
    if prob.status not in ("optimal", "optimal_inaccurate") or c.value is None:
        return None
    return np.maximum(np.floor(np.asarray(c.value) * 100 + 1e-6) / 100, 0.0)


def _cerrar(monto: float, tea: float, desembolso: date, cuotas: np.ndarray, seguros: Seguros) -> list[Periodo]:
    """Simula con prelación; la última cuota positiva cancela el residuo de redondeo y el plan se corta ahí."""
    ult = int(np.nonzero(cuotas > 0)[0].max()) if (cuotas > 0).any() else len(cuotas) - 1
    filas = simular_cuotas(monto, tea, desembolso, list(cuotas[: ult + 1]), seguros, cerrar_en_ultima=True)
    return filas


def cuota_fija(monto: float, tea: float, desembolso: date, n: int, seguros: Seguros) -> list[Periodo]:
    """Cuota constante que cancela al final con días exactos y la misma prelación (referencia justa)."""
    lo, hi = 0.0, monto * 2
    for _ in range(80):
        cuota = (lo + hi) / 2
        filas = simular_cuotas(monto, tea, desembolso, [cuota] * n, seguros, cerrar_en_ultima=False)
        lo, hi = (cuota, hi) if filas[-1].saldo_deuda > 0 else (lo, cuota)
    cuota = round(hi, 2)
    return simular_cuotas(monto, tea, desembolso, [cuota] * n, seguros, cerrar_en_ultima=True)


def _monto_maximo(tea, desembolso, un, factor, seguros, max_gracia, monto) -> float:
    """Máximo monto con plan factible (solo la restricción dura del escenario esperado)."""
    lo, hi = 0.0, monto
    if _resolver(100.0, tea, desembolso, un, factor, seguros, max_gracia) is None:
        return 0.0
    for _ in range(14):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _resolver(mid, tea, desembolso, un, factor, seguros, max_gracia) is not None else (lo, mid)
    return math.floor(lo / 50) * 50


def construir(monto: float, tea: float, desembolso: date, plazo: int, un: list[float], factor: float,
              seguros: Seguros, max_gracia: int, adversos: list[list[float]] | None = None,
              peso_estres: float = PESO_ESTRES) -> dict:
    """Devuelve {'factible', 'cuotas' (np.ndarray) o None, 'ajustes', 'bitacora'}."""
    bitacora = [{"paso": "restriccion", "detalle": f"cuota ≤ {factor} × UN esperada en cada periodo; "
                 f"hasta {max_gracia} periodos de gracia"}]
    un_plazo = _extender(un, plazo)
    adv = [_extender(a, plazo) for a in (adversos or [])]
    cuotas = _resolver(monto, tea, desembolso, un_plazo, factor, seguros, max_gracia, adv, peso_estres)
    if adv:
        bitacora.append({"paso": "robustez", "detalle": f"penaliza excesos sobre la capacidad en {len(adv)} escenarios adversos"})
    if cuotas is not None:
        bitacora.append({"paso": "optimizacion", "estado": "factible", "plazo": plazo})
        return {"factible": True, "cuotas": cuotas, "ajustes": [], "bitacora": bitacora}
    bitacora.append({"paso": "optimizacion", "estado": "no factible", "plazo": plazo})
    ajustes = []
    maximo = _monto_maximo(tea, desembolso, un_plazo, factor, seguros, max_gracia, monto)
    if maximo > 0:
        ajustes.append({"tipo": "reducir_monto", "monto_maximo": maximo})
    for p in range(plazo + 1, PLAZO_MAXIMO + 1):
        if _resolver(monto, tea, desembolso, _extender(un, p), factor, seguros, max_gracia) is not None:
            ajustes.append({"tipo": "ampliar_plazo", "plazo_minimo": p})
            break
    bitacora.append({"paso": "ajustes", "sugeridos": ajustes})
    return {"factible": False, "cuotas": None, "ajustes": ajustes, "bitacora": bitacora}


def resumen(monto: float, desembolso: date, filas: list[Periodo], un: list[float], factor: float, tea: float) -> dict:
    sobre, ratios = 0, []
    for f, u in zip(filas, _extender(un, len(filas))):
        if f.cuota > 0:
            if u <= 0 or f.cuota > factor * u + 0.01:
                sobre += 1
            if u > 0:
                ratios.append(f.cuota / u)
    from .costos import ted
    return {"cuotas": len(filas), "total_pagado": round(float(sum(f.cuota for f in filas)), 2),
            "interes_total": round(float(sum(f.pago_interes for f in filas)), 2),
            "seguros_total": round(float(sum(f.pago_seguros for f in filas)), 2),
            "ted": round(ted(tea), 8), "tcea": round(tcea(monto, desembolso, filas), 4),
            "ratio_max": round(float(max(ratios)), 3) if ratios else None, "etapas_sobre_factor": sobre,
            "cumple_factor": sobre == 0,
            "meses_gracia": sum(1 for f in filas if f.tipo == "gracia"),
            "meses_solo_interes": sum(1 for f in filas if f.tipo == "solo_interes" and f.cuota > 0)}


def estres(filas: list[Periodo], un_escenario: list[float], factor: float) -> dict:
    un = _extender(un_escenario, len(filas))
    sobre, ratio_max, exceso = 0, 0.0, 0.0
    for f, u in zip(filas, un):
        if f.cuota <= 0:
            continue
        cap = factor * max(u, 0.0)
        if u <= 0 or f.cuota > cap + 0.01:
            sobre += 1
            exceso += f.cuota - cap
        ratio_max = max(ratio_max, f.cuota / u if u > 0 else 99.0)
    return {"etapas_sobre_factor": sobre, "ratio_max": round(float(ratio_max), 3),
            "monto_sobre_capacidad": round(float(exceso), 2)}
