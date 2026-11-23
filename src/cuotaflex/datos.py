"""Generador de cartera sintética de microempresarios (La Libertad).

Solo datos sintéticos: ningún dato real de clientes. Los perfiles estacionales son
referenciales (campañas agrícolas, temporadas de pesca, campañas comerciales) y deben
calibrarse con información de la Caja.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import cargar_parametros, cuota_francesa, tea_a_tem

MESES = 12

# Multiplicadores mensuales ene..dic (se normalizan a media 1)
PERFILES = {
    "agricultura":      [0.60, 0.55, 0.60, 0.90, 1.40, 1.50, 1.30, 0.90, 0.80, 0.90, 1.30, 1.30],
    "pesca":            [1.20, 1.00, 0.60, 1.30, 1.50, 1.40, 1.20, 0.60, 0.50, 0.60, 1.10, 1.30],
    "comercio_campana": [0.80, 0.90, 1.30, 0.90, 1.10, 0.90, 1.20, 0.80, 0.80, 0.90, 1.00, 1.60],
    "calzado":          [0.70, 0.80, 1.20, 1.00, 1.10, 1.00, 1.30, 0.80, 0.80, 1.00, 1.30, 1.40],
    "bodega":           [1.00, 0.95, 1.00, 1.00, 1.00, 0.98, 1.02, 1.00, 0.98, 1.00, 1.00, 1.10],
    "servicios":        [0.95, 1.00, 1.00, 0.95, 1.00, 1.00, 1.10, 1.00, 0.95, 0.95, 1.00, 1.10],
}
PERFILES = {k: np.array(v) / np.mean(v) for k, v in PERFILES.items()}

# peso en cartera, ventas medias (S/), volatilidad idiosincrática, margen medio
RUBROS = {
    "agricultura":      (0.22, 7000, 0.22, 0.35),
    "pesca":            (0.10, 8000, 0.25, 0.33),
    "comercio_campana": (0.20, 9000, 0.15, 0.28),
    "calzado":          (0.13, 8500, 0.18, 0.30),
    "bodega":           (0.20, 6000, 0.08, 0.22),
    "servicios":        (0.15, 6500, 0.10, 0.32),
}


def indice_estacionalidad(rubro: str) -> float:
    """Coeficiente de variación del perfil estacional (0 = plano)."""
    p = PERFILES[rubro]
    return float(np.std(p) / np.mean(p))


def simular_ventas(rubro: str, escala: float, n_meses: int, rng, mes_inicio: int = 0,
                   n_tray: int | None = None) -> np.ndarray:
    """Ventas mensuales con estacionalidad + choque AR(1) log-normal."""
    sigma = RUBROS[rubro][2]
    forma = (n_tray, n_meses) if n_tray else (n_meses,)
    eps = rng.normal(0, sigma, size=forma)
    z = np.zeros(forma)
    for t in range(n_meses):
        prev = z[..., t - 1] if t else 0
        z[..., t] = 0.5 * prev + eps[..., t]
    meses = (mes_inicio + np.arange(n_meses)) % MESES
    return escala * PERFILES[rubro][meses] * np.exp(z - sigma**2 / 2)


def generar_cartera(n: int | None = None, semilla: int | None = None,
                    meses_historia: int = 24) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (clientes, historial_ventas largo: cliente_id, mes, ventas)."""
    par = cargar_parametros()
    n = n or par["simulacion"]["n_clientes"]
    rng = np.random.default_rng(semilla if semilla is not None else par["simulacion"]["semilla"])
    nombres = list(RUBROS)
    pesos = np.array([RUBROS[r][0] for r in nombres])
    rubros = rng.choice(nombres, size=n, p=pesos / pesos.sum())

    filas, hist = [], []
    for i, rubro in enumerate(rubros):
        _, media, _, margen_m = RUBROS[rubro]
        escala = media * rng.lognormal(0, 0.35)
        margen = float(np.clip(rng.normal(margen_m, 0.05), 0.12, 0.55))
        gasto_fam = escala * margen * rng.uniform(0.35, 0.60)
        excedente = escala * margen - gasto_fam
        otras_cuotas = excedente * rng.choice([0, 0, 0.1, 0.2, 0.35], p=[.4, .2, .2, .12, .08])
        # historial de pagos: mayoría puntual, cola con atrasos
        dias_atraso_max = int(rng.choice([0, 3, 8, 15, 35, 70], p=[.40, .22, .15, .11, .08, .04]))
        n_previos = int(rng.integers(0, 6))
        plazo = int(rng.choice(par["credito"]["plazos_meses"]))
        tea = par["credito"]["tea_base"] + (0.06 if dias_atraso_max > 15 else 0) + rng.uniform(-0.05, 0.05)
        cuota_obj = (excedente - otras_cuotas) * rng.uniform(0.35, 0.60)
        principal = round(cuota_francesa(1, tea_a_tem(tea), plazo) ** -1 * cuota_obj, -2)
        cid = f"C{i:05d}"
        filas.append({
            "cliente_id": cid, "rubro": rubro, "region": rng.choice(["Trujillo", "Chepén", "Pacasmayo", "Virú", "Ascope"]),
            "ventas_medias": round(escala, 2), "margen": round(margen, 3), "gasto_familiar": round(gasto_fam, 2),
            "otras_cuotas": round(otras_cuotas, 2), "dias_atraso_max": dias_atraso_max,
            "creditos_previos": n_previos, "pct_cobros_yape": round(rng.uniform(0, 0.7), 2),
            "antiguedad_negocio_anios": int(rng.integers(1, 20)), "ajuste_asesor": round(rng.normal(1, 0.05), 3),
            "principal": max(principal, 1000.0), "plazo": plazo, "tea": round(tea, 4),
            "mes_desembolso": int(rng.integers(0, 12)),
        })
        ventas = simular_ventas(rubro, escala, meses_historia, rng, mes_inicio=(filas[-1]["mes_desembolso"] - meses_historia) % 12)
        hist.extend({"cliente_id": cid, "t": t - meses_historia, "ventas": round(v, 2)} for t, v in enumerate(ventas))
    return pd.DataFrame(filas), pd.DataFrame(hist)


def ampliar_con_sdv(clientes: pd.DataFrame, n: int) -> pd.DataFrame:
    """Opcional: ajusta un sintetizador SDV sobre la cartera semilla para generar más filas."""
    from sdv.metadata import Metadata  # dependencia opcional
    from sdv.single_table import GaussianCopulaSynthesizer

    meta = Metadata.detect_from_dataframe(clientes)
    sint = GaussianCopulaSynthesizer(meta)
    sint.fit(clientes)
    return sint.sample(n)
