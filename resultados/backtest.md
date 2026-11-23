# Backtesting del pronóstico de ventas

Cartera sintética de 300 clientes, origen móvil (4 orígenes, entrenamiento de 18 a 21 meses, horizonte de 6 meses). Pinball normalizado por la venta media del cliente (menor es mejor).

| Método | MAPE p50 | Pinball medio | Cobertura p10–p90 (ideal 80%) | Ventas ≥ p25 (ideal 75%) |
|---|---|---|---|---|
| perfil (sigma x1.3) | 16.5% | 0.0540 | 79.5% | 76.5% |
| perfil (sigma x1.5) | 16.3% | 0.0545 | 86.0% | 80.6% |
| perfil (sigma x1.0) | 16.7% | 0.0551 | 67.7% | 70.2% |
| mixto 0.3 (sigma x1.3) | 17.1% | 0.0558 | 81.2% | 77.2% |
| mixto 0.5 (sigma x1.3) | 18.1% | 0.0590 | 80.1% | 76.8% |
| mixto 0.5 (sigma x1.0) | 18.2% | 0.0592 | 75.3% | 73.8% |
| statsforecast | 21.8% | 0.0721 | 74.7% | 75.0% |

**Mejor método por pinball medio: `perfil (sigma x1.3)`.**

## Por rubro (mejor método)

| Rubro | MAPE | Cobertura p10–p90 | Ventas ≥ p25 |
|---|---|---|---|
| agricultura | 22.7% | 78.8% | 76.6% |
| bodega | 8.1% | 81.6% | 78.2% |
| calzado | 17.4% | 82.3% | 80.8% |
| comercio_campana | 16.4% | 77.7% | 72.5% |
| pesca | 26.4% | 82.5% | 79.7% |
| servicios | 10.9% | 76.7% | 75.4% |
