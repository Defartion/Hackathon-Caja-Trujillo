# Validación del ciclo económico

La cobertura p10–p90 de la evaluación sintética fue **79.84%** sobre
**7,680 meses** de **640 clientes**. El rango de
aceptación es 75% a 85%.

## Método

- Cada patrón del catálogo genera 25 clientes de calibración y
  40 de evaluación con las semillas 260401 y
  260402, respectivamente. Cada cliente aporta 12 meses.
- La venta típica surge del índice sectorial con escala y amplitud propias del
  cliente. Los clientes sin veda adelantan o atrasan su campaña un mes con
  probabilidad del 20%. La captura usa promedios por etapa con errores comunes y por etapa.
  Las ventas futuras agregan ruido mensual, un choque común por trimestre y
  episodios puntuales de ventas bajas con probabilidad mensual del 7%. Los
  costos y gastos del cliente se mantienen fijos entre captura y realización.
  Los tres casos estrella ilustran la captura con evidencias. La cohorte
  sintética mide la incertidumbre de las ventas declaradas sin evidencias.
- Sobre los 400 clientes de calibración se toma el percentil
  80 empírico del residuo logarítmico absoluto de ventas estandarizado por
  la volatilidad del patrón y el cuantil normal 0.9. Este multiplicador
  (**1.196965**) se aplica al ancho logarítmico de p10 y p90. La cohorte
  independiente mide la cobertura en UN con esos intervalos y los gastos
  descontados.
- El ejercicio mide el desempeño bajo los supuestos del generador. La
  precisión sobre negocios observados requiere una evaluación con datos
  externos consentidos.

## Error de la mediana y coherencia anual

| Métrica | Resultado |
|---|---:|
| MAPE de ventas p50 | 18.46% |
| MAE de UN p50 | S/ 885.11 |
| MAPE de UN p50, `UN ≠ 0` | 194.04% (7,680 meses) |
| MAPE de UN p50, `abs(UN) ≥ S/ 100` | 70.55% (7,328 meses) |
| Mayor diferencia absoluta de UN anual contra la captura | S/ 0.03 |

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
| Ventas alto, normal y bajo | -10,980.77 | +10,980.80 |
| Proporción de costo de ventas | +16,016.81 | -16,016.80 |
| Gastos operativos y tributarios | +3,667.35 | -3,667.35 |
| Carga familiar y otras cuotas | +3,409.03 | -3,409.05 |

## Casos estrella

Las capturas de Rosa, Martín y Luis están en
[`data/ciclos/casos_estrella.json`](../data/ciclos/casos_estrella.json).
Se muestran los primeros doce meses posteriores al desembolso.

| Cliente sintético | UN p50 anual (S/) | Diferencia con captura (S/) | Meses de cima | Meses de valle |
|---|---:|---:|---|---|
| E001 · arroz · Chepén | 15,536.99 | -0.01 | 2027-06, 2027-07 | 2027-01, 2027-02, 2027-03 |
| E002 · pesca artesanal · Pacasmayo | 22,290.01 | +0.01 | 2028-01, 2028-02, 2028-03 | 2027-05, 2027-06, 2027-07, 2027-08, 2027-09 |
| E003 · bodega · Trujillo | 2,820.03 | +0.03 | 2027-07, 2027-12 | 2027-02, 2027-03 |

## Reproducción

```sh
PYTHONPATH=src python -m cuotaflex.ciclo.validacion --escribir
```

El comando actualiza este informe y
[`data/ciclos/calibracion.json`](../data/ciclos/calibracion.json), que emplea
el estimador. Sin la opción `--escribir`, imprime el informe en la salida
estándar.
