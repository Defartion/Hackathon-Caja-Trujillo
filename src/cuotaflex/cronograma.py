"""Cronograma de un préstamo del core con fechas, desglose y estado de cada cuota.

Lo usan la app del cliente (routers/cliente.py) y el detalle de préstamos del asesor (routers/prestamo_detalle.py).

- Vencimiento: el último día de cada mes, empezando en el mes de la primera cuota del plan. Así la primera
  cuota nunca vence antes del desembolso aunque caiga en el mismo mes.
- Cuotas pagadas: `cuotasPagadas` sigue siendo cuántas cuotas seguidas están pagadas desde la primera (lo usan
  las alertas y los aplazamientos). Las que el cliente adelanta fuera de orden van en `cuotasAdelantadas` y se
  suman a las seguidas apenas se completa el hueco.
"""
from __future__ import annotations

import calendar
from datetime import date

from .agente import MESES_ES
from .config import desglose_cronograma, tea_a_tem


def _referencia(prestamo: dict) -> date:
    fecha = prestamo.get("fechaDesembolso")
    try:
        return date.fromisoformat(fecha) if fecha else date.today()
    except (TypeError, ValueError):
        return date.today()


def fechas_vencimiento(prestamo: dict, n: int | None = None) -> list[date]:
    n = len(prestamo["cuotas"]) if n is None else n
    referencia = _referencia(prestamo)
    filas = prestamo.get("propuesta", {}).get("cronograma") or []
    try:
        primer_mes = MESES_ES.index(filas[0]["mes"])  # 0 = enero
    except (IndexError, KeyError, ValueError):
        primer_mes = referencia.month % 12  # sin dato: el mes siguiente al desembolso
    anio = referencia.year if primer_mes >= referencia.month - 1 else referencia.year + 1
    fechas = []
    for k in range(n):
        m = primer_mes + k
        a, mes = anio + m // 12, m % 12 + 1
        fechas.append(date(a, mes, calendar.monthrange(a, mes)[1]))
    return fechas


def pagadas(prestamo: dict) -> set[int]:
    seguidas = prestamo.get("cuotasPagadas", 0)
    return set(range(1, seguidas + 1)) | {int(k) for k in prestamo.get("cuotasAdelantadas", [])}


def proxima(prestamo: dict) -> int | None:
    """La primera cuota sin pagar (None si ya pagó todas)."""
    hechas = pagadas(prestamo)
    return next((k for k in range(1, len(prestamo["cuotas"]) + 1) if k not in hechas), None)


def registrar_pago(prestamo: dict, numero: int) -> None:
    """Marca la cuota `numero` como pagada (en orden o adelantada)."""
    seguidas = prestamo.get("cuotasPagadas", 0)
    adelantadas = {int(k) for k in prestamo.get("cuotasAdelantadas", [])}
    if numero == seguidas + 1:
        seguidas += 1
        while seguidas + 1 in adelantadas:
            adelantadas.discard(seguidas + 1)
            seguidas += 1
    else:
        adelantadas.add(numero)
    prestamo["cuotasPagadas"] = seguidas
    if adelantadas or "cuotasAdelantadas" in prestamo:
        prestamo["cuotasAdelantadas"] = sorted(adelantadas)


def fechas_de_pago(prestamo: dict) -> dict[int, str]:
    """Fecha en que se pagó cada cuota. Los pagos antiguos sin número se asignan en orden."""
    hechas = sorted(pagadas(prestamo))
    asignadas: dict[int, str] = {}
    for pago in prestamo.get("pagos", []):
        numero = pago.get("cuota")
        if numero is None:
            numero = next((k for k in hechas if k not in asignadas), None)
        if numero is not None and numero not in asignadas:
            asignadas[int(numero)] = pago.get("fecha")
    return asignadas


def detalle(prestamo: dict, cuotas: list[float] | None = None) -> list[dict]:
    """Una fila por cuota: vencimiento, monto, capital, interés, saldo después de pagarla y estado."""
    cuotas = prestamo["cuotas"] if cuotas is None else cuotas
    filas = desglose_cronograma(prestamo["principal"], tea_a_tem(prestamo["tea"]), cuotas)
    meses = [f.get("mes") for f in prestamo.get("propuesta", {}).get("cronograma", [])]
    hechas, siguiente, pagos = pagadas(prestamo), proxima(prestamo), fechas_de_pago(prestamo)
    salida = []
    for fila, vence in zip(filas, fechas_vencimiento(prestamo, len(cuotas))):
        k = fila["numero"]
        estado = "pagada" if k in hechas else "proxima" if k == siguiente else "pendiente"
        salida.append({**fila, "mes": meses[k - 1] if k - 1 < len(meses) else MESES_ES[vence.month - 1],
                       "fecha": vence.isoformat(), "estado": estado, "fechaPago": pagos.get(k)})
    return salida


def resumen(prestamo: dict) -> dict:
    filas = detalle(prestamo)
    pagadas_ = [f for f in filas if f["estado"] == "pagada"]
    pendientes = [f for f in filas if f["estado"] != "pagada"]
    capital_pagado = sum(f["capital"] for f in pagadas_)
    siguiente = next((f for f in filas if f["estado"] == "proxima"), None)

    def cuota(f: dict) -> dict:
        return {"numero": f["numero"], "mes": f["mes"], "monto": f["cuota"], "fecha": f["fecha"]}

    return {
        "totalAPagar": round(sum(f["cuota"] for f in filas), 2),
        "totalPagado": round(sum(float(p.get("monto", 0)) for p in prestamo.get("pagos", [])), 2),
        "porPagar": round(sum(f["cuota"] for f in pendientes), 2),
        "saldoCapital": round(max(prestamo["principal"] - capital_pagado, 0.0), 2),
        "interesesTotales": round(sum(f["interes"] for f in filas), 2),
        "cuotasPendientes": len(pendientes),
        "cuotaMayor": cuota(max(filas, key=lambda f: f["cuota"])) if filas else None,
        "cuotaMenor": cuota(min(filas, key=lambda f: f["cuota"])) if filas else None,
        "proximoVencimiento": siguiente["fecha"] if siguiente else None,
        "diasParaVencer": (date.fromisoformat(siguiente["fecha"]) - date.today()).days if siguiente else None,
    }
