# CuotaFlex · Plan detallado por fases

**Cajathón 2026 · Caja Trujillo · Reto NEG-01 "Cuotas que se adaptan al flujo del negocio"**
Equipo: Sebastian, Joaquin, Stefano y Andre · Repositorio: `Defartion/Hackathon-Caja-Trujillo` (privado)

## Calendario general

| Fecha | Hito |
|---|---|
| 22 nov | Fase 0 terminada. Arranca la fase 1 |
| **24–26 nov** | **Entrega del Concept Solution** (confirmar la fecha exacta con la organización) |
| 25–29 nov | La organización evalúa los conceptos. En paralelo hacemos la fase 2 |
| 30 nov – 2 dic | Fase 3: preparación de la final |
| **3 y 4 dic** | **Final en el Hub UPAO**: dos días de construcción, demostración y pitch |

## Cómo trabajamos (todas las fases)

1. **4 lotes por fase (A, B, C y D), independientes:** cada uno en su rama `fase-N/lote-x-nombre` y con sus propios archivos.
2. **Integración:** cuando los 4 lotes están listos, se crea la rama `integracion/fase-N` desde `main` y se fusionan los cuatro. Ahí se corre `pytest`, se compilan todas las apps y se prueba el flujo completo.
3. **Paso a `main`:** solo cuando la integración está revisada. Después se preparan los lotes de la siguiente fase.
4. **Criterio de "hecho":** se cumplen los criterios de aceptación del lote, las pruebas pasan, hay capturas en el README y el PR está revisado por otro integrante.
5. **Datos:** siempre sintéticos. Los commits van a nombre de cada integrante.

---

## Fase 0 · Base (✅ terminada)

**Qué se construyó:**
- **Motor:**
  - Datos sintéticos por rubro de La Libertad.
  - Pronóstico probabilístico de ventas.
  - Políticas de elegibilidad y sobreendeudamiento.
  - Optimizador de cronograma (MILP con CVXPY y HiGHS).
  - Un agente que replanifica y explica.
- **Simulación:** Monte Carlo de cuota fija contra CuotaFlex.
- **API compatible con Fineract:** con aplazamiento de cuotas y registro automático de nuevos routers.
- **Pruebas:** 5 iniciales.
- **Concepto preliminar.**

**Resultado de referencia** (600 créditos × 200 escenarios):

| Indicador | Cuota fija | CuotaFlex |
|---|---|---|
| Atraso > 30 días | 16.3% | 7.3% |
| Default | 8.5% | 3.4% |
| Margen neto / cartera | 16.5% | 22.7% |

La mayor parte de la mejora viene de prestar el monto adecuado. El cronograma por sí solo baja el atraso de 16.3% a 14.3%.

---

## Fase 1 · Demo funcional y concepto (22–26 nov)

**Objetivo:** que el jurado pueda *ver y usar* la solución, y entregar el concepto a tiempo.
Las instrucciones detalladas están en `docs/fases/fase-1/entregas/`.

| Lote | Responsable | Entregable | Estado |
|---|---|---|---|
| A · App del asesor | Sebastian | Bandeja, ficha con pronóstico, propuesta, comparación de riesgo, bitácora y registro en el core | ✅ Rama `fase-1/lote-a-asesor` |
| B · App del cliente | Joaquin | App móvil: próxima cuota, cronograma por temporada, aplazamiento con vista previa del costo y alivio por El Niño | En curso |
| C · Tablero de simulación | Stefano | Controles de políticas, escenarios predefinidos, 4 indicadores y 4 gráficos, historial de corridas | En curso |
| D · Concept Solution | Andre | Documento final, diagramas, resumen de una página, correo a la organización, lista de verificación | **Urgente** |

**Integración (`integracion/fase-1`):**
- Las tres apps (5173, 5174, 5175) funcionan a la vez contra una sola API.
- Un préstamo registrado desde la app del asesor se puede ver y aplazar desde la app del cliente.
- El tablero corre el escenario "Base" en menos de 15 s.
- `pytest` pasa con las pruebas de los 4 lotes.
- Se consolidan los `requirements-lote-*.txt` en `requirements.txt`.

**Criterio de salida:** concepto entregado y las tres apps funcionando juntas en `main`.

---

## Fase 2 · Calidad del modelo e integración real (25–29 nov)

**Objetivo:** que los números resistan las preguntas del jurado y que la solución se conecte con
sistemas reales: core bancario, alertas oficiales e IA generativa.

### Lote A · Calibración y backtesting del modelo
**Archivos exclusivos:** `datos.py`, `pronostico.py`, `politica.py`, `simulacion.py`, `config/parametros.yaml`, `notebooks/` y `tests/test_fase2_a.py`.
1. **Calibrar la cartera sintética** para que la cuota fija dé una mora cercana a la de microempresa de una caja municipal: buscar la cifra pública de la SBS, de 5% a 8% aproximadamente. Hoy da 16%, porque la cartera está estresada a propósito.
2. **Backtesting del pronóstico:** validación con origen móvil, entrenando con 12 a 18 meses y pronosticando 6.
   - Métricas: MAPE, pérdida pinball por cuantil y cobertura del intervalo p10–p90 (debería cubrir alrededor de 80%).
   - Comparar AutoETS, perfil del rubro y su mezcla. Opcional: Chronos.
3. **Selección de producto por simulación:** en lugar de la regla fija (umbral de estacionalidad 0.15), simular las tres modalidades para cada cliente y elegir la de menor riesgo sin bajar la rentabilidad. Esto corrige el caso de calzado y comercio, donde la cuota estacional sale peor.
4. **Revisar el recargo por producto:** evaluar quitarlo en la cuota estacional, que no da opcionalidad al cliente, y mantenerlo en el aplazamiento.
5. **Análisis de sensibilidad del supuesto clave** (`fuga_caja_mensual`): un gráfico del beneficio de CuotaFlex según la fuga, de 0 a 0.4. Es la respuesta honesta a "¿y si el cliente ahorra?".
6. Actualizar `resultados/resumen.json` y escribir una nota de una página con los cambios en las cifras.

### Lote B · Integración con Apache Fineract real
**Archivos exclusivos:** `infra/fineract/`, `src/cuotaflex/integraciones/fineract.py` y `tests/test_fase2_b.py`.
1. Crear `docker-compose.yml` con Fineract y su base de datos, con versión fijada, healthcheck y un script de arranque.
2. Script `seed_fineract.py` que crea la oficina, el asesor y el **producto de crédito con cuotas variables habilitadas** (con su rango de días entre cuotas).
3. Adaptador `FineractClient` con la misma interfaz que el mock: crear cliente, crear préstamo, `addVariations`, aprobar, desembolsar, pagar y reprogramar.
4. **Comprobar en el Swagger de la versión instalada** el cuerpo exacto de `addVariations` y documentarlo.
5. Variable de entorno `CORE=mock|fineract`. La API usa uno u otro sin cambiar los frontends.
6. Probar el flujo completo contra Fineract real y grabar un GIF. **Plan B:** si Fineract falla el día de la final, se cambia a `CORE=mock`.

### Lote C · Disparador ENFEN y notificaciones
**Archivos exclusivos:** `src/cuotaflex/integraciones/enfen.py`, `src/cuotaflex/notificaciones/`, `src/cuotaflex/api/routers/alertas.py`, la función `estado_el_nino()` de `routers/cliente.py` y `tests/test_fase2_c.py`.
1. **Lector del comunicado oficial del ENFEN:** obtener el último comunicado y extraer el estado del sistema de alerta ("No activo", "Vigilancia" o "Alerta de El Niño costero").
   - Guardar la fuente y la fecha.
   - Respaldo manual si la página no responde.
2. **Tarea programada:** revisar el estado una vez al día. Si cambia a "Alerta", marcar los préstamos con la cláusula de rubros expuestos y habilitar el alivio.
3. **Notificaciones simuladas:** una bandeja de salida (outbox) con mensajes para SMS o WhatsApp.
   - Recordatorio de cuota 3 días antes.
   - Aviso de temporada baja.
   - Aviso de alerta El Niño con el alivio disponible.
   - Plantillas en español sencillo.
4. **Endpoint de impacto para la Caja:** cuántos préstamos y qué saldo quedan cubiertos por la alerta, por rubro y región.
5. Mostrar en el tablero del lote C de la fase 1 un indicador del estado del ENFEN (solo un componente nuevo).

### Lote D · Agente con IA generativa y salvaguardas
**Archivos exclusivos:** `src/cuotaflex/explicador.py`, `src/cuotaflex/api/routers/agente_chat.py`, `evaluacion/` y `tests/test_fase2_d.py`. Solo un cambio de una línea en `agente.py`: `explicar()` pasa a llamar a `explicador`.
1. **Explicación con LLM** para el cliente y para el asesor, con dos tonos distintos.
   - **Salvaguarda numérica:** toda cifra del texto tiene que existir en la propuesta. Si no, se usa la plantilla.
2. **Chat del asesor:** el asesor pregunta "¿por qué bajó el monto?" o "¿qué pasa si le doy 24 meses?". El agente responde usando sus herramientas (recalcular la propuesta, simular el escenario o consultar las políticas). No inventa datos.
3. **Salvaguardas de cumplimiento:** no prometer aprobación, no dar asesoría fuera del producto y mencionar siempre la TCEA y el costo de los aplazamientos.
4. **Conjunto de evaluación:** 30 casos con la respuesta esperada. Medir exactitud de cifras, cumplimiento de reglas, latencia y costo por consulta.
5. **Respaldo sin conexión:** si no hay API key o la red falla, se usan las plantillas.
6. **Antes de usarlo en la final, confirmar con la organización** si se permite la IA generativa y cómo se declara.

**Integración (`integracion/fase-2`):**
- Se vuelven a correr todas las simulaciones con el modelo calibrado.
- El flujo completo funciona con `CORE=fineract`.
- El modo El Niño se activa con el disparador del ENFEN.
- El chat del agente funciona dentro de la app del asesor.

**Criterio de salida:**
- Cifras calibradas y defendibles, publicadas en el concepto actualizado si la organización lo permite.
- Integración real funcionando, con su plan B probado.

---

## Fase 3 · Preparación de la final (24 nov – 1 dic)

**Objetivo:** demo estable, desplegada y ensayada, con el pitch listo. Instrucciones detalladas en `docs/fases/fase-3/`.

| Lote | Responsable | Entregable |
|---|---|---|
| A · Persistencia, roles y despliegue | Sebastian | SQLite por instantánea, PIN por rol, espejo automático en Fineract, Docker Compose, URLs públicas y `reset_demo` |
| B · QA y casos estrella | Joaquin | 3 casos estrella reproducibles (agricultora, pescador, bodeguero), pruebas de punta a punta con Playwright, carga ligera, modo sin conexión y Fineract en Windows |
| C · Plan de la final | Stefano | Diseño del módulo en vivo (pago a cosecha o % de ventas), plan por horas, lista de verificación, contingencias, verificador del entorno, video de respaldo y declaración de propiedad intelectual |
| D · Pitch | Andre | Concepto v2 con cifras de la fase 2, pitch de 10 a 12 láminas, guion de 5–7 y de 3 minutos, 20 o más preguntas y resumen impreso con QR |

**Integración (`integracion/fase-3`):** ensayo general completo, dos veces, con el cronómetro corriendo, sobre la versión desplegada y en modo sin conexión.
**Criterio de salida:** demo desplegada, pitch ensayado, video de respaldo listo y plan de los dos días aprobado por el equipo.

---

## Fase 4 · Ajuste a las preguntas frecuentes del NEG-01 (25 – 30 nov)

El 24 de noviembre la organización publicó 10 preguntas frecuentes que definen qué se evalúa:
- estimación del **ciclo económico** (sector y zona con fuentes públicas, sin historial de pagos);
- un **plan nuevo por etapas** con Cuota/UN ≤ factor del producto en cada etapa;
- **costos de la Caja** (TED base 360, seguros, prelación, pendientes sin capitalizar y TCEA);
- una **vista para el comité**;
- la **comparación con la cuota fija en escenarios adversos**.

No se mide la mora de una cartera real. Instrucciones en `docs/fases/fase-4/` y contratos en `CONTRATOS.md`.

| Lote | Responsable | Entregable |
|---|---|---|
| A · Motor financiero y plan | Sebastian | Constructor con Cuota/UN ≤ factor como restricción dura, prelación y pendientes, TCEA, comparación con la cuota fija, estrés y cifras para el pitch |
| B · Modelo del ciclo | Joaquin | Catálogo sector × zona con fuentes públicas, estimador con la captura del asesor, escenarios adversos y validación |
| C · Asesor y comité | Stefano | Nueva solicitud en 3 pasos y vista imprimible para el comité con validación del Asesor de Riesgos |
| D · Concepto, pitch y agente | Andre | **Concepto v3 subido antes del 26 nov**, pitch v2 y agente que explica el plan con un LLM externo |

---

## Durante la final (3 y 4 dic)

| Bloque | Qué se hace |
|---|---|
| Día 1, mañana | Calibrar con los datos o parámetros que entregue la Caja y volver a correr la simulación |
| Día 1, tarde | Construir el módulo en vivo (pago a cosecha o porcentaje de ventas) en el motor y en la app del cliente |
| Día 2, mañana | Integrar ese módulo en el tablero y en la comparación, más las pruebas de punta a punta |
| Día 2, tarde | Congelar el código, ensayar dos veces y presentar |

**Regla de oro:** desde 3 horas antes de presentar no se cambia código, solo datos y textos.
