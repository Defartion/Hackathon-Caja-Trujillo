# CuotaFlex

**Cuotas que se adaptan al flujo del negocio** · Cajathón 2026 · Caja Trujillo · Desafío NEG-01

## Problema

Los microempresarios de La Libertad venden por temporadas (agricultura, pesca, campañas comerciales, calzado), pero pagan la misma cuota todos los meses. En temporada baja se atrasan por falta de liquidez, no por falta de capacidad. Y El Niño costero golpea a rubros enteros a la vez: hoy el ENFEN mantiene la alerta.

## Solución

Un agente para el asesor de negocios que:

- pronostica las ventas del cliente con incertidumbre (cuantiles p10 a p90);
- elige entre cuota fija, cuota con hasta 2 aplazamientos o cuota estacional;
- optimiza el cronograma para que cada cuota quepa en el escenario conservador, sin que la Caja pierda valor presente;
- activa un alivio pactado si el ENFEN declara alerta de El Niño costero;
- registra el cronograma en el core con una API compatible con Apache Fineract.

## Impacto, en simulación con datos sintéticos

600 créditos y 200 escenarios por crédito, con las mismas trayectorias para las dos estrategias:

| Indicador | Cuota fija | CuotaFlex |
|---|---|---|
| Créditos con atraso > 30 días | 16.3% | **7.3%** |
| Default (3 cuotas impagas seguidas) | 8.5% | **3.4%** |
| Margen neto / cartera | 16.5% | **22.7%** |

La cartera colocada es 14% menor porque el agente no sobreendeuda, y la mayor parte del efecto viene de dimensionar bien el monto y el plazo. Fuente: `resultados/resumen.json`.

## Por qué es diferente

- **No es un chatbot ni un tablero:** decide, optimiza con restricciones de riesgo y mide su efecto con una simulación causal.
- **La incertidumbre es parte del diseño:** cada cuota se calcula contra el escenario conservador (p25), no contra el promedio.
- **El Niño con un disparador objetivo:** la alerta oficial del ENFEN activa el alivio, sin trámites.
- **Ya funciona:** el motor, la API y las pruebas están construidos. La fase presencial se dedica a adaptarlo a los datos y sistemas de la Caja.

## Equipo

**Sabado de paz** (CJT-WG3TXH): Stefano Zamora (coordinador; simulación y tablero) · Sebastian Pelaez (motor, API e integración) · Joaquin Diaz (app del cliente) · Andre Ramirez (concepto, pruebas y demo). Cuatro perfiles de desarrollo tecnológico: web, backend y APIs, apps móviles, integración de sistemas, IA generativa y QA.
