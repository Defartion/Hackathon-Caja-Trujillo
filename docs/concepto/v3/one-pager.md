# CuotaFlex

**Cuotas que se adaptan al flujo del negocio** · Cajathón 2026 · Desafío NEG-01 · Concepto v3

## Problema

Los microempresarios de La Libertad venden por temporadas, pero su capacidad de pago se evalúa con un ingreso promedio único y el core solo genera cuotas fijas. En la siembra, la veda o la baja comercial, la cuota fija puede superar lo que el negocio deja. Además, el ENFEN mantiene la Alerta de El Niño Costero (Comunicado N.° 20-2026). [Registro del ENFEN](../../../src/cuotaflex/integraciones/README_ENFEN.md).

## Solución

Una herramienta del **Asesor de Negocios** para créditos nuevos:

- **estima el ciclo económico** del cliente con el patrón de su sector y su zona, tomado de fuentes públicas y ajustado con la captura en campo, sin historial de pagos;
- **construye desde el inicio un plan** con cuotas y periodos variables, con **Cuota/UN ≤ factor en cada etapa**;
- aplica los costos de la Caja: TED base 360, seguros, prelación seguros → interés → capital, pendientes sin capitalizar y TCEA;
- muestra al **Asesor de Riesgos y al comité** el ciclo, las cuotas, Cuota/UN por etapa, los supuestos y la comparación con la cuota fija en escenarios adversos.

## Impacto en escenarios sintéticos

Prototipo actual, 600 clientes sintéticos con el mismo monto y plazo:

| Métrica | Cuota fija | Plan adaptado |
|---|---:|---:|
| Clientes con alguna etapa donde Cuota/UN > 0.85 | 45.8% | **34.3%** |
| Escenario El Niño · clientes con alguna etapa > 0.85 | 62.7% | **55.0%** |
| Interés total medio por crédito | S/ 2,060 | S/ 2,030 |

El motor de la final impone Cuota/UN ≤ factor en todas las etapas como restricción dura. Si no hay plan factible, propone menos monto o más plazo. [Cifras](cifras_cuota_un.json).

## Por qué es diferente

- **No es un tablero ni un chatbot:** modelo de ciclo con incertidumbre, optimización con restricciones de riesgo y un agente que verifica cada cifra.
- **Sin datos internos:** a la Caja solo le pide parámetros del producto, como el factor, las tasas de seguros y la política de gracia.

## Equipo

**Sabado de paz (CJT-WG3TXH).** Stefano Zamora · Sebastian Pelaez · Joaquin Diaz · Andre Ramirez.
