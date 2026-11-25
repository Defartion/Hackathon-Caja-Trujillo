"""Estimación mensual del ciclo a partir de referencias públicas y captura del asesor."""

import json
from datetime import date
from functools import cache
from math import exp, fsum, inf, isfinite
from statistics import NormalDist, mean, median

from .catalogo import RUTA_DATOS, Patron, obtener_patron
from .escenarios import generar_escenarios, redondear_importe, utilidad_neta

UMBRAL_CIMA = 0.20
UMBRAL_VALLE = 0.20
CUANTIL_NORMAL_P90 = NormalDist().inv_cdf(0.90)
MESES_ANIO = frozenset(range(1, 13))
TIPOS_EVIDENCIA = frozenset({"yape", "boleta", "boletas"})


@cache
def _calibracion_guardada() -> tuple[float, float]:
    datos = json.loads((RUTA_DATOS / "calibracion.json").read_text(encoding="utf-8"))
    return datos["factor_intervalo"], datos["cobertura_p10_p90_backtest"]


def _calendario(fecha: date, meses: int) -> list[tuple[int, int]]:
    calendario = []
    for desplazamiento in range(1, meses + 1):
        anio, mes = divmod(fecha.year * 12 + fecha.month - 1 + desplazamiento, 12)
        if anio > date.max.year:
            raise ValueError("El horizonte excede el año máximo de una fecha ISO.")
        calendario.append((anio, mes + 1))
    return calendario


def _repartir_ventas(
    patron: Patron, grupos: list[tuple[float, set[int]]]
) -> tuple[float, ...]:
    """Usar el perfil dentro de cada temporada y preservar su nivel promedio declarado."""
    ventas = [0.0] * 12
    activos = [(nivel, meses) for nivel, meses in grupos if meses]
    for i, (nivel, meses) in enumerate(activos):
        meses_ordenados = sorted(meses)
        indices = [patron.indices[mes - 1] for mes in meses_ordenados]
        indice_medio = mean(indices)
        desviaciones = [nivel * (indice / indice_medio - 1) for indice in indices]

        # Atenuar dispersiones que mezclarían los niveles de temporadas adyacentes.
        piso = nivel - (nivel - activos[i - 1][0]) / 2 if i else 0.0
        techo = nivel + (activos[i + 1][0] - nivel) / 2 if i + 1 < len(activos) else inf
        minima, maxima = min(desviaciones), max(desviaciones)
        ajuste_inferior = (nivel - piso) / -minima if minima < 0 else 1.0
        ajuste_superior = (techo - nivel) / maxima if maxima > 0 else 1.0
        ajuste = min(1.0, ajuste_inferior, ajuste_superior)
        for mes, desviacion in zip(meses_ordenados, desviaciones):
            ventas[mes - 1] = max(nivel + ajuste * desviacion, 0.0)
    return tuple(ventas)


def _ajustar_evidencias(
    ventas: tuple[float, ...], normal: float, evidencias: list[dict], mes_desembolso: int,
) -> tuple[tuple[float, ...], float, list[str]]:
    if not evidencias:
        return ventas, normal, []

    promedios = []
    aumento = 0.0
    promedio_anual = mean(ventas)
    for evidencia in evidencias:
        if evidencia["tipo"].strip().casefold() not in TIPOS_EVIDENCIA:
            raise ValueError("Las evidencias de ventas deben ser promedios de Yape o boletas.")
        meses = evidencia["meses"]
        resto = meses % 12
        observado = evidencia["monto_promedio_mensual"]
        aporte_resto = fsum(ventas[(mes_desembolso - 2 - i) % 12] / meses for i in range(resto))
        promedio = promedio_anual * (1 - resto / meses) + aporte_resto
        if promedio > 0:
            promedios.append((observado, promedio))
        else:
            aumento = max(aumento, observado)

    factor = max(1.0, max(((observado - aumento) / promedio for observado, promedio in promedios), default=1.0))

    supuestos = [
        "Evidencias: cada promedio de Yape o boletas acota por abajo las ventas de sus últimos "
        "meses completos previos al mes del desembolso. Los canales pueden solaparse, por lo "
        "que se usa el mayor ajuste requerido."
    ]
    if factor > 1:
        supuestos.append(f"El piso observado eleva las ventas de todos los meses por un factor de {factor:.3f}.")
    if aumento > 0:
        supuestos.append(
            f"Hay evidencia en una ventana de ventas proyectadas en cero. Se suma un piso de "
            f"S/ {aumento:,.2f} al nivel mensual para conservar la diferencia entre temporadas."
        )
    return tuple(venta * factor + aumento for venta in ventas), normal * factor + aumento, supuestos


def estimar_ciclo(
    solicitud: dict,
    *,
    umbral_cima: float = UMBRAL_CIMA,
    umbral_valle: float = UMBRAL_VALLE,
    factor_intervalo: float | None = None,
    cobertura_backtest: float | None = None,
) -> dict:
    """Proyectar la UN del cliente para el horizonte solicitado, sin usar datos crediticios."""
    if factor_intervalo is None or cobertura_backtest is None:
        factor_calibrado, cobertura_calibrada = _calibracion_guardada()
        factor_intervalo = factor_calibrado if factor_intervalo is None else factor_intervalo
        cobertura_backtest = cobertura_calibrada if cobertura_backtest is None else cobertura_backtest
    if not isfinite(factor_intervalo) or factor_intervalo <= 0 or not 0 <= cobertura_backtest <= 1:
        raise ValueError("La calibración del intervalo debe tener un factor positivo y cobertura entre 0 y 1.")
    if any(not isfinite(valor) or valor < 0 for valor in (umbral_cima, umbral_valle)):
        raise ValueError("Los umbrales de etapa deben ser finitos y no negativos.")

    zona = solicitud["zona"]
    patron = obtener_patron(
        solicitud["sector"], solicitud["actividad"], zona["departamento"], zona["provincia"], zona.get("distrito"),
    )
    captura = solicitud["captura"]
    fecha_inicio = date.fromisoformat(solicitud["fecha_inicio"])

    altos_captura, bajos_captura = captura.get("meses_altos"), captura.get("meses_bajos")
    altos_patron, bajos_patron = set(patron.meses_altos), set(patron.meses_bajos)
    altos = altos_patron.copy() if altos_captura is None else set(altos_captura)
    bajos = bajos_patron.copy() if bajos_captura is None else set(bajos_captura)
    if altos_captura is None:
        altos -= bajos
    if bajos_captura is None:
        bajos -= altos
    if altos & bajos or (altos | bajos) - MESES_ANIO:
        raise ValueError("Los meses altos y bajos deben estar entre 1 y 12 y no pueden superponerse.")

    supuestos = list(patron.supuestos)
    altos_cliente = altos if altos_captura is not None and altos != altos_patron else set()
    bajos_cliente = bajos if bajos_captura is not None and bajos != bajos_patron else set()
    if altos != altos_patron or bajos != bajos_patron:
        supuestos.append(
            f"Se ajustó el calendario a la captura del asesor. Meses altos: {sorted(altos)}. "
            f"Meses bajos: {sorted(bajos)}. El patrón público registraba "
            f"{sorted(altos_patron)} y {sorted(bajos_patron)}, respectivamente."
        )

    venta_baja = captura["ventas_mes_bajo"]
    venta_normal = captura["ventas_mes_normal"]
    venta_alta = captura["ventas_mes_alto"]
    if not 0 <= venta_baja <= venta_normal <= venta_alta:
        raise ValueError("Las ventas deben ser no negativas y ordenarse de menor a mayor por temporada.")
    ventas_anuales = _repartir_ventas(patron, [
        (venta_baja, bajos),
        (venta_normal, MESES_ANIO - altos - bajos),
        (venta_alta, altos),
    ])
    supuestos.append(
        "Los índices mensuales reparten las ventas dentro de cada temporada manteniendo los "
        "promedios de la captura. Se atenúan las diferencias que cruzarían temporadas."
    )
    ventas_anuales, venta_normal, supuestos_evidencias = _ajustar_evidencias(
        ventas_anuales, venta_normal, captura.get("evidencias") or [], fecha_inicio.month,
    )
    ventas_anuales = tuple(redondear_importe(venta) for venta in ventas_anuales)
    supuestos.extend(supuestos_evidencias)

    margen_bruto = 1 - captura["costo_ventas_pct"]
    gastos_fijos = fsum(captura[concepto] for concepto in (
        "gastos_operativos", "gastos_tributarios", "carga_familiar", "otras_deudas_cuota",
    ))
    supuestos.append(
        f"Margen bruto de {margen_bruto:.1%} y deducciones fijas de S/ {gastos_fijos:,.2f} "
        "mensuales por gastos operativos, tributos, carga familiar y otras deudas, según la captura."
    )

    utilidades = tuple(redondear_importe(utilidad_neta(venta, margen_bruto, gastos_fijos)) for venta in ventas_anuales)
    mediana = median(utilidades)
    escala = max(abs(mediana), median(abs(un - mediana) for un in utilidades))
    limite_cima = mediana + escala * umbral_cima
    limite_valle = mediana - escala * umbral_valle
    if not all(map(isfinite, (mediana, limite_cima, limite_valle))):
        raise OverflowError("La utilidad excede el rango de cálculo de las etapas.")
    supuestos.append(
        f"Etapas sobre la mediana anual de UN de S/ {mediana:,.2f}. Los meses de temporada "
        f"son cima por encima de S/ {limite_cima:,.2f} o valle por debajo de S/ {limite_valle:,.2f}. "
        "En un calendario ajustado por el asesor, sus meses altos y bajos usan como corte la mediana."
    )

    calendario = _calendario(fecha_inicio, solicitud["meses"])
    sigma = patron.volatilidad * factor_intervalo
    multiplicador_p90 = exp(CUANTIL_NORMAL_P90 * sigma)
    periodos = []
    for anio, mes in calendario:
        venta, un = ventas_anuales[mes - 1], utilidades[mes - 1]
        if mes in altos and un > (mediana if mes in altos_cliente else limite_cima):
            etapa = "cima"
        elif mes in bajos and un < (mediana if mes in bajos_cliente else limite_valle):
            etapa = "valle"
        else:
            etapa = "normal"
        periodos.append({
            "periodo": f"{anio:04d}-{mes:02d}",
            "etapa": etapa,
            "ventas_p50": venta,
            "un_p10": redondear_importe(utilidad_neta(venta / multiplicador_p90, margen_bruto, gastos_fijos)),
            "un_p50": un,
            "un_p90": redondear_importe(utilidad_neta(venta * multiplicador_p90, margen_bruto, gastos_fijos)),
        })
    supuestos.append("p10 y p90 se calculan con volatilidad logarítmica de ventas calibrada en clientes sintéticos.")

    escenarios, supuestos_escenarios = generar_escenarios(
        patron, calendario, ventas_anuales, altos, venta_normal, margen_bruto, gastos_fijos,
    )
    return {
        "cliente_id": solicitud["cliente_id"],
        "sector": solicitud["sector"],
        "actividad": solicitud["actividad"],
        "zona": {"departamento": zona["departamento"], "provincia": zona["provincia"], "distrito": zona.get("distrito")},
        "fecha_inicio": solicitud["fecha_inicio"],
        "meses": solicitud["meses"],
        "periodos": periodos,
        "escenarios": escenarios,
        "supuestos": [*supuestos, *supuestos_escenarios],
        "fuentes": [*patron.fuentes, {
            "nombre": "Captura del asesor",
            "uso": "Ventas por temporada, costos, gastos, carga familiar, otras deudas y evidencias de venta.",
        }],
        "calidad": {
            "metodo": "patron_sector_zona + ajuste_asesor",
            "cobertura_p10_p90_backtest": cobertura_backtest,
        },
    }
