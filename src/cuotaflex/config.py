"""Carga de parámetros y utilidades financieras básicas."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[2]
RUTA_PARAMETROS = RAIZ / "config" / "parametros.yaml"


@lru_cache(maxsize=4)
def cargar_parametros(ruta: str | None = None) -> dict:
    with open(ruta or RUTA_PARAMETROS, encoding="utf-8") as f:
        return yaml.safe_load(f)


def tea_a_tem(tea: float) -> float:
    """Tasa efectiva anual -> tasa efectiva mensual."""
    return (1 + tea) ** (1 / 12) - 1


def cuota_francesa(principal: float, tem: float, n: int) -> float:
    if tem == 0:
        return principal / n
    return principal * tem / (1 - (1 + tem) ** -n)


def factores_descuento(tem: float, n: int) -> np.ndarray:
    return (1 + tem) ** -np.arange(1, n + 1)


def desglose_cronograma(principal: float, tem: float, cuotas) -> list[dict]:
    """Separa cada cuota en interés y capital (saldo decreciente)."""
    saldo, filas = principal, []
    for k, c in enumerate(cuotas, start=1):
        interes = saldo * tem
        capital = c - interes
        saldo -= capital
        filas.append({"numero": k, "cuota": round(float(c), 2), "interes": round(interes, 2),
                      "capital": round(capital, 2), "saldo": round(max(saldo, 0.0), 2)})
    return filas


def tir_mensual(flujos) -> float:
    """TIR mensual por bisección (flujos[0] negativo)."""
    flujos = np.asarray(flujos, dtype=float)
    t = np.arange(len(flujos))
    lo, hi = -0.99, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        vpn = np.sum(flujos / (1 + mid) ** t)
        lo, hi = (mid, hi) if vpn > 0 else (lo, mid)
    return (lo + hi) / 2
