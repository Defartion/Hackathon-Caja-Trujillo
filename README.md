# Thinku · Cuotas que se adaptan al flujo del negocio

**Cajathón 2026 · Caja Trujillo · Eje 4 (Inclusión financiera y resiliencia) · Reto NEG-01**

> ¿Cómo podríamos ofrecer alternativas de pago que se ajusten a las variaciones de ingresos de los
> microempresarios, sin comprometer su capacidad de pago ni la sostenibilidad financiera de Caja Trujillo?

Thinku es un motor que, para cada solicitud de crédito:

1. **Pronostica** las ventas del negocio con incertidumbre (p10/p25/p50/p90) combinando historial en la Caja,
   estacionalidad de negocios similares y la observación del asesor.
2. **Evalúa** elegibilidad y riesgo de sobreendeudamiento con las políticas de la Caja.
3. **Elige el producto** adecuado: cuota fija, cuota fija con 2 aplazamientos o cuotas estacionales,
   más una cláusula de alivio que se activa con la alerta de El Niño costero del ENFEN.
4. **Optimiza el cronograma** (programación entera mixta): cada cuota cabe en la capacidad del escenario
   conservador y el valor presente cierra el crédito, así que la rentabilidad se mantiene.
5. **Valida y explica** la propuesta al asesor y al cliente, y la carga en Fineract (o en la API compatible).
6. **Simula miles de escenarios** para medir el efecto en mora y rentabilidad frente a la cuota fija.

## Resultados de la simulación (datos sintéticos)

600 créditos × 200 escenarios de ingresos y El Niño, con las mismas trayectorias para ambas estrategias
(`python scripts/simular.py`):

| Indicador | Cuota fija | Thinku completo | Solo cronograma |
|---|---|---|---|
| Créditos con atraso > 30 días | 16.3% | **7.3%** (-55%) | 14.3% (-12%) |
| Default (3 cuotas impagas) | 8.5% | **3.4%** (-60%) | 7.7% (-10%) |
| Margen neto / cartera | 16.5% | **22.7%** | 17.1% |
| Cartera colocada | S/ 4.51 M | S/ 3.89 M (-14%) | S/ 4.51 M |

*Completo* incluye el dimensionamiento responsable del monto y del plazo; *solo cronograma* mantiene
el monto y el plazo solicitados para aislar el efecto de las cuotas flexibles. Son datos sintéticos y
supuestos referenciales: hay que calibrarlos con la información de la Caja (ver `docs/CONCEPTO.md`).

## Estructura

```
config/parametros.yaml      parámetros de negocio y de riesgo (editables en vivo)
src/cuotaflex/
  datos.py                  cartera sintética (rubros de La Libertad, estacionalidad, historial)
  pronostico.py             pronóstico probabilístico (statsforecast AutoETS + perfil del rubro + asesor)
  politica.py               elegibilidad, sobreendeudamiento, producto, validación
  optimizador.py            cronograma óptimo (CVXPY + HiGHS, MILP)
  agente.py                 agente asesor: orquesta, replanifica y explica (LLM opcional)
  simulacion.py             Monte Carlo cuota fija vs. Thinku
  cuentas.py                cuentas con correo y contraseña (además del PIN por rol)
  cronograma.py             vencimientos, desglose y pagos de cada cuota (en orden o adelantados)
  api/main.py               API compatible con Fineract (+ aplazamiento)
scripts/                    simular.py, demo_agente.py
tests/                      pruebas del motor y de la API
docs/                       CONCEPTO.md (concept solution), ARQUITECTURA.md, diseno/ (sistema de diseño)
```

## Uso rápido

```bash
pip install -r requirements.txt
pytest                                   # pruebas
python scripts/demo_agente.py 3          # propuestas del agente
python scripts/simular.py                # KPIs -> resultados/
PYTHONPATH=src uvicorn cuotaflex.api.main:app --reload   # API en http://127.0.0.1:8000/docs
```

## Tecnología existente declarada

Apache Fineract y Mifos (opcionales; aquí se integran con una API propia compatible), CVXPY, HiGHS,
statsforecast, FastAPI, NumPy y pandas. SDV, Chronos y el SDK de Anthropic son opcionales. Todos los datos son sintéticos.
