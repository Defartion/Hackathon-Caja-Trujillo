"""Análisis de sensibilidad del beneficio de CuotaFlex frente a la cuota fija (fase 2, lote A).

Varía un supuesto a la vez: gasto del sobrante mensual (fuga), probabilidad de El Niño y
volatilidad real de las ventas frente a la estimada. Salida: resultados/sensibilidad.md + PNG.
Uso: python scripts/sensibilidad.py [--clientes 300] [--escenarios 100]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from cuotaflex.config import cargar_parametros  # noqa: E402
from cuotaflex.simulacion import comparar_cartera  # noqa: E402

BARRIDOS = {
    "fuga_caja_mensual": ("simulacion", "fuga_caja_mensual", [0.0, 0.1, 0.15, 0.2, 0.3, 0.4],
                          "Gasto del sobrante mensual (fuga de caja)"),
    "probabilidad_nino": ("el_nino", "probabilidad_anual", [0.0, 0.15, 0.5, 1.0], "Probabilidad anual de El Niño"),
    "factor_volatilidad": ("simulacion", "factor_volatilidad", [1.0, 1.5, 2.0],
                           "Volatilidad real / volatilidad estimada (error de pronóstico)"),
}


def main(n, n_esc):
    base = cargar_parametros()
    res = {}
    for clave, (sec, campo, valores, _) in BARRIDOS.items():
        res[clave] = []
        for v in valores:
            par = copy.deepcopy(base)
            par[sec][campo] = v
            _, s = comparar_cartera(n, n_esc, par=par)
            f, x = s["fija"], s["cuotaflex"]
            res[clave].append({"valor": v, "default_fija": f["default_pct"], "default_flex": x["default_pct"],
                               "mora_fija": f["mora30_pct"], "mora_flex": x["mora30_pct"],
                               "margen_fija": f["margen_sobre_cartera_pct"], "margen_flex": x["margen_sobre_cartera_pct"]})
            print(clave, v, res[clave][-1], flush=True)
    out = RAIZ / "resultados"
    (out / "img").mkdir(parents=True, exist_ok=True)
    (out / "sensibilidad.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")

    fig, ejes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, (clave, (_, _, _, titulo)) in zip(ejes, BARRIDOS.items()):
        xs = [r["valor"] for r in res[clave]]
        ax.plot(xs, [r["default_fija"] for r in res[clave]], "o-", color="#57606A", label="Default cuota fija")
        ax.plot(xs, [r["default_flex"] for r in res[clave]], "o-", color="#0B5CAD", label="Default CuotaFlex")
        ax2 = ax.twinx()
        ax2.plot(xs, [r["margen_flex"] - r["margen_fija"] for r in res[clave]], "s--", color="#1A7F37", label="Δ margen (pp)")
        ax.set_title(titulo, fontsize=10)
        ax.set_ylabel("Default (%)")
        ax2.set_ylabel("Δ margen / cartera (pp)", color="#1A7F37")
        ax.grid(alpha=.3)
    ejes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Sensibilidad del beneficio de CuotaFlex (datos sintéticos)", fontsize=12)
    fig.tight_layout()
    fig.savefig(out / "img" / "sensibilidad.png", dpi=130)

    L = ["# Análisis de sensibilidad", "",
         f"Cartera sintética de {n} créditos × {n_esc} escenarios. Se varía un supuesto a la vez; el resto queda en `config/parametros.yaml`.", "",
         "![Sensibilidad](img/sensibilidad.png)", ""]
    for clave, (_, _, _, titulo) in BARRIDOS.items():
        L += [f"## {titulo}", "", "| Valor | Default fija | Default CuotaFlex | Atraso>30 fija | Atraso>30 CuotaFlex | Δ margen (pp) |",
              "|---|---|---|---|---|---|"]
        L += [f"| {r['valor']} | {r['default_fija']}% | {r['default_flex']}% | {r['mora_fija']}% | {r['mora_flex']}% | "
              f"{r['margen_flex'] - r['margen_fija']:+.1f} |" for r in res[clave]]
        L.append("")
    (out / "sensibilidad.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=300)
    ap.add_argument("--escenarios", type=int, default=100)
    a = ap.parse_args()
    main(a.clientes, a.escenarios)
