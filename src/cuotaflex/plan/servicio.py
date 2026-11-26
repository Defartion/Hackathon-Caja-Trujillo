"""Orquesta el contrato POST /plan/proponer (docs/fases/fase-4/CONTRATOS.md §2)."""
from __future__ import annotations

from datetime import date

from .constructor import _cerrar, construir, cuota_fija, estres, resumen
from .costos import Periodo, Seguros


class ErrorSolicitud(ValueError):
    pass


def _filas_json(filas: list[Periodo], periodos_ciclo: list[dict], un: list[float]) -> list[dict]:
    out = []
    for i, f in enumerate(filas):
        u = un[i] if i < len(un) else (un[i - 12] if i >= 12 else un[-1])
        etapa = periodos_ciclo[i]["etapa"] if i < len(periodos_ciclo) else periodos_ciclo[i % len(periodos_ciclo)]["etapa"]
        out.append({"n": f.n, "fecha_vencimiento": f.fecha_vencimiento.isoformat(), "dias": f.dias, "etapa": etapa,
                    "cuota": round(f.cuota, 2), "seguro_desgravamen": round(f.seguro_desgravamen, 2),
                    "seguro_multirriesgo": round(f.seguro_multirriesgo, 2), "interes": round(f.interes, 2),
                    "pago_seguros": round(f.pago_seguros, 2), "pago_interes": round(f.pago_interes, 2),
                    "capital": round(f.capital, 2), "pendiente_seguros": round(f.pendiente_seguros, 2),
                    "pendiente_interes": round(f.pendiente_interes, 2), "saldo_capital": round(f.saldo_capital, 2),
                    "saldo_deuda": round(f.saldo_deuda, 2), "un_esperada": round(u, 2),
                    "ratio_cuota_un": round(f.cuota / u, 3) if u > 0 else None, "tipo": f.tipo})
    return out


def proponer_plan(sol: dict) -> dict:
    monto, tea, plazo = float(sol["monto"]), float(sol["tea"]), int(sol["plazo_meses"])
    desembolso = date.fromisoformat(sol["fecha_desembolso"])
    prod = dict(sol.get("producto") or {})
    if prod.get("id"):  # producto del catálogo de config; lo enviado en la solicitud prevalece
        from ..config import cargar_parametros
        cat = cargar_parametros().get("productos", {})
        if prod["id"] not in cat or not isinstance(cat[prod["id"]], dict):
            raise ErrorSolicitud(f"Producto desconocido: {prod['id']}")
        prod = {**cat[prod["id"]], "tope_tea": cat.get("tope_tea"), **{k: v for k, v in prod.items() if k != "id"}}
    factor = float(prod.get("factor", 0.85))
    if not 0 < factor < 1:
        raise ErrorSolicitud("El factor del producto debe estar entre 0 y 1.")
    if monto <= 0 or plazo <= 0:
        raise ErrorSolicitud("Monto y plazo deben ser positivos.")
    tope = prod.get("tope_tea")
    if tope is not None and tea > float(tope):
        raise ErrorSolicitud(f"La TEA {tea:.2%} supera el tope del producto ({float(tope):.2%}).")
    ciclo = sol.get("ciclo")
    if not isinstance(ciclo, dict) or not ciclo.get("periodos"):
        raise ErrorSolicitud("Falta el ciclo estimado (respuesta de POST /ciclo/estimar).")
    seguros = Seguros.desde_dict(sol.get("seguros"))
    max_gracia = int(prod.get("max_meses_gracia", 4))
    periodos_ciclo = ciclo["periodos"]
    un = [float(p["un_p50"]) for p in periodos_ciclo]

    adversos = [e["un"] for e in (ciclo.get("escenarios") or []) if e.get("id") != "base"]
    r = construir(monto, tea, desembolso, plazo, un, factor, seguros, max_gracia, adversos,
                  float(prod.get("peso_estres", 2.0)))
    fija = cuota_fija(monto, tea, desembolso, plazo, seguros)
    plan_json = None
    if r["factible"]:
        filas = _cerrar(monto, tea, desembolso, r["cuotas"], seguros)
        plan_json = {"periodos": _filas_json(filas, periodos_ciclo, un), "resumen": resumen(monto, desembolso, filas, un, factor, tea)}
    fija_json = {"periodos": _filas_json(fija, periodos_ciclo, un), "resumen": resumen(monto, desembolso, fija, un, factor, tea)}
    escenarios = ciclo.get("escenarios") or [{"id": "base", "nombre": "Esperado", "un": un}]
    est = []
    for e in escenarios:
        item = {"escenario": e["id"], "nombre": e.get("nombre", e["id"]), "fija": estres(fija, e["un"], factor)}
        item["adaptado"] = estres(filas, e["un"], factor) if r["factible"] else None
        est.append(item)
    supuestos = [f"TEA {tea:.2%} → TED base 360 aplicada por días exactos sobre el saldo de capital",
                 f"Factor del producto {factor} sobre la utilidad neta esperada de cada etapa",
                 "Prelación: seguros → interés → capital; lo pendiente no capitaliza",
                 f"Hasta {max_gracia} periodos de gracia"]
    if seguros.desgravamen_tasa_mensual:
        supuestos.append(f"Desgravamen {seguros.desgravamen_tasa_mensual:.4%} mensual sobre el saldo (interés simple por días, base 360)")
    if seguros.multirriesgo_tasa_mensual:
        supuestos.append(f"Multirriesgo {seguros.multirriesgo_tasa_mensual:.4%} mensual sobre S/ {seguros.valor_asegurable:,.0f}")
    return {"factible": r["factible"], "plan": plan_json, "plan_cuota_fija": fija_json if sol.get("comparar_cuota_fija", True) else None,
            "estres": est, "ajustes_sugeridos": r["ajustes"], "supuestos": supuestos + list(ciclo.get("supuestos", [])),
            "bitacora": r["bitacora"]}
