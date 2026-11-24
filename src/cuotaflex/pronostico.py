"""Pronóstico probabilístico de ventas por cliente.

Combina tres fuentes (como pide el reto ante cobros en efectivo/Yape):
1. Historial propio del cliente en la Caja (modelo de series de tiempo).
2. Perfil de negocios similares (estacionalidad del rubro aprendida de la cartera).
3. Ajuste acotado del asesor de campo.
Devuelve cuantiles para reconocer la incertidumbre (p10, p25, p50, p90).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .datos import PERFILES

CUANTILES = (0.10, 0.25, 0.50, 0.90)


def _perfil(cliente: dict, hist: np.ndarray, plazo: int) -> tuple[np.ndarray, float]:
    """Nivel desestacionalizado del cliente × perfil del rubro; sigma de residuos log."""
    perfil = PERFILES[cliente["rubro"]]
    m0 = cliente["mes_desembolso"]
    meses_hist = (m0 - len(hist) + np.arange(len(hist))) % 12
    desest = hist / perfil[meses_hist]
    nivel = np.average(desest, weights=np.linspace(0.5, 1.5, len(hist)))  # más peso a lo reciente
    sigma = float(np.std(np.log(desest / nivel)))
    futuros = (m0 + np.arange(plazo)) % 12
    return nivel * perfil[futuros], max(sigma, 0.05)


def _statsforecast(series: dict[str, np.ndarray], h: int) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS

    df = pd.concat([pd.DataFrame({"unique_id": k, "ds": np.arange(len(v)), "y": v}) for k, v in series.items()])
    sf = StatsForecast(models=[AutoETS(season_length=12, model="ZZA")], freq=1, n_jobs=1)
    fc = sf.forecast(df=df, h=h, level=[80])
    out = {}
    for k, g in fc.groupby("unique_id"):
        media = g["AutoETS"].to_numpy()
        sig = (g["AutoETS-hi-80"].to_numpy() - media) / norm.ppf(0.9)
        out[k] = (np.maximum(media, 1.0), np.maximum(sig, 1e-6))
    return out


def pronosticar(clientes: pd.DataFrame, historial: pd.DataFrame, metodo: str | None = None,
                peso_modelo: float | None = None, factor_sigma: float | None = None) -> dict[str, np.ndarray]:
    """{cliente_id: array (4, plazo) con cuantiles de ventas mensuales}.

    peso_modelo y factor_sigma toman por defecto `pronostico.*` de config (calibrados por backtesting).
    factor_sigma ensancha la dispersión del perfil: el sigma de residuos dentro de muestra subestima
    la incertidumbre fuera de muestra.
    """
    from .config import cargar_parametros

    cfg = cargar_parametros().get("pronostico", {})
    metodo = metodo or cfg.get("metodo", "mixto")
    peso_modelo = cfg.get("peso_modelo", 0.5) if peso_modelo is None else peso_modelo
    factor_sigma = cfg.get("factor_sigma", 1.0) if factor_sigma is None else factor_sigma
    hist_por_cli = {k: g.sort_values("t")["ventas"].to_numpy() for k, g in historial.groupby("cliente_id")}
    h = int(clientes["plazo"].max())
    modelo = {}
    if metodo in ("mixto", "statsforecast"):
        try:
            modelo = _statsforecast(hist_por_cli, h)
        except Exception:  # sin statsforecast o fallo: se usa solo el perfil
            modelo = {}
    z = norm.ppf(CUANTILES)
    res = {}
    for cli in clientes.to_dict("records"):
        cid, plazo = cli["cliente_id"], cli["plazo"]
        hist = hist_por_cli[cid]
        base, sig_log = _perfil(cli, hist, plazo)
        sig_log *= factor_sigma
        q_perfil = base * np.exp(np.outer(z, np.ones(plazo)) * sig_log - sig_log**2 / 2)
        if cid in modelo and metodo != "perfil":
            media, sig = modelo[cid][0][:plazo], modelo[cid][1][:plazo]
            q_modelo = np.maximum(media + np.outer(z, sig), 0.0)
            w = 1.0 if metodo == "statsforecast" else peso_modelo
            q = w * q_modelo + (1 - w) * q_perfil
        else:
            q = q_perfil
        ajuste = float(np.clip(cli.get("ajuste_asesor", 1.0), 0.9, 1.1))  # el asesor no puede inflar más de 10%
        res[cid] = np.sort(q * ajuste, axis=0)
    return res


def excedente_cuantiles(cliente: dict, q_ventas: np.ndarray) -> np.ndarray:
    """Excedente para pagar deudas = ventas*margen - gasto familiar - otras cuotas."""
    return q_ventas * cliente["margen"] - cliente["gasto_familiar"] - cliente["otras_cuotas"]
