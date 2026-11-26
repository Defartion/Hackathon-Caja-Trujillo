"""Detalle de un préstamo registrado para el asesor (y el supervisor): GET /motor/prestamos/{id}.

Junta lo que hoy está repartido en el core: datos del cliente, condiciones del crédito, avance de pagos y el
cronograma con vencimientos, capital, interés y saldo. Va bajo /motor (roles asesor y supervisor).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ... import cronograma as crono
from ...politica import PRODUCTOS

router = APIRouter(prefix="/motor", tags=["asesor"])

_DATOS_CLIENTE = ("nombre", "rubro", "region", "ventas_medias", "margen", "gasto_familiar", "otras_cuotas",
                  "dias_atraso_max", "ajuste_asesor")


@router.get("/prestamos/{lid}")
def detalle_prestamo(lid: int):
    from .. import main as api

    prestamo = api.DB["loans"].get(lid)
    if prestamo is None:
        raise HTTPException(404, "préstamo no existe")
    propuesta = prestamo.get("propuesta", {})
    cliente = api.DB["clients"].get(prestamo["clientId"], {})
    cuotas = prestamo.get("cuotas") or [0]
    return {
        "id": lid,
        "clientId": prestamo["clientId"],
        "estado": prestamo["status"]["value"],
        "producto": prestamo.get("producto"),
        "descripcionProducto": PRODUCTOS.get(prestamo.get("producto"), ""),
        "principal": prestamo["principal"],
        "principalSolicitado": propuesta.get("principal_solicitado"),
        "plazo": prestamo["numberOfRepayments"],
        "tea": prestamo["tea"],
        "fechaDesembolso": prestamo.get("fechaDesembolso"),
        "cuotaMinima": float(min(cuotas)),
        "cuotaMaxima": float(max(cuotas)),
        "cuotaFijaReferencia": propuesta.get("cuota_fija_referencia"),
        "aplazamientosRestantes": prestamo.get("aplazamientosRestantes", 0),
        "clausulaElNino": bool(propuesta.get("clausula_el_nino")),
        "cumplePoliticas": propuesta.get("valido"),
        "explicacion": propuesta.get("explicacion", ""),
        "cliente": {k: cliente.get(k) for k in _DATOS_CLIENTE},
        "cuotasPagadas": len(crono.pagadas(prestamo)),
        "totalCuotas": len(prestamo.get("cuotas", [])),
        "pagos": [{"fecha": p.get("fecha"), "monto": p.get("monto"), "cuota": p.get("cuota")}
                  for p in prestamo.get("pagos", [])],
        "resumen": crono.resumen(prestamo),
        "cronograma": crono.detalle(prestamo),
    }
