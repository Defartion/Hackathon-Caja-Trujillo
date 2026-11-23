"""Backtesting del pronóstico de ventas con origen móvil (fase 2, lote A).

Entrena con 18-21 meses de historial y pronostica los 6 siguientes, en 4 orígenes, sobre la cartera
sintética. Compara perfil, statsforecast y mezclas. Salida: resultados/backtest.md y backtest.json.
Uso: python scripts/backtest.py [--clientes 300]
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
warnings.filterwarnings("ignore")

from cuotaflex.datos import generar_cartera  # noqa: E402
from cuotaflex.pronostico import CUANTILES, pronosticar  # noqa: E402

H, TOTAL, ORIGENES = 6, 27, (18, 19, 20, 21)
METODOS = {  # nombre: (metodo, peso_modelo, factor_sigma)
    "perfil (sigma x1.0)": ("perfil", None, 1.0), "perfil (sigma x1.3)": ("perfil", None, 1.3),
    "perfil (sigma x1.5)": ("perfil", None, 1.5), "statsforecast": ("statsforecast", None, 1.0),
    "mixto 0.3 (sigma x1.3)": ("mixto", 0.3, 1.3), "mixto 0.5 (sigma x1.0)": ("mixto", 0.5, 1.0),
    "mixto 0.5 (sigma x1.3)": ("mixto", 0.5, 1.3)}


def pinball(y, q, tau):
    d = y - q
    return np.mean(np.maximum(tau * d, (tau - 1) * d))


def main(n):
    clientes, hist = generar_cartera(n, semilla=101, meses_historia=TOTAL)
    hist = hist.assign(i=hist.t + TOTAL)  # 0..26
    filas = []
    for L in ORIGENES:
        train = hist[hist.i < L][["cliente_id", "t", "ventas"]]
        real = hist[(hist.i >= L) & (hist.i < L + H)].sort_values(["cliente_id", "i"])
        y = {k: g["ventas"].to_numpy() for k, g in real.groupby("cliente_id")}
        cli_bt = clientes.assign(plazo=H, mes_desembolso=(clientes.mes_desembolso - TOTAL + L) % 12)
        for nombre, (metodo, peso, fs) in METODOS.items():
            q = pronosticar(cli_bt, train, metodo=metodo, peso_modelo=peso if peso is not None else 0.5, factor_sigma=fs)
            for c in cli_bt.itertuples():
                Q, Y = q[c.cliente_id], y[c.cliente_id]
                filas.append({"origen": L, "metodo": nombre, "rubro": c.rubro,
                              "ape": float(np.mean(np.abs(Y - Q[2]) / Y)),
                              **{f"pinball_p{int(t*100)}": pinball(Y, Q[k], t) / np.mean(Y) for k, t in enumerate(CUANTILES)},
                              "cob_10_90": float(np.mean((Y >= Q[0]) & (Y <= Q[3]))),
                              "sobre_p25": float(np.mean(Y >= Q[1]))})
    df = pd.DataFrame(filas)
    agg = df.groupby("metodo").agg(MAPE=("ape", "mean"), pinball_p10=("pinball_p10", "mean"), pinball_p25=("pinball_p25", "mean"),
                                   pinball_p50=("pinball_p50", "mean"), pinball_p90=("pinball_p90", "mean"),
                                   cobertura_10_90=("cob_10_90", "mean"), sobre_p25=("sobre_p25", "mean"))
    agg["pinball_medio"] = agg[[c for c in agg if c.startswith("pinball")]].mean(axis=1)
    agg = agg.sort_values("pinball_medio")
    por_rubro = df[df.metodo == agg.index[0]].groupby("rubro")[["ape", "cob_10_90", "sobre_p25"]].mean()
    out = RAIZ / "resultados"
    (out / "backtest.json").write_text(json.dumps({"global": agg.round(4).to_dict("index"),
                                                    "por_rubro_mejor": por_rubro.round(4).to_dict("index")}, indent=2), encoding="utf-8")
    f = lambda v: f"{v:.1%}"
    lineas = ["# Backtesting del pronóstico de ventas", "",
              f"Cartera sintética de {n} clientes, origen móvil ({len(ORIGENES)} orígenes, entrenamiento de 18 a 21 meses, "
              f"horizonte de {H} meses). Pinball normalizado por la venta media del cliente (menor es mejor).", "",
              "| Método | MAPE p50 | Pinball medio | Cobertura p10–p90 (ideal 80%) | Ventas ≥ p25 (ideal 75%) |",
              "|---|---|---|---|---|"]
    lineas += [f"| {m} | {f(r.MAPE)} | {r.pinball_medio:.4f} | {f(r.cobertura_10_90)} | {f(r.sobre_p25)} |" for m, r in agg.iterrows()]
    lineas += ["", f"**Mejor método por pinball medio: `{agg.index[0]}`.**", "", "## Por rubro (mejor método)", "",
               "| Rubro | MAPE | Cobertura p10–p90 | Ventas ≥ p25 |", "|---|---|---|---|"]
    lineas += [f"| {r} | {f(v.ape)} | {f(v.cob_10_90)} | {f(v.sobre_p25)} |" for r, v in por_rubro.iterrows()]
    (out / "backtest.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=300)
    main(ap.parse_args().clientes)
