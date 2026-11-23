# Cambios en las cifras · Fase 2, lote A

Cartera sintética de 600 créditos × 200 escenarios (semilla 2026). Cada celda muestra cuota fija → CuotaFlex.

## Simulación completa (con dimensionamiento de monto y plazo)

| Indicador | Fase 1 | Fase 2 (calibrada) |
|---|---|---|
| Atraso > 30 días en la vida del crédito | 16.26% → 7.28% | 10.36% → 4.82% |
| Default (3 cuotas impagas) | 8.53% → 3.42% | 4.76% → 2.05% |
| Margen neto / cartera | 16.45% → 22.71% | 19.24% → 25.69% |
| Cartera colocada | S/ 4.51 M → 3.89 M | S/ 3.41 M → 2.85 M |

## Solo cronograma (mismo monto y plazo que pidió el cliente)

| Indicador | Fase 1 | Fase 2 (calibrada) |
|---|---|---|
| Atraso > 30 días | 16.26% → 14.33% | 10.36% → 7.47% |
| Default | 8.53% → 7.69% | 4.76% → 3.45% |
| Margen neto / cartera | 16.45% → 17.1% | 19.24% → 21.48% |

## Qué cambió y por qué (para el concepto y el pitch)

1. **Cartera calibrada contra la SBS.** La cuota fija pasa de 16% a ~10% de créditos con algún atraso > 30 días y ~4.8% de default. Es coherente con la mora de microempresa de cajas municipales (5%–5.7% en 2026, una foto de un mes); nuestra métrica acumula toda la vida del crédito, por eso es mayor. Detalle en `calibracion.md`.
2. **Selección de producto por simulación.** El agente simula fija, aplazamiento y estacional sobre los escenarios de *su propio pronóstico* (no conoce el generador de la cartera) y elige la de menor default sin perder más de 5% de VPN. Esto corrige el caso de calzado y comercio, donde la regla fija de la fase 1 empeoraba.
3. **El cronograma por sí solo ya mueve la aguja.** Con el mismo monto y plazo, el default baja ~28% (antes ~10%) y el margen sube ~2 pp. La mayor parte del efecto total aún viene de prestar el monto adecuado, y se dice tal cual.
4. **Pronóstico validado.** El backtesting fuera de muestra elige el perfil del rubro con incertidumbre calibrada (cobertura p10–p90 de 79.5%, ideal 80%). Detalle en `backtest.md`.
5. **Robusto a los supuestos.** Aun si el cliente ahorrara todo su sobrante, si hubiera El Niño seguro o si las ventas fueran el doble de volátiles de lo estimado, CuotaFlex tiene menos default que la cuota fija. Detalle en `sensibilidad.md`.

**Por rubro (simulación completa):** ningún rubro empeora en mora ni en rentabilidad por sol prestado. En calzado el VPN por crédito baja porque se presta 23% menos, pero la rentabilidad por sol sube de 0.227 a 0.285 y la mora cae de 3.2% a 0.9%.
