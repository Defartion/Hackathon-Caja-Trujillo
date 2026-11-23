"""Genera la figura del cronograma de ejemplo del Concept Solution (Lote D, fase 1).

Toma la misma cartera sintética de la simulación (config/parametros.yaml: 600 clientes,
semilla 2026), elige al primer agricultor al que el agente asigna la cuota estacional y
compara, con el mismo monto y plazo, la cuota fija tradicional con la cuota estacional
frente a su capacidad de pago (70% del excedente en el escenario conservador p25).

Uso, desde la raíz del repositorio:
    pip install -r requirements.txt -r requirements-lote-d-concepto.txt
    python docs/concepto/generar_figuras.py

Solo datos sintéticos. No modifica el motor: lo consume.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))

from cuotaflex.agente import AgenteAsesor  # noqa: E402
from cuotaflex.config import cargar_parametros, cuota_francesa, tea_a_tem  # noqa: E402
from cuotaflex.datos import generar_cartera  # noqa: E402

SEMILLA = 2026  # la misma de la simulación (config/parametros.yaml)
RUBRO = "agricultura"
SALIDA = Path(__file__).resolve().parent / "img" / "cronograma-ejemplo.png"

# Tokens de la identidad visual común (docs/fases/ROADMAP.md)
AZUL = "#0B5CAD"      # cuota flexible
GRIS_900 = "#1F2328"  # texto principal y cuota fija
GRIS_600 = "#57606A"  # texto secundario y capacidad
GRIS_200 = "#E5E7EB"  # grilla
AMBAR = "#B7791F"     # alerta / temporada baja


def elegir_ejemplo(semilla: int = SEMILLA, par: dict | None = None) -> tuple[dict, dict]:
    """Primer agricultor de la cartera sintética al que el agente asigna la cuota estacional."""
    par = par or cargar_parametros()
    clientes, historial = generar_cartera(par["simulacion"]["n_clientes"], semilla)
    agente = AgenteAsesor(par, metodo_pronostico="perfil")  # mismo pronóstico que la simulación
    for cliente in clientes.to_dict("records"):
        if cliente["rubro"] != RUBRO:
            continue
        propuesta = agente.proponer(cliente, historial)
        if propuesta["producto"] == "estacional":
            return cliente, propuesta
    raise RuntimeError("No hay agricultores con cuota estacional en la cartera sintética")


def datos_cronograma(cliente: dict, propuesta: dict, par: dict | None = None) -> dict:
    """Cuotas fija y estacional con el mismo monto y plazo, y la capacidad mensual (p25)."""
    par = par or cargar_parametros()
    crono = propuesta["cronograma"]
    estacional = np.array([f["cuota"] for f in crono])
    ratio = par["capacidad_pago"]["ratio_cuota_excedente_max"]
    capacidad = ratio * np.maximum([f["excedente_p25"] for f in crono], 0.0)
    # La cuota fija tradicional no lleva el recargo de la opción flexible: usa la TEA base del cliente.
    fija = round(cuota_francesa(propuesta["principal_aprobado"], tea_a_tem(cliente["tea"]), propuesta["plazo"]), 2)
    exceso_fija = np.maximum(fija - capacidad, 0.0)
    exceso_est = np.maximum(estacional - capacidad, 0.0)
    return {
        "cliente_id": cliente["cliente_id"],
        "meses": [f["mes"] for f in crono],
        "estacional": estacional,
        "fija": fija,
        "capacidad": capacidad,
        "principal_solicitado": propuesta["principal_solicitado"],
        "plazo_solicitado": int(cliente["plazo"]),
        "principal_aprobado": propuesta["principal_aprobado"],
        "plazo": propuesta["plazo"],
        "exceso_fija": float(exceso_fija.sum()),
        "meses_exceso_fija": int((exceso_fija > 0.5).sum()),
        "exceso_estacional": float(exceso_est.sum()),
        "meses_exceso_estacional": int((exceso_est > 0.5).sum()),
    }


def _fuente():
    from matplotlib import font_manager

    disponibles = {f.name for f in font_manager.fontManager.ttflist}
    return "Inter" if "Inter" in disponibles else "DejaVu Sans"


def _barras_redondeadas(ax, xs, alturas, ancho, color, radio_px=7.0):
    """Columnas con el extremo superior redondeado y la base recta (sin borde)."""
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


def dibujar_cronograma(d: dict, ruta: Path = SALIDA) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter
    from matplotlib.transforms import blended_transform_factory

    plt.rcParams.update({"font.family": _fuente(), "font.size": 10, "axes.edgecolor": GRIS_600,
                         "xtick.color": GRIS_600, "ytick.color": GRIS_600, "text.color": GRIS_900})
    n = len(d["meses"])
    x = np.arange(1, n + 1)
    tope = max(d["capacidad"].max(), d["estacional"].max(), d["fija"]) * 1.12

    fig, ax = plt.subplots(figsize=(8.6, 4.9), dpi=240)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.69, bottom=0.205)
    ax.set_xlim(0.4, n + 0.6)
    ax.set_ylim(0, tope)

    # Meses en que la cuota fija no cabe: banda de alerta (temporada baja)
    for xi, cap in zip(x, d["capacidad"]):
        if d["fija"] > cap + 0.5:
            ax.axvspan(xi - 0.5, xi + 0.5, color=AMBAR, alpha=0.13, lw=0, zorder=0)

    # Capacidad de pago: lavado tenue + borde escalonado
    bordes = np.r_[x - 0.5, x[-1] + 0.5]
    cap_esc = np.r_[d["capacidad"], d["capacidad"][-1]]
    ax.fill_between(bordes, cap_esc, step="post", color=GRIS_600, alpha=0.10, lw=0, zorder=1)
    ax.step(bordes, cap_esc, where="post", color=GRIS_600, lw=1.6, zorder=2)

    _barras_redondeadas(ax, x, d["estacional"], 0.46, AZUL)
    ax.plot([x[0] - 0.5, x[-1] + 0.5], [d["fija"], d["fija"]], color=GRIS_900, lw=1.6,
            solid_capstyle="round", zorder=4)

    # Rótulos selectivos: el máximo y el mínimo de la cuota estacional, y la cuota fija
    i_max, i_min = int(np.argmax(d["estacional"])), int(np.argmin(d["estacional"]))
    for i in (i_max, i_min):
        ax.annotate(f"S/ {d['estacional'][i]:,.0f}", (x[i], d["estacional"][i]), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color=GRIS_900, zorder=5)
    # Rótulo de la cuota fija en el centro del primer tramo de menor capacidad (temporada baja)
    minimos = np.flatnonzero(d["capacidad"] <= d["capacidad"].min() + 0.5)
    tramo = minimos[: np.argmax(np.diff(np.r_[minimos, minimos[-1] + 2]) > 1) + 1]
    i_baja = int(tramo[len(tramo) // 2])
    ax.annotate(f"Cuota fija S/ {d['fija']:,.0f}", (x[i_baja], d["fija"]), xytext=(0, 5),
                textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color=GRIS_900, zorder=5)

    # Ejes y grilla recesivos
    ax.set_xticks(x, d["meses"])
    ax.tick_params(axis="x", length=0, labelsize=8.5, pad=4)
    ax.tick_params(axis="y", length=0, labelsize=8.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", color=GRIS_200, lw=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRIS_600)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.set_ylabel("Soles por mes", color=GRIS_600, fontsize=9)
    trans = blended_transform_factory(ax.transData, ax.transAxes)
    for k in range(0, n, 12):
        fin = min(k + 12, n)
        ax.text((k + 1 + fin) / 2, -0.10, f"Año {k // 12 + 1}", transform=trans, ha="center",
                va="top", fontsize=8.5, color=GRIS_600)
        if k:
            ax.axvline(k + 0.5, color=GRIS_200, lw=0.8, zorder=0)

    fig.text(0.075, 0.955, "Un agricultor: cuota fija vs. cuota estacional frente a su capacidad de pago",
             fontsize=12.5, fontweight="semibold", color=GRIS_900)
    fig.text(0.075, 0.925,
             f"Crédito propuesto por el agente: S/ {d['principal_aprobado']:,.0f} a {d['plazo']} meses "
             f"(el cliente pidió S/ {d['principal_solicitado']:,.0f} a {d['plazo_solicitado']} meses).\n"
             f"Exceso sobre la capacidad en todo el crédito: cuota fija S/ {d['exceso_fija']:,.0f} en "
             f"{d['meses_exceso_fija']} meses; cuota estacional S/ {d['exceso_estacional']:,.0f} en "
             f"{d['meses_exceso_estacional']} meses.",
             fontsize=8.8, color=GRIS_600, va="top", linespacing=1.5)
    leyenda = [
        Patch(facecolor=AZUL, label="Cuota estacional CuotaFlex (TEA base + 2 pp)"),
        Line2D([], [], color=GRIS_900, lw=1.6, label="Cuota fija tradicional (TEA base)"),
        Patch(facecolor=(0.34, 0.38, 0.42, 0.10), edgecolor=GRIS_600, lw=1.2,
              label="Capacidad de pago: 70% del excedente en el escenario p25"),
        Patch(facecolor=AMBAR, alpha=0.25, label="Meses en que la cuota fija supera la capacidad"),
    ]
    fig.legend(handles=leyenda, loc="upper left", bbox_to_anchor=(0.068, 0.845), ncol=2, frameon=False,
               fontsize=8.8, handlelength=1.6, columnspacing=1.8, labelcolor=GRIS_900)
    fig.text(0.075, 0.008,
             f"Datos sintéticos. Cartera de la simulación (semilla {SEMILLA}), cliente {d['cliente_id']}: el primer "
             "agricultor al que el agente asigna cuota estacional.\nMismo monto y plazo en ambas cuotas. "
             "Fuente: docs/concepto/generar_figuras.py",
             fontsize=7.5, color=GRIS_600, va="bottom", linespacing=1.5)

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, facecolor="white")
    plt.close(fig)
    return ruta


def main(argv: list[str] | None = None) -> Path:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=SALIDA, help="ruta del PNG")
    ap.add_argument("--semilla", type=int, default=SEMILLA, help="semilla de la cartera sintética")
    args = ap.parse_args(argv)
    cliente, propuesta = elegir_ejemplo(args.semilla)
    ruta = dibujar_cronograma(datos_cronograma(cliente, propuesta), args.salida)
    print(f"Figura guardada en {ruta}")
    return ruta


if __name__ == "__main__":
    main()
