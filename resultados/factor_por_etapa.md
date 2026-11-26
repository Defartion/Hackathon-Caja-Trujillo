# Cuota / Utilidad Neta por etapa: cuota fija vs. plan por etapas

600 clientes sintéticos (semilla 2026), mismo monto, TEA y plazo que pidieron; desembolso 01/12/2026; TED base 360 por días exactos, desgravamen 0.077% mensual, prelación seguros → interés → capital; UN esperada de cada mes según el pronóstico (adaptador provisional hasta integrar el modelo de ciclo del lote B). El plan cumple el factor como restricción dura en el escenario esperado y, además, minimiza el monto que excedería la capacidad en los escenarios adversos (robustez).

## Factor 0.65

| Métrica | Cuota fija | Plan por etapas |
|---|---:|---:|
| Clientes con alguna etapa sobre el factor (todos) | 56.3% | 0% en los planes propuestos |
| Clientes con plan factible al monto pedido | — | 96.7% |
| En los factibles: clientes con alguna etapa sobre el factor | 54.8% | 0.0% |
| Escenario El Niño: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 2,389 | S/ 1,742 |
| Escenario El Niño: clientes con alguna etapa sobre el factor | 66.0% | 49.1% |
| Escenario Temporada alta 1 mes tarde: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 687 | S/ 347 |
| Escenario Temporada alta 1 mes tarde: clientes con alguna etapa sobre el factor | 54.8% | 45.7% |
| Escenario Ventas −20%: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 1,888 | S/ 810 |
| Escenario Ventas −20%: clientes con alguna etapa sobre el factor | 87.8% | 70.7% |
| Interés total medio (factibles) | S/ 2,063 | S/ 1,630 |
| TCEA media (factibles) | 47.01% | 46.78% |
| Meses de gracia promedio | — | 1.78 |

Cuando no hay plan factible al monto pedido, el motor sugiere en promedio un monto máximo del 85.5% de lo solicitado, o un plazo mayor.

| Rubro | Plan factible | Cuota fija sobre el factor |
|---|---:|---:|
| agricultura | 94.5% | 100.0% |
| bodega | 100.0% | 2.6% |
| calzado | 95.1% | 93.9% |
| comercio_campana | 97.6% | 58.4% |
| pesca | 89.3% | 100.0% |
| servicios | 100.0% | 2.1% |

## Factor 0.85

| Métrica | Cuota fija | Plan por etapas |
|---|---:|---:|
| Clientes con alguna etapa sobre el factor (todos) | 46.3% | 0% en los planes propuestos |
| Clientes con plan factible al monto pedido | — | 99.3% |
| En los factibles: clientes con alguna etapa sobre el factor | 46.0% | 0.0% |
| Escenario El Niño: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 2,227 | S/ 1,545 |
| Escenario El Niño: clientes con alguna etapa sobre el factor | 62.4% | 39.6% |
| Escenario Temporada alta 1 mes tarde: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 600 | S/ 202 |
| Escenario Temporada alta 1 mes tarde: clientes con alguna etapa sobre el factor | 46.0% | 26.3% |
| Escenario Ventas −20%: S/ de cuota por encima de la capacidad (promedio por cliente) | S/ 1,543 | S/ 427 |
| Escenario Ventas −20%: clientes con alguna etapa sobre el factor | 74.2% | 43.3% |
| Interés total medio (factibles) | S/ 2,092 | S/ 1,430 |
| TCEA media (factibles) | 47.03% | 46.73% |
| Meses de gracia promedio | — | 2.18 |

Cuando no hay plan factible al monto pedido, el motor sugiere en promedio un monto máximo del 87.8% de lo solicitado, o un plazo mayor.

| Rubro | Plan factible | Cuota fija sobre el factor |
|---|---:|---:|
| agricultura | 97.6% | 100.0% |
| bodega | 100.0% | 0.0% |
| calzado | 98.8% | 72.0% |
| comercio_campana | 100.0% | 28.8% |
| pesca | 100.0% | 100.0% |
| servicios | 100.0% | 0.0% |
