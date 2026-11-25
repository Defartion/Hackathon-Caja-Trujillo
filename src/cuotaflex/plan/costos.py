"""Calendario, tasas, seguros y prelación de pagos según las reglas de la Caja (FAQ NEG-01).

- TEA → TED = (1 + TEA)^(1/360) − 1, aplicada por los días exactos de cada periodo sobre el saldo de capital.
- Seguros con interés simple por días (base 360): desgravamen sobre el saldo de capital, multirriesgo
  sobre el valor asegurable. Tasa expresada como mensual: tasa_mensual / 30 × días × base.
- Prelación: seguros → interés → capital, con pagos parciales. Lo no pagado queda pendiente en su
  mismo concepto: suma a la deuda, no al saldo de capital, y no genera interés.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date


def sumar_meses(d: date, k: int) -> date:
    """Mismo día k meses después; si el mes no tiene ese día, el último día del mes."""
    m = d.month - 1 + k
    anio, mes = d.year + m // 12, m % 12 + 1
    return date(anio, mes, min(d.day, calendar.monthrange(anio, mes)[1]))


def vencimientos(desembolso: date, n: int) -> list[date]:
    return [sumar_meses(desembolso, k) for k in range(1, n + 1)]


def ted(tea: float) -> float:
    return (1 + tea) ** (1 / 360) - 1


def factor_interes(tea: float, dias: int) -> float:
    """Fracción de interés de un periodo de `dias` días sobre el saldo de capital."""
    return (1 + ted(tea)) ** dias - 1


@dataclass
class Seguros:
    desgravamen_tasa_mensual: float = 0.0     # sobre saldo de capital
    multirriesgo_tasa_mensual: float = 0.0    # sobre valor asegurable
    valor_asegurable: float = 0.0

    @classmethod
    def desde_dict(cls, s: dict | None) -> "Seguros":
        s = s or {}
        d, m = s.get("desgravamen") or {}, s.get("multirriesgo") or {}
        return cls(d.get("tasa_mensual", 0.0) if d.get("activo") else 0.0,
                   m.get("tasa_mensual", 0.0) if m.get("activo") else 0.0,
                   float(m.get("valor_asegurable") or 0.0) if m.get("activo") else 0.0)

    def desgravamen(self, saldo: float, dias: int) -> float:
        return saldo * self.desgravamen_tasa_mensual / 30 * dias

    def multirriesgo(self, dias: int) -> float:
        return self.valor_asegurable * self.multirriesgo_tasa_mensual / 30 * dias


@dataclass
class Estado:
    saldo_capital: float
    pendiente_seguros: float = 0.0
    pendiente_interes: float = 0.0

    @property
    def deuda(self) -> float:
        return self.saldo_capital + self.pendiente_seguros + self.pendiente_interes


@dataclass
class Periodo:
    n: int
    fecha_vencimiento: date
    dias: int
    cuota: float
    seguro_desgravamen: float
    seguro_multirriesgo: float
    interes: float
    pago_seguros: float
    pago_interes: float
    capital: float
    pendiente_seguros: float
    pendiente_interes: float
    saldo_capital: float
    saldo_deuda: float
    extra: dict = field(default_factory=dict)

    @property
    def tipo(self) -> str:
        if self.capital > 0.005:
            return "amortizacion"
        return "gracia" if self.pendiente_interes > 0.005 or self.pendiente_seguros > 0.005 else "solo_interes"


def aplicar_periodo(estado: Estado, cuota: float, dias: int, tea: float, seguros: Seguros) -> tuple[dict, Estado]:
    """Genera los cargos del periodo y aplica la cuota con prelación seguros → interés → capital."""
    s_desg = seguros.desgravamen(estado.saldo_capital, dias)
    s_mr = seguros.multirriesgo(dias)
    interes = estado.saldo_capital * factor_interes(tea, dias)
    restante = max(cuota, 0.0)
    deuda_seguros = estado.pendiente_seguros + s_desg + s_mr
    pago_seg = min(restante, deuda_seguros); restante -= pago_seg
    deuda_interes = estado.pendiente_interes + interes
    pago_int = min(restante, deuda_interes); restante -= pago_int
    capital = min(restante, estado.saldo_capital); restante -= capital
    nuevo = Estado(estado.saldo_capital - capital, deuda_seguros - pago_seg, deuda_interes - pago_int)
    return ({"seguro_desgravamen": s_desg, "seguro_multirriesgo": s_mr, "interes": interes, "pago_seguros": pago_seg,
             "pago_interes": pago_int, "capital": capital, "sobrante": restante}, nuevo)


def simular_cuotas(monto: float, tea: float, desembolso: date, cuotas: list[float], seguros: Seguros,
                   cerrar_en_ultima: bool = True) -> list[Periodo]:
    """Recorre el cronograma con la prelación. Si `cerrar_en_ultima`, la última cuota paga toda la deuda."""
    fechas = vencimientos(desembolso, len(cuotas))
    estado, previa, filas = Estado(monto), desembolso, []
    for i, (fv, c) in enumerate(zip(fechas, cuotas)):
        dias = (fv - previa).days
        previa = fv
        if cerrar_en_ultima and i == len(cuotas) - 1:
            # cuota exacta que cancela todo lo generado en el último periodo
            s_desg = seguros.desgravamen(estado.saldo_capital, dias)
            c = estado.deuda + s_desg + seguros.multirriesgo(dias) + estado.saldo_capital * factor_interes(tea, dias)
        c = float(c)
        mov, estado = aplicar_periodo(estado, c, dias, tea, seguros)
        filas.append(Periodo(i + 1, fv, dias, c, mov["seguro_desgravamen"], mov["seguro_multirriesgo"], mov["interes"],
                             mov["pago_seguros"], mov["pago_interes"], mov["capital"], estado.pendiente_seguros,
                             estado.pendiente_interes, estado.saldo_capital, estado.deuda))
    return filas


def tcea(monto: float, desembolso: date, filas: list[Periodo]) -> float:
    """Tasa anual (base 360) que iguala el desembolso con las cuotas en sus fechas (bisección)."""
    flujos = [(f.cuota, (f.fecha_vencimiento - desembolso).days) for f in filas if f.cuota > 0]
    if not flujos:
        return 0.0
    lo, hi = -0.99, 20.0
    for _ in range(200):
        mid = (lo + hi) / 2
        vp = sum(c / (1 + mid) ** (d / 360) for c, d in flujos) - monto
        lo, hi = (mid, hi) if vp > 0 else (lo, mid)
    return (lo + hi) / 2
