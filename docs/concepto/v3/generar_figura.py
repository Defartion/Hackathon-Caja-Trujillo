"""Figura 1 del concepto v3: cuota fija y plan del prototipo frente al tope Cuota/UN ≤ factor.

Toma la cartera sintética de la simulación (semilla 2026) y elige al primer agricultor al que el agente
asigna la cuota estacional con el monto y el plazo solicitados. Compara, mes a mes, la cuota fija y el plan
adaptado del prototipo actual (motor de la fase 2) con el tope factor × UN esperada del mes.

Uso, desde la raíz del repositorio:
    python docs/concepto/v3/generar_figura.py
Requiere matplotlib (requirements-dev.txt). Solo datos sintéticos; no modifica el motor.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "src"))

from cuotaflex.agente import AgenteAsesor  # noqa: E402
from cuotaflex.config import cargar_parametros, cuota_francesa, tea_a_tem  # noqa: E402
from cuotaflex.datos import generar_cartera  # noqa: E402

SEMILLA = 2026
FACTOR = 0.85
SALIDA = Path(__file__).resolve().parent / "img" / "cuota-un-ejemplo.png"

AZUL, GRIS_900, GRIS_600, GRIS_200, AMBAR = "#0B5CAD", "#1F2328", "#57606A", "#E5E7EB", "#B7791F"


def elegir_ejemplo(semilla: int = SEMILLA) -> tuple[dict, dict]:
    """Primer agricultor con cuota estacional, sin cambiar monto ni plazo."""
    par = cargar_parametros()
    clientes, historial = generar_cartera(par["simulacion"]["n_clientes"], semilla)
    agente = AgenteAsesor(par, metodo_pronostico="perfil", replanificar=False)
    for cli in clientes.to_dict("records"):
        if cli["rubro"] != "agricultura":
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            prop = agente.proponer({**cli, "producto_preferido": "estacional"}, historial)
        if prop["producto"] == "estacional":
            return cli, prop
    raise RuntimeError("No hay agricultores con cuota estacional en la cartera sintética")


def datos(cli: dict, prop: dict, factor: float = FACTOR) -> dict:
    crono = prop["cronograma"]
    un = np.array([f["excedente_p50"] for f in crono], dtype=float)
    adaptado = np.array([f["cuota"] for f in crono], dtype=float)
    fija = round(cuota_francesa(prop["principal_aprobado"], tea_a_tem(cli["tea"]), len(crono)), 2)
    tope = factor * np.maximum(un, 0.0)

    def sobre(c):
        c = np.broadcast_to(c, un.shape)
        return np.where(un > 0, c > factor * un, c > 0)

    return {
        "cliente_id": cli["cliente_id"], "meses": [f["mes"] for f in crono], "un": un, "tope": tope,
        "adaptado": adaptado, "fija": fija, "factor": factor,
        "principal": prop["principal_aprobado"], "plazo": len(crono),
        "meses_sobre_fija": int(sobre(fija).sum()), "meses_sobre_adaptado": int(sobre(adaptado).sum()),
        "ratio_max_fija": float(np.max(np.where(un > 0, fija / np.where(un > 0, un, 1), np.inf))),
    }


def _barras(ax, xs, alturas, ancho, color, radio_px=7.0):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    (x0, y0), (x1, y1) = ax.transData.transform([(0, 0), (1, 1)])
    px_x, px_y = x1 - x0, y1 - y0
    for x, h in zip(xs, alturas):
        if h <= 0:
            continue
        izq, der = x - ancho / 2, x + ancho / 2
        rx, ry = min(radio_px / px_x, ancho / 2), min(radio_px / px_y, h)
        verts = [(izq, 0), (izq, h - ry), (izq, h), (izq + rx, h), (der - rx, h), (der, h),
                 (der, h - ry), (der, 0), (izq, 0)]
        codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO,
                 MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", zorder=3))


def dibujar(d: dict, ruta: Path = SALIDA) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter

    fuente = "Inter" if "Inter" in {f.name for f in font_manager.fontManager.ttflist} else "DejaVu Sans"
    plt.rcParams.update({"font.family": fuente, "font.size": 10, "axes.edgecolor": GRIS_600,
                         "xtick.color": GRIS_600, "ytick.color": GRIS_600, "text.color": GRIS_900})
    n = len(d["meses"])
    x = np.arange(1, n + 1)
    tope_max = max(d["tope"].max(), d["adaptado"].max(), d["fija"]) * 1.15

    fig, ax = plt.subplots(figsize=(8.6, 4.7), dpi=240)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.69, bottom=0.15)
    ax.set_xlim(0.4, n + 0.6)
    ax.set_ylim(0, tope_max)

    for xi, un, tope in zip(x, d["un"], d["tope"]):
        if (un <= 0 and d["fija"] > 0) or d["fija"] > tope + 0.5:
            ax.axvspan(xi - 0.5, xi + 0.5, color=AMBAR, alpha=0.13, lw=0, zorder=0)
    bordes = np.r_[x - 0.5, x[-1] + 0.5]
    tope_esc = np.r_[d["tope"], d["tope"][-1]]
    ax.fill_between(bordes, tope_esc, step="post", color=GRIS_600, alpha=0.10, lw=0, zorder=1)
    ax.step(bordes, tope_esc, where="post", color=GRIS_600, lw=1.6, zorder=2)
    _barras(ax, x, d["adaptado"], 0.46, AZUL)
    ax.plot([x[0] - 0.5, x[-1] + 0.5], [d["fija"], d["fija"]], color=GRIS_900, lw=1.6, zorder=4)

    for i in (int(np.argmax(d["adaptado"])), int(np.argmin(d["adaptado"]))):
        ax.annotate(f"S/ {d['adaptado'][i]:,.0f}", (x[i], d["adaptado"][i]), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=8.5, zorder=5)
    i_bajo = int(np.argmin(d["tope"]))
    ax.annotate(f"Cuota fija S/ {d['fija']:,.0f}", (x[i_bajo], d["fija"]), xytext=(0, 5),
                textcoords="offset points", ha="center", va="bottom", fontsize=8.5, zorder=5)

    ax.set_xticks(x, d["meses"])
    ax.tick_params(axis="both", length=0, labelsize=8.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", color=GRIS_200, lw=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.set_ylabel("Soles por mes", color=GRIS_600, fontsize=9)

    fig.text(0.075, 0.955, f"Un agricultor: la cuota fija y el plan del prototipo frente a Cuota/UN ≤ {d['factor']}",
             fontsize=12.5, fontweight="semibold")
    fig.text(0.075, 0.925,
             f"Mismo monto y plazo: S/ {d['principal']:,.0f} a {d['plazo']} meses. Meses sobre el factor: "
             f"cuota fija {d['meses_sobre_fija']}, plan del prototipo {d['meses_sobre_adaptado']}.\n"
             "El motor de la final no permite ninguno: si la UN del mes no alcanza, aplica solo interés o gracia.",
             fontsize=8.8, color=GRIS_600, va="top", linespacing=1.5)
    leyenda = [
        Patch(facecolor=AZUL, label="Plan adaptado del prototipo (motor de la fase 2)"),
        Line2D([], [], color=GRIS_900, lw=1.6, label="Cuota fija"),
        Patch(facecolor=(0.34, 0.38, 0.42, 0.10), edgecolor=GRIS_600, lw=1.2,
              label=f"Tope de la cuota: {d['factor']} × UN esperada del mes"),
        Patch(facecolor=AMBAR, alpha=0.25, label="Meses en que la cuota fija supera el tope"),
    ]
    fig.legend(handles=leyenda, loc="upper left", bbox_to_anchor=(0.068, 0.835), ncol=2, frameon=False,
               fontsize=8.8, handlelength=1.6, columnspacing=1.8, labelcolor=GRIS_900)
    fig.text(0.075, 0.012,
             f"Datos sintéticos. Cartera de la simulación (semilla {SEMILLA}), cliente {d['cliente_id']}: el primer "
             "agricultor con cuota estacional. UN = utilidad neta esperada (p50) del mes.\n"
             "Fuente: docs/concepto/v3/generar_figura.py",
             fontsize=7.5, color=GRIS_600, va="bottom", linespacing=1.5)

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, facecolor="white")
    plt.close(fig)
    return ruta


def main(argv: list[str] | None = None) -> Path:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args(argv)
    cli, prop = elegir_ejemplo()
    ruta = dibujar(datos(cli, prop), args.salida)
    print(f"Figura guardada en {ruta}")
    return ruta


if __name__ == "__main__":
    main()
