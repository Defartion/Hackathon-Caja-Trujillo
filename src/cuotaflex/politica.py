"""Políticas de riesgo: elegibilidad, selección de producto y validación del cronograma."""
from __future__ import annotations

import numpy as np

from .config import cargar_parametros, cuota_francesa, factores_descuento, tea_a_tem
from .datos import indice_estacionalidad

PRODUCTOS = {
    "fija": "Cuota fija tradicional",
    "aplazamiento": "Cuota fija con hasta 2 aplazamientos (cuota mínima) condicionados a buen pago",
    "estacional": "Cuotas ajustadas a la estacionalidad del negocio (temporada alta paga más)",
}


def excedente_medio(cli: dict) -> float:
    return cli["ventas_medias"] * cli["margen"] - cli["gasto_familiar"]


def evaluar_elegibilidad(cli: dict, par: dict | None = None) -> dict:
    par = par or cargar_parametros()
    fx, cap = par["flexibilidad"], par["capacidad_pago"]
    ref = cuota_francesa(cli["principal"], tea_a_tem(cli["tea"]), cli["plazo"])
    exc = excedente_medio(cli)
    ratio_deuda = (ref + cli["otras_cuotas"]) / exc if exc > 0 else np.inf
    motivos = []
    if cli["dias_atraso_max"] > fx["requisito_dias_atraso_max"]:
        motivos.append(f"historial con atraso de {cli['dias_atraso_max']} días (> {fx['requisito_dias_atraso_max']})")
    if ratio_deuda > cap["ratio_deuda_total_max"]:
        motivos.append(f"carga de deuda {ratio_deuda:.0%} del excedente (> {cap['ratio_deuda_total_max']:.0%}): riesgo de sobreendeudamiento")
    return {"elegible_flex": not motivos, "motivos": motivos, "ratio_deuda": round(float(ratio_deuda), 3),
            "sobreendeudado": ratio_deuda > cap["ratio_deuda_total_max"]}


def recomendar_producto(cli: dict, elegibilidad: dict, umbral_estacional: float = 0.15) -> str:
    if not elegibilidad["elegible_flex"]:
        return "fija"
    return "estacional" if indice_estacionalidad(cli["rubro"]) >= umbral_estacional else "aplazamiento"


def aplica_clausula_el_nino(cli: dict, par: dict | None = None) -> bool:
    par = par or cargar_parametros()
    return cli["rubro"] in par["el_nino"]["rubros_expuestos"]


def validar_cronograma(principal: float, tem: float, cuotas, excedente_p50, par: dict | None = None) -> dict:
    par = par or cargar_parametros()
    fx, capp = par["flexibilidad"], par["capacidad_pago"]
    cuotas = np.asarray(cuotas, dtype=float)
    n = len(cuotas)
    ref = cuota_francesa(principal, tem, n)
    d = factores_descuento(tem, n)
    chequeos = {
        "cierra_valor_presente": abs(d @ cuotas - principal) < 1.0,
        "respeta_piso": bool(np.all(cuotas >= fx["cuota_minima_pct"] * ref - 0.01)),
        "respeta_techo": bool(np.all(cuotas <= fx["cuota_maxima_mult"] * ref + 1.0)),
        "meses_reducidos_ok": int(np.sum(cuotas < (1 - fx["tolerancia_reduccion"]) * ref - 0.5))
        <= fx["max_meses_reducidos_anio"] * int(np.ceil(n / 12)),
        "carga_mediana_ok": bool(np.median(cuotas / np.maximum(excedente_p50, 1)) <= capp["ratio_cuota_excedente_max"]),
    }
    return {"valido": all(chequeos.values()), "chequeos": chequeos}


def recargo_producto(par: dict, producto: str) -> float:
    """Recargo de TEA por modalidad. `recargo.<producto>` manda si está definido;
    si no, se usa la clave histórica `flexibilidad.recargo_spread_tea` (la que mueve el tablero)."""
    if producto == "fija":
        return 0.0
    especifico = (par.get("recargo") or {}).get(producto)
    return float(especifico) if especifico is not None else float(par["flexibilidad"]["recargo_spread_tea"])
