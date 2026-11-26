"""Cifras de Cuota/UN del concepto v3: cuota fija frente al plan adaptado del prototipo actual.

Reproduce, con el motor de la fase 2, la comparación que usa el concepto v3:
- cartera sintética de la simulación (600 clientes, semilla 2026), con el monto y el plazo solicitados;
- plan adaptado: el agente con producto preferido "estacional" y sin replanificar. Si el cliente no es
  elegible a cuotas flexibles, el agente mantiene la cuota fija;
- cuota fija: cuota francesa a la TEA base del cliente;
- UN de cada mes: utilidad neta esperada (p50) del pronóstico = ventas p50 × margen − gasto familiar −
  otras cuotas;
- un mes supera el factor si Cuota/UN > factor, o si la UN es ≤ 0 y la cuota es > 0;
- escenario El Niño: la UN de todo el plazo con la caída de ventas del rubro de config/parametros.yaml.

Uso, desde la raíz del repositorio (tarda cerca de un minuto):
    python docs/concepto/v3/cifras_cuota_un.py
Escribe docs/concepto/v3/cifras_cuota_un.json. Solo datos sintéticos; no modifica el motor.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "src"))

from cuotaflex.agente import AgenteAsesor  # noqa: E402
from cuotaflex.config import cargar_parametros, cuota_francesa, tea_a_tem  # noqa: E402
from cuotaflex.datos import generar_cartera  # noqa: E402

SEMILLA = 2026
FACTORES = (0.85, 0.65)
SALIDA = Path(__file__).resolve().parent / "cifras_cuota_un.json"


def ratios(cuotas, un) -> np.ndarray:
    """Cuota/UN por mes; infinito si la UN es ≤ 0 y hay cuota."""
    cuotas = np.broadcast_to(np.asarray(cuotas, dtype=float), un.shape)
    seguro = np.where(un > 0, un, 1.0)
    return np.where(un > 0, cuotas / seguro, np.where(cuotas > 0, np.inf, 0.0))


def creditos(semilla: int = SEMILLA, par: dict | None = None) -> list[dict]:
    par = par or cargar_parametros()
    clientes, historial = generar_cartera(par["simulacion"]["n_clientes"], semilla)
    agente = AgenteAsesor(par, metodo_pronostico="perfil", replanificar=False)
    salida = []
    for cli in clientes.to_dict("records"):
        with contextlib.redirect_stdout(io.StringIO()):  # el solver imprime su encabezado
            prop = agente.proponer({**cli, "producto_preferido": "estacional"}, historial)
        crono = prop["cronograma"]
        un = np.array([f["excedente_p50"] for f in crono], dtype=float)
        principal, plazo = prop["principal_aprobado"], len(crono)
        fija = cuota_francesa(principal, tea_a_tem(cli["tea"]), plazo)
        ventas = (un + cli["gasto_familiar"] + cli["otras_cuotas"]) / cli["margen"]
        salida.append({
            "cliente_id": cli["cliente_id"], "rubro": str(cli["rubro"]), "producto": prop["producto"],
            "principal": principal, "plazo": plazo, "un": un, "ventas": ventas, "margen": cli["margen"],
            "fija": fija, "adaptado": np.array([f["cuota"] for f in crono], dtype=float),
            "interes_fija": fija * plazo - principal,
            "interes_adaptado": float(sum(f["interes"] for f in crono)),
        })
    return salida


def _resumen(creds: list[dict], factor: float, un_clave: str = "un") -> dict:
    out = {}
    for plan in ("fija", "adaptado"):
        sobre = [ratios(c[plan], c[un_clave]) > factor for c in creds]
        out[plan] = {
            "clientes_pct": round(100 * float(np.mean([s.any() for s in sobre])), 2),
            "etapas_promedio": round(float(np.mean([s.sum() for s in sobre])), 3),
        }
    return out


def calcular(semilla: int = SEMILLA) -> dict:
    par = cargar_parametros()
    creds = creditos(semilla, par)
    caidas = par["el_nino"]["caida_ingresos"]
    for c in creds:  # El Niño: caída de ventas del rubro en todo el plazo (5% si el rubro no está listado)
        c["un_nino"] = c["un"] - caidas.get(c["rubro"], 0.05) * c["ventas"] * c["margen"]
    productos: dict[str, int] = {}
    for c in creds:
        productos[c["producto"]] = productos.get(c["producto"], 0) + 1
    por_rubro = {}
    for rubro in sorted({c["rubro"] for c in creds}):
        sub = [c for c in creds if c["rubro"] == rubro]
        r = _resumen(sub, 0.85)
        por_rubro[rubro] = {"n": len(sub), "fija_pct": r["fija"]["clientes_pct"],
                            "adaptado_pct": r["adaptado"]["clientes_pct"]}
    return {
        "fuente": "docs/concepto/v3/cifras_cuota_un.py (motor de la fase 2)",
        "semilla": semilla,
        "n_clientes": len(creds),
        "productos_plan_adaptado": productos,
        "factor_0.85": _resumen(creds, 0.85),
        "factor_0.65": _resumen(creds, 0.65),
        "el_nino_factor_0.85": _resumen(creds, 0.85, "un_nino"),
        "interes_medio": {
            "fija": round(float(np.mean([c["interes_fija"] for c in creds])), 2),
            "adaptado": round(float(np.mean([c["interes_adaptado"] for c in creds])), 2),
        },
        "por_rubro_factor_0.85": por_rubro,
    }


def main() -> Path:
    cifras = calcular()
    SALIDA.write_text(json.dumps(cifras, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Cifras guardadas en {SALIDA}")
    return SALIDA


if __name__ == "__main__":
    main()
