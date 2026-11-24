# CuotaFlex

**Cuotas que se adaptan al flujo del negocio** · Cajathón 2026 · Desafío NEG-01 · Concepto v2

## Problema

Los microempresarios de La Libertad venden por temporadas y pagan cuotas mensuales constantes. En los meses de siembra, veda o baja comercial, un negocio viable puede quedarse sin liquidez para pagar. El ENFEN documentó la Alerta de El Niño Costero en el Comunicado N.° 20-2026 del 13 de noviembre. [Registro de la fase 2](../../../src/cuotaflex/integraciones/README_ENFEN.md).

## Solución

CuotaFlex ayuda al asesor a elegir entre cuota fija, cuota con aplazamientos y cuota estacional. Pronostica el flujo, simula alternativas y ajusta monto, plazo y cronograma según la capacidad estimada en el escenario p25. La bitácora muestra cómo llegó a la propuesta y el chat verifica sus cifras con las herramientas del motor.

El cliente ve su cronograma, la TEA y el costo de aplazar antes de confirmar. La alerta oficial habilita el alivio pactado. El prototipo registra el préstamo en el core de demo y cuenta con un espejo en Apache Fineract.

## Impacto simulado

Cartera de 600 créditos sintéticos y 200 escenarios por crédito, con trayectorias compartidas entre las estrategias.

| Indicador | Cuota fija | CuotaFlex completo | Solo cronograma |
|---|---:|---:|---:|
| Créditos con atraso > 30 días | 10.4% | **4.8%** | 7.5% |
| Default (3 cuotas impagas seguidas) | 4.8% | **2.1%** | 3.5% |
| Margen neto / cartera | 19.2% | **25.7%** | 21.5% |
| Cartera colocada | S/ 3.41 M | **S/ 2.85 M** | S/ 3.41 M |

En el modo completo la cartera es **16% menor**. El cronograma flexible reduce el default aun con monto y plazo constantes. El dimensionamiento añade parte de la reducción y modera la colocación. Las cifras corresponden a simulaciones con datos sintéticos. [Resultados de la fase 2](../../../resultados/resumen.json).

## Qué cambió desde la v1

La calibración contra la SBS corrigió la línea base de la cartera sintética. El producto se selecciona por simulación y el backtest valida la cobertura del pronóstico, que alcanzó **79.5%** en el intervalo p10 a p90. [Cambios de fase 2](../../../resultados/CAMBIOS_FASE2.md) · [Backtest](../../../resultados/backtest.md).

## Equipo

**Sabado de paz (CJT-WG3TXH).** Stefano Zamora · Sebastian Pelaez · Joaquin Diaz · Andre Ramirez.
