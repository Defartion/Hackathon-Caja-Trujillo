"""Trayectorias de utilidad para la comparación de planes bajo estrés."""

from collections.abc import Iterable
from math import isfinite
from statistics import mean

from .catalogo import Patron

CAIDA_PRECIO = 0.20


def utilidad_neta(ventas: float, margen_bruto: float, gastos_fijos: float) -> float:
    return ventas * margen_bruto - gastos_fijos


def redondear_importe(valor: float) -> float:
    if not isfinite(valor):
        raise OverflowError("El importe excede el rango de cálculo.")
    return round(valor, 2)


def _escenario(identificador: str, nombre: str, utilidad: Iterable[float]) -> dict:
    return {"id": identificador, "nombre": nombre, "un": [redondear_importe(un) for un in utilidad]}


def _ventana_el_nino(meses: list[int], temporada: tuple[int, ...]) -> list[int]:
    """Probar un solo evento, incluido lo que reste si el horizonte empieza en la temporada."""
    inicio = next((i for i, mes in enumerate(meses) if mes in temporada), None)
    if inicio is None:
        return []
    pendientes = temporada[temporada.index(meses[inicio]):]
    duracion = (pendientes[-1] - pendientes[0]) % 12 + 1
    fin = min(inicio + duracion, len(meses))
    return [i for i in range(inicio, fin) if meses[i] in pendientes]


def generar_escenarios(
    patron: Patron,
    calendario: list[tuple[int, int]],
    ventas_anuales: tuple[float, ...],
    meses_altos: set[int],
    ventas_mes_normal: float,
    margen_bruto: float,
    gastos_fijos: float,
) -> tuple[list[dict], list[str]]:
    meses = [mes for _, mes in calendario]
    ventas = [ventas_anuales[mes - 1] for mes in meses]

    def utilidad(trayectoria: Iterable[float]) -> Iterable[float]:
        return (utilidad_neta(monto, margen_bruto, gastos_fijos) for monto in trayectoria)

    escenarios = [_escenario("base", "Esperado", utilidad(ventas))]
    supuestos = ["Base: ventas esperadas según el patrón ajustado a la captura del asesor."]

    ventana = _ventana_el_nino(meses, patron.meses_el_nino)
    ventas_nino = ventas.copy()
    for i in ventana:
        ventas_nino[i] *= 1 - patron.caida_el_nino
    escenarios.append(_escenario("el_nino", "El Niño costero", utilidad(ventas_nino)))
    if ventana:
        desde, hasta = (calendario[i] for i in (ventana[0], ventana[-1]))
        alcance = f"de {desde[0]:04d}-{desde[1]:02d} a {hasta[0]:04d}-{hasta[1]:02d}"
    else:
        alcance = "fuera del horizonte de esta solicitud"
    supuestos.append(
        f"El Niño costero: caída de {patron.caida_el_nino:.0%} de ventas en "
        f"{patron.actividad}, {patron.provincia}, durante un solo episodio ({alcance}). "
        "La caída se modela como menor volumen con el mismo precio, costo unitario y gastos fijos. "
        "La magnitud es un supuesto de estrés informado por los episodios de 2017 y 2023."
    )

    if patron.sector == "agricultura":
        excedentes = [
            max(venta - ventas_mes_normal, 0.0) if mes in meses_altos else 0.0
            for mes, venta in enumerate(ventas_anuales, start=1)
        ]
        ventas_retrasadas = [
            ventas_anuales[mes - 1] - excedentes[mes - 1] + excedentes[mes - 2]
            for mes in meses
        ]
        escenarios.append(_escenario("retraso_cosecha", "Cosecha un mes tarde", utilidad(ventas_retrasadas)))
        supuestos.append(
            "Retraso de cosecha: en cada campaña, el ingreso de los meses altos que excede "
            "la venta mensual normal se traslada al mes siguiente. Se conservan los gastos fijos."
        )
    elif patron.sector == "pesca":
        veda = set(patron.meses_veda or patron.meses_bajos)
        extension = {mes % 12 + 1 for mes in veda} - veda
        venta_veda = mean(ventas_anuales[mes - 1] for mes in sorted(veda))
        ventas_veda = [min(venta, venta_veda) if mes in extension else venta for mes, venta in zip(meses, ventas)]
        escenarios.append(_escenario("veda_extendida", "Veda extendida un mes", utilidad(ventas_veda)))
        referencia = "veda del patrón" if patron.meses_veda else "temporada baja como referencia hipotética"
        supuestos.append(
            f"Veda extendida: se usa la {referencia}. El primer mes posterior a cada "
            "cierre se limita a su venta promedio, siempre que ese promedio reduzca las ventas previstas."
        )

    escenarios.append(_escenario(
        "caida_precios",
        f"Precio de venta −{CAIDA_PRECIO:.0%}",
        (utilidad_neta(monto, margen_bruto - CAIDA_PRECIO, gastos_fijos) for monto in ventas),
    ))
    supuestos.append(
        f"Caída de precios: se reduce {CAIDA_PRECIO:.0%} el precio de venta durante el horizonte. "
        "El volumen, el costo de venta en soles y los gastos fijos se mantienen."
    )
    return escenarios, supuestos
