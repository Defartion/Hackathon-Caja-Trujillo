"""Calibra y evalúa el intervalo de UN con clientes totalmente sintéticos."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from math import ceil, exp, fsum, log
from pathlib import Path
from random import Random
from statistics import NormalDist, mean, median

from .catalogo import RUTA_DATOS, Patron, cargar_patrones
from .estimador import estimar_ciclo

_RAIZ = Path(__file__).resolve().parents[3]
_DATOS = _RAIZ / "data" / "ciclos"
_MESES = tuple(range(1, 13))
_FIJOS = ("gastos_operativos", "gastos_tributarios", "carga_familiar", "otras_deudas_cuota")
_VENTAS = ("ventas_mes_alto", "ventas_mes_normal", "ventas_mes_bajo")
_ERRORES_CAPTURA = {
    "Ventas alto, normal y bajo": _VENTAS,
    "Proporción de costo de ventas": ("costo_ventas_pct",),
    "Gastos operativos y tributarios": _FIJOS[:2],
    "Carga familiar y otras cuotas": _FIJOS[2:],
}
_SEMILLA_CALIBRACION = 260401
_SEMILLA_EVALUACION = 260402
_N_CALIBRACION = 25
_N_EVALUACION = 40
_COBERTURA_OBJETIVO = 0.80
_RADIO_NORMAL = NormalDist().inv_cdf(0.9)
_PISO_MAPE = 100.0


@dataclass(frozen=True)
class ClienteSintetico:
    solicitud: dict
    ventas_observadas: tuple[float, ...]
    volatilidad: float

    @property
    def un_observada(self) -> tuple[float, ...]:
        captura = self.solicitud["captura"]
        return tuple(round(_utilidad(venta, captura), 2) for venta in self.ventas_observadas)


def _utilidad(ventas: float, captura: dict) -> float:
    return ventas * (1 - captura["costo_ventas_pct"]) - fsum(captura[campo] for campo in _FIJOS)


def _cliente_sintetico(patron: Patron, rng: Random, cliente_id: str) -> ClienteSintetico:
    # Un cliente puede desplazar su campaña y tener más o menos estacionalidad
    # que la zona. Los meses sujetos a una veda conservan su calendario.
    desplazar = rng.choice((-1, 1)) if not patron.meses_veda and rng.random() < 0.20 else 0
    altos = sorted((mes - 1 + desplazar) % 12 + 1 for mes in patron.meses_altos)
    bajos = sorted((mes - 1 + desplazar) % 12 + 1 for mes in patron.meses_bajos)
    normales = [mes for mes in _MESES if mes not in altos and mes not in bajos]
    nivel = rng.uniform(4000, 19000)
    amplitud = rng.uniform(0.65, 1.45)
    ventas_tipicas = {
        mes: nivel * patron.indices[(mes - 1 - desplazar) % 12] ** amplitud
        for mes in _MESES
    }
    sesgo_asesor = rng.gauss(0, 0.075)
    captura = {
        "meses_altos": altos,
        "meses_bajos": bajos,
        "costo_ventas_pct": round(rng.uniform(0.42, 0.76), 3),
        "gastos_operativos": round(nivel * rng.uniform(0.06, 0.17), 2),
        "gastos_tributarios": round(nivel * rng.uniform(0.007, 0.03), 2),
        "carga_familiar": round(rng.uniform(650, 1500), 2),
        "otras_deudas_cuota": round(nivel * rng.uniform(0.0, 0.06), 2),
        "evidencias": [],
    }
    # La captura resume un año típico. Se preserva el orden comercial de las
    # tres cifras incluso cuando el patrón apenas varía entre estaciones.
    ventas_declaradas = [
        mean(ventas_tipicas[mes] for mes in (grupo or _MESES))
        * exp(sesgo_asesor + rng.gauss(0, 0.04))
        for grupo in (altos, normales, bajos)
    ]
    captura.update(zip(_VENTAS, sorted((round(v, 2) for v in ventas_declaradas), reverse=True)))

    # La realización del año futuro tiene un componente común a cada
    # trimestre, ruido mensual y episodios puntuales de menor venta.
    ventas_observadas = []
    for trimestre in range(4):
        shock_trimestral = rng.gauss(0, 0.50 * patron.volatilidad)
        for mes in _MESES[3 * trimestre:3 * (trimestre + 1)]:
            shock_mensual = rng.gauss(0, 0.85 * patron.volatilidad)
            episodio = rng.uniform(0.72, 0.92) if rng.random() < 0.07 else 1.0
            ventas_observadas.append(ventas_tipicas[mes] * exp(shock_trimestral + shock_mensual) * episodio)

    solicitud = {
        "cliente_id": cliente_id,
        "sector": patron.sector,
        "actividad": patron.actividad,
        "zona": {
            "departamento": patron.departamento,
            "provincia": patron.provincia,
            "distrito": patron.distrito,
        },
        "fecha_inicio": "2026-12-01",
        "meses": 12,
        "captura": captura,
    }
    return ClienteSintetico(solicitud, tuple(ventas_observadas), patron.volatilidad)


def _cohorte(semilla: int, muestra_por_patron: int) -> list[ClienteSintetico]:
    rng = Random(semilla)
    return [
        _cliente_sintetico(patron, rng, f"SIM-{semilla}-{i:02}-{n:02}")
        for i, patron in enumerate(cargar_patrones(), start=1)
        for n in range(1, muestra_por_patron + 1)
    ]


def _calibrar(clientes: list[ClienteSintetico]) -> float:
    distancias = []
    for cliente in clientes:
        estimado = estimar_ciclo(
            cliente.solicitud, factor_intervalo=1.0, cobertura_backtest=_COBERTURA_OBJETIVO
        )
        for observado, periodo in zip(cliente.ventas_observadas, estimado["periodos"], strict=True):
            log_residuo = abs(log(observado / periodo["ventas_p50"]))
            distancias.append(log_residuo / (_RADIO_NORMAL * cliente.volatilidad))
    distancias.sort()
    return round(distancias[ceil(_COBERTURA_OBJETIVO * len(distancias)) - 1], 6)


def _un_declarada(captura: dict) -> float:
    altos = len(captura["meses_altos"])
    bajos = len(captura["meses_bajos"])
    ventas = (
        altos * captura["ventas_mes_alto"]
        + (12 - altos - bajos) * captura["ventas_mes_normal"]
        + bajos * captura["ventas_mes_bajo"]
    )
    return ventas * (1 - captura["costo_ventas_pct"]) - 12 * fsum(captura[campo] for campo in _FIJOS)


def _primer_ano(periodos: list[dict]) -> float:
    return fsum(periodo["un_p50"] for periodo in periodos[:12])


def _sensibilidad(
    solicitud: dict, base: float, factor: float, cambios: dict[str, tuple[list[float], list[float]]]
) -> None:
    for nombre, campos in _ERRORES_CAPTURA.items():
        for escala, serie in zip((0.80, 1.20), cambios[nombre], strict=True):
            captura = dict(solicitud["captura"])
            for campo in campos:
                original = captura[campo]
                captura[campo] = min(1.0, original * escala) if campo == "costo_ventas_pct" else original * escala
            estimado = estimar_ciclo(
                {**solicitud, "captura": captura},
                factor_intervalo=factor,
                cobertura_backtest=_COBERTURA_OBJETIVO,
            )
            serie.append(_primer_ano(estimado["periodos"]) - base)


def validar() -> tuple[dict, str]:
    """Devuelve la calibración publicable y su informe reproducible."""
    calibracion = _cohorte(_SEMILLA_CALIBRACION, _N_CALIBRACION)
    evaluacion = _cohorte(_SEMILLA_EVALUACION, _N_EVALUACION)
    factor = _calibrar(calibracion)
    coincidencias = []
    errores_absolutos = []
    errores_relativos = []
    errores_relativos_estables = []
    errores_relativos_ventas = []
    diferencias_anuales = []
    cambios = {nombre: ([], []) for nombre in _ERRORES_CAPTURA}
    for cliente in evaluacion:
        estimado = estimar_ciclo(
            cliente.solicitud, factor_intervalo=factor, cobertura_backtest=_COBERTURA_OBJETIVO
        )
        periodos = estimado["periodos"]
        for venta, observado, periodo in zip(
            cliente.ventas_observadas, cliente.un_observada, periodos, strict=True
        ):
            errores_relativos_ventas.append(abs(periodo["ventas_p50"] - venta) / venta)
            coincidencias.append(periodo["un_p10"] <= observado <= periodo["un_p90"])
            error = abs(periodo["un_p50"] - observado)
            errores_absolutos.append(error)
            if observado != 0:
                errores_relativos.append(error / abs(observado))
            if abs(observado) >= _PISO_MAPE:
                errores_relativos_estables.append(error / abs(observado))
        base = _primer_ano(periodos)
        diferencias_anuales.append(abs(base - _un_declarada(cliente.solicitud["captura"])))
        _sensibilidad(cliente.solicitud, base, factor, cambios)

    cobertura = round(mean(coincidencias), 6)
    ajustes = {"factor_intervalo": factor, "cobertura_p10_p90_backtest": cobertura}
    filas_sensibilidad = "\n".join(
        f"| {nombre} | {median(serie_baja):+,.2f} | {median(serie_alta):+,.2f} |"
        for nombre, (serie_baja, serie_alta) in cambios.items()
    )
    casos = json.loads((_DATOS / "casos_estrella.json").read_text(encoding="utf-8"))
    filas_casos = []
    for caso in casos:
        estimado = estimar_ciclo(caso, factor_intervalo=factor, cobertura_backtest=cobertura)
        periodos = estimado["periodos"][:12]
        meses_cima = ", ".join(p["periodo"] for p in periodos if p["etapa"] == "cima") or "—"
        meses_valle = ", ".join(p["periodo"] for p in periodos if p["etapa"] == "valle") or "—"
        diferencia = _primer_ano(periodos) - _un_declarada(caso["captura"])
        filas_casos.append(
            f"| {caso['cliente_id']} · {caso['actividad']} · {caso['zona']['provincia']} "
            f"| {_primer_ano(periodos):,.2f} | {diferencia:+,.2f} | {meses_cima} | {meses_valle} |"
        )

    informe = f"""# Validación del ciclo económico

La cobertura p10–p90 de la evaluación sintética fue **{cobertura:.2%}** sobre
**{len(coincidencias):,} meses** de **{len(evaluacion):,} clientes**. El rango de
aceptación es 75% a 85%.

## Método

- Cada patrón del catálogo genera {_N_CALIBRACION} clientes de calibración y
  {_N_EVALUACION} de evaluación con las semillas {_SEMILLA_CALIBRACION} y
  {_SEMILLA_EVALUACION}, respectivamente. Cada cliente aporta 12 meses.
- La venta típica surge del índice sectorial con escala y amplitud propias del
  cliente. Los clientes sin veda adelantan o atrasan su campaña un mes con
  probabilidad del 20%. La captura usa promedios por etapa con errores comunes y por etapa.
  Las ventas futuras agregan ruido mensual, un choque común por trimestre y
  episodios puntuales de ventas bajas con probabilidad mensual del 7%. Los
  costos y gastos del cliente se mantienen fijos entre captura y realización.
  Los tres casos estrella ilustran la captura con evidencias. La cohorte
  sintética mide la incertidumbre de las ventas declaradas sin evidencias.
- Sobre los {len(calibracion):,} clientes de calibración se toma el percentil
  80 empírico del residuo logarítmico absoluto de ventas estandarizado por
  la volatilidad del patrón y el cuantil normal 0.9. Este multiplicador
  (**{factor:.6f}**) se aplica al ancho logarítmico de p10 y p90. La cohorte
  independiente mide la cobertura en UN con esos intervalos y los gastos
  descontados.
- El ejercicio mide el desempeño bajo los supuestos del generador. La
  precisión sobre negocios observados requiere una evaluación con datos
  externos consentidos.

## Error de la mediana y coherencia anual

| Métrica | Resultado |
|---|---:|
| MAPE de ventas p50 | {mean(errores_relativos_ventas):.2%} |
| MAE de UN p50 | S/ {mean(errores_absolutos):,.2f} |
| MAPE de UN p50, `UN ≠ 0` | {mean(errores_relativos):.2%} ({len(errores_relativos):,} meses) |
| MAPE de UN p50, `abs(UN) ≥ S/ {_PISO_MAPE:,.0f}` | {mean(errores_relativos_estables):.2%} ({len(errores_relativos_estables):,} meses) |
| Mayor diferencia absoluta de UN anual contra la captura | S/ {max(diferencias_anuales):,.2f} |

Para la UN, el MAPE divide el error absoluto por el valor absoluto de la UN
observada. Se reportan el valor general y el de meses alejados de cero para mostrar el
efecto del denominador. La UN anual declarada pondera la venta alta, normal
y baja por el número de meses de cada etapa de captura, aplica el margen y
descuenta doce veces los gastos mensuales. Las diferencias de céntimos se
deben al redondeo mensual.

## Sensibilidad de la captura

Cambio mediano de la UN p50 anual en soles frente a la captura de referencia,
perturbando un grupo de datos cada vez en la cohorte de evaluación.

| Dato perturbado | −20% | +20% |
|---|---:|---:|
{filas_sensibilidad}

## Casos estrella

Las capturas de Rosa, Martín y Luis están en
[`data/ciclos/casos_estrella.json`](../data/ciclos/casos_estrella.json).
Se muestran los primeros doce meses posteriores al desembolso.

| Cliente sintético | UN p50 anual (S/) | Diferencia con captura (S/) | Meses de cima | Meses de valle |
|---|---:|---:|---|---|
{chr(10).join(filas_casos)}

## Reproducción

```sh
PYTHONPATH=src python -m cuotaflex.ciclo.validacion --escribir
```

El comando actualiza este informe y
[`data/ciclos/calibracion.json`](../data/ciclos/calibracion.json), que emplea
el estimador. Sin la opción `--escribir`, imprime el informe en la salida
estándar.
"""
    return ajustes, informe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escribir", action="store_true", help="Actualiza el informe y la calibración.")
    args = parser.parse_args()
    ajustes, informe = validar()
    if args.escribir:
        (RUTA_DATOS / "calibracion.json").write_text(
            json.dumps(ajustes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (_RAIZ / "resultados" / "ciclo_validacion.md").write_text(informe, encoding="utf-8")
    else:
        print(informe, end="")


if __name__ == "__main__":
    main()
