# Calibración de la cartera sintética

## Referencia
- Mora de **cajas municipales**: 5.66% (febrero 2026) y 5.1% (julio 2026), según cifras de la SBS citadas por la prensa (Infobae, abril 2026).
- Mora de **microempresa** en el sistema: 5% en junio 2026, cerca del máximo histórico de 2023, año de El Niño (InfoMercado, con cifras SBS).
- Verificar con el último boletín estadístico de la SBS (cartera atrasada de microempresa, cajas municipales) antes de la final.

## Cómo se compara
La SBS publica la **mora contable de un mes** (cartera atrasada / cartera total). La simulación mide el
**% de créditos que alguna vez tuvieron un atraso > 30 días durante toda su vida** (12 a 24 meses), que
es necesariamente mayor. El objetivo fue que la cuota fija quedara en ~8%–12% de atraso acumulado y
~3%–5% de default, órdenes de magnitud compatibles con una mora mensual de ~5%.

## Qué se ajustó (`config/parametros.yaml` → `cartera_sintetica`)
| Parámetro | Fase 1 | Fase 2 |
|---|---|---|
| Cuota solicitada / excedente libre | 35%–60% | 30%–42% |
| Gasto del sobrante mensual (`fuga_caja_mensual`) | 0.15 | 0.15 (sin cambio; ver sensibilidad) |
| Distribución de atrasos previos | 0/3/8/15/35/70 días | igual |

Resultado (300 × 100): cuota fija con 10.1% de atraso > 30 días y 4.3% de default (antes 16.8% y 8.4%).
En la corrida oficial (600 × 200): 10.4% y 4.8%.

## Límites
- Los perfiles estacionales por rubro son referenciales; deben validarse con asesores de campo.
- Con datos reales de la Caja se debe recalibrar todo: este archivo documenta el procedimiento.
