# Cuota / Utilidad Neta por etapa: cuota fija vs. plan por etapas

600 clientes sintéticos (semilla 2026), mismo monto, TEA y plazo que pidieron; desembolso 01/12/2026; TED base 360 por días exactos, desgravamen 0.077% mensual, prelación seguros → interés → capital; UN esperada de cada mes según el pronóstico (adaptador provisional hasta integrar el modelo de ciclo del lote B). El plan cumple el factor como restricción dura en el escenario esperado y, además, minimiza el monto que excedería la capacidad en los escenarios adversos (robustez).

## Factor 0.65

| Métrica | Cuota fija | Plan por etapas |
|---|---:|---:|
| Clientes con alguna etapa sobre el factor (todos) | 56.3% | 0% en los planes propuestos |
| Clientes con plan factible al monto pedido | — | 95.2% |
| En los factibles: clientes con alguna etapa sobre el factor | 54.1% | 0.0% |
| Escenario El Niño: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 2,315 | S/ 1,670 |
| Escenario El Niño: clientes con alguna etapa sobre el factor | 65.5% | 48.3% |
| Escenario Temporada alta 1 mes tarde: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 647 | S/ 323 |
| Escenario Temporada alta 1 mes tarde: clientes con alguna etapa sobre el factor | 54.1% | 44.1% |
| Escenario Ventas −20%: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 1,843 | S/ 781 |
| Escenario Ventas −20%: clientes con alguna etapa sobre el factor | 87.6% | 70.4% |
| Interés total medio (factibles) | S/ 2,063 | S/ 1,620 |
| TCEA media (factibles) | 47.0% | 46.79% |
| Meses de gracia promedio | — | 1.64 |

Cuando no hay plan factible al monto pedido, el motor sugiere en promedio un monto máximo del 83.1% de lo solicitado, o un plazo mayor.

| Rubro | Plan factible | Cuota fija sobre el factor |
|---|---:|---:|
| agricultura | 89.8% | 100.0% |
| bodega | 100.0% | 2.6% |
| calzado | 95.1% | 93.9% |
| comercio_campana | 96.0% | 58.4% |
| pesca | 87.5% | 100.0% |
| servicios | 100.0% | 2.1% |

## Factor 0.85

| Métrica | Cuota fija | Plan por etapas |
|---|---:|---:|
| Clientes con alguna etapa sobre el factor (todos) | 46.3% | 0% en los planes propuestos |
| Clientes con plan factible al monto pedido | — | 98.8% |
| En los factibles: clientes con alguna etapa sobre el factor | 45.7% | 0.0% |
| Escenario El Niño: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 2,202 | S/ 1,526 |
| Escenario El Niño: clientes con alguna etapa sobre el factor | 62.2% | 39.5% |
| Escenario Temporada alta 1 mes tarde: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 587 | S/ 203 |
| Escenario Temporada alta 1 mes tarde: clientes con alguna etapa sobre el factor | 45.7% | 25.3% |
| Escenario Ventas −20%: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 1,526 | S/ 429 |
| Escenario Ventas −20%: clientes con alguna etapa sobre el factor | 74.0% | 44.7% |
| Interés total medio (factibles) | S/ 2,089 | S/ 1,419 |
| TCEA media (factibles) | 47.02% | 46.76% |
| Meses de gracia promedio | — | 2.04 |

Cuando no hay plan factible al monto pedido, el motor sugiere en promedio un monto máximo del 83.8% de lo solicitado, o un plazo mayor.

| Rubro | Plan factible | Cuota fija sobre el factor |
|---|---:|---:|
| agricultura | 96.1% | 100.0% |
| bodega | 100.0% | 0.0% |
| calzado | 98.8% | 72.0% |
| comercio_campana | 99.2% | 28.8% |
| pesca | 100.0% | 100.0% |
| servicios | 100.0% | 0.0% |
