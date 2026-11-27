# Preguntas del jurado · Thinku

Cada respuesta está pensada para unos 30 segundos. Cuando el jurado pida evidencia, muestra la fila, la pantalla o la prueba que se cita debajo.

## Impacto y evidencia

### 01 · ¿Qué problema resuelve para una persona como Rosa?

En siembra, Rosa paga insumos y aún tiene ingresos bajos. En cosecha dispone de más caja. Thinku compara modalidades y puede mover parte de sus pagos hacia los meses de mayores ventas. El asesor ve el cronograma y la bitácora antes de evaluar la propuesta. En E001 se puede observar el cambio mes a mes.

Evidencia del caso [E001 y cronograma](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md#e001--rosa-agricultora-de-arroz-en-chepén)

### 02 · ¿Cuánto reduce el incumplimiento?

En la evaluación completa, el default pasa de 4,76 % con cuota fija a 2,05 % con Thinku. El atraso de más de treinta días pasa de 10,36 % a 4,82 %. Evaluamos seiscientos créditos sintéticos en doscientos escenarios. En un piloto mediríamos si el resultado se reproduce con la cartera y los costos reales de la Caja.

Evidencia de simulación [Resumen de resultados](../../resultados/resumen.json) · [Cambios de la fase 2](../../resultados/CAMBIOS_FASE2.md)

### 03 · ¿Cuánto del efecto se debe al cronograma?

Al mantener el mismo monto y plazo, el experimento de solo cronograma baja el default de 4,76 % a 3,45 %. En la corrida completa, con monto y plazo ajustables, baja a 2,05 %. La caída adicional es compatible con un mejor dimensionamiento dentro de esta comparación. En el piloto conviene reproducir los dos brazos de evaluación.

Evidencia de ambos experimentos [Cambios de la fase 2](../../resultados/CAMBIOS_FASE2.md)

### 04 · ¿Por qué baja la cartera colocada? ¿Pierde la Caja?

Cuando la cuota supera la capacidad estimada, el motor puede dimensionar un préstamo menor. La colocación baja de S/ 3,41 millones a S/ 2,85 millones en la corrida completa. En esa misma corrida, el margen neto total sube de S/ 655.866 a S/ 733.475. Mostraríamos ambos indicadores para que la Caja evalúe el intercambio entre alcance, riesgo y rentabilidad.

Evidencia de colocación y margen [Resumen de resultados](../../resultados/resumen.json)

### 05 · ¿Qué significa el margen mostrado?

El tablero divide el margen neto simulado entre la cartera colocada. Cuota fija da 19,24 % y el modo completo de Thinku 25,69 %. La comparación también cambia el monto colocado. Por eso mostramos el saldo de cartera y el margen total en soles junto con la tasa. El piloto debe incorporar fondeo, costos y pérdidas observados.

Evidencia de margen y denominador [Resumen de resultados](../../resultados/resumen.json)

### 06 · ¿Cómo usaron los datos de la SBS?

Usamos como referencia la mora de microempresa de cajas municipales, entre 5 % y 5,7 % en 2026 según la documentación de calibración. La SBS reporta una foto de cartera. Nuestra métrica de más de treinta días cuenta si el atraso ocurrió en algún momento del préstamo. La referencia ayuda a dimensionar el escenario y ambas métricas conservan su significado.

Evidencia y definición [Cambios de la fase 2](../../resultados/CAMBIOS_FASE2.md)

### 07 · ¿Y si el pronóstico falla?

En el backtest fuera de muestra, el intervalo p10 a p90 cubrió 79,5 % de las ventas sintéticas. También duplicamos la volatilidad en sensibilidad. El default subió con las dos estrategias, y Thinku mantuvo menor default en esa corrida. En un piloto mediríamos el error por rubro y revisaríamos los casos que se desvíen del rango previsto.

Evidencia de validación [Backtest](../../resultados/backtest.md) · [Sensibilidad](../../resultados/sensibilidad.md)

### 08 · ¿Qué pasa si no hay El Niño?

Sin una alerta, el préstamo sigue el cronograma previsto y conserva las condiciones de su modalidad. En sensibilidad se ensayó una probabilidad anual nula y Thinku mantuvo menor default en esa simulación. El ajuste estacional y la evaluación del excedente también sirven para meses de baja venta que son parte de una campaña normal.

Evidencia de escenario y disparador [Sensibilidad](../../resultados/sensibilidad.md) · [Integración ENFEN](../../src/cuotaflex/integraciones/README_ENFEN.md)

### 09 · ¿Funciona igual para todos los rubros?

En la cartera sintética completa, agricultura y pesca concentran buena parte de la mejora en atraso. Bodega y servicios empiezan con atraso observado nulo en esa corrida. El motor puede elegir cuota fija cuando es la mejor alternativa disponible. Proponemos un piloto por rubro y región para decidir dónde conviene utilizar cada modalidad.

Evidencia por rubro [Resumen de resultados](../../resultados/resumen.json)

### 10 · ¿Qué pasa si el cliente ahorra más o menos de lo previsto?

Evaluamos distintos niveles de gasto del sobrante mensual, desde ahorrar todo hasta gastar una parte considerable. El riesgo absoluto cambia con ese supuesto. Thinku mantuvo una tasa de default menor que la fija en los niveles probados. En un piloto conviene contrastar el supuesto de ahorro con la evidencia disponible y volver a ejecutar la sensibilidad.

Evidencia de escenarios [Sensibilidad](../../resultados/sensibilidad.md)

## Riesgo, cliente y cumplimiento

### 11 · ¿El producto aumenta el sobreendeudamiento?

El motor parte del excedente luego de gastos y otras deudas y evalúa la cuota en un escenario conservador. Si la propuesta supera esa capacidad, revisa monto o plazo y puede mantener la modalidad fija. Luis ya tenía otras obligaciones. Pidió S/ 8.000 y el motor propuso S/ 5.800. La decisión queda en la bitácora para revisión humana.

Evidencia en la ficha [Caso E003](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md#e003--luis-bodeguero-en-trujillo)

### 12 · ¿Cómo lo vería la SBS? ¿Es una reprogramación?

El cronograma estacional se propone en la originación. Un alivio posterior altera pagos según la cláusula que el piloto estudiaría. La Caja debe validar la clasificación, el tratamiento contable, el contrato y el reporte aplicable con su equipo de cumplimiento. La demo separa ambas operaciones y registra cambios y costos para que se puedan revisar.

Evidencia del recorrido [Cronograma y alivio en las apps](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md) · [Integración ENFEN](../../src/cuotaflex/integraciones/README_ENFEN.md)

### 13 · ¿El aplazamiento es gratis?

El cliente paga una cuota menor en el mes elegido. El saldo que difiere genera intereses y se reparte en las cuotas siguientes. El simulador muestra el nuevo cronograma y el costo adicional antes de confirmar. En el piloto, la Caja definiría el formato y las condiciones de comunicación para que el cliente pueda comparar.

Evidencia del recorrido [Modo cliente y tratamiento de avisos](../../src/cuotaflex/integraciones/README_ENFEN.md)

### 14 · ¿Qué ocurre si el ENFEN emite Vigilancia o cambia la alerta?

Vigilancia produce un aviso preventivo. El alivio se habilita con Alerta de El Niño Costero para los préstamos activos que tienen cláusula y saldo de alivios. El módulo registra la fuente, fecha y cambio de estado. El comunicado documentado para este pitch es el N.º 20-2026 del 13 de noviembre.

Evidencia del disparador [Integración ENFEN](../../src/cuotaflex/integraciones/README_ENFEN.md)

### 15 · ¿Qué pasa si el monto de un comercio parece exagerado?

Una venta alta de un mes se evalúa junto con el historial, el patrón del rubro y la incertidumbre del pronóstico. También se revisan margen, gastos y deudas. El asesor puede ajustar los parámetros y ver cómo cambia la oferta. Para operar con datos reales, la Caja tendría que validar los registros y controlar la calidad de las fuentes.

Evidencia de estimación [Backtest](../../resultados/backtest.md) · [Caso E003](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md#e003--luis-bodeguero-en-trujillo)

### 16 · ¿Quién toma la decisión crediticia?

Thinku genera una propuesta auditable. El asesor y los responsables de crédito conservan la decisión de acuerdo con las políticas de la Caja. La bitácora muestra qué modalidad se comparó, qué condiciones limitaron la oferta y qué cifra produjo el recálculo. El piloto debería medir también cuándo y por qué un asesor modifica una propuesta.

Evidencia de la decisión [Caso E001](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md#e001--rosa-agricultora-de-arroz-en-chepén)

## Tecnología e integración

### 17 · ¿Por qué no basta un tablero o un chatbot?

El tablero permite comparar escenarios de cartera. El chat deja consultar una decisión individual. Los dos se apoyan en un motor que estima ventas, compara modalidades, optimiza cuotas y verifica capacidad de pago. En el pitch se ve el efecto directo en un cronograma, un recálculo y una propuesta que puede revisar el asesor.

Evidencia del flujo [Evaluación del agente](../../evaluacion/REPORTE.md) · [Recorridos de demo](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md)

### 18 · ¿El LLM puede inventar cifras?

Sí, un borrador puede contener un monto inventado o una garantía indebida. El agente compara sus cifras con los resultados de las herramientas y usa una salida de respaldo si el borrador incumple las reglas. En la evaluación se descartaron los dos borradores incorrectos. Se ensayaron treinta consultas sintéticas por modo, con respaldo local y proveedor simulado.

Evidencia del control [Evaluación y metodología](../../evaluacion/REPORTE.md)

### 19 · ¿Qué hace el sistema si falla el proveedor de IA o la red?

La demo local mantiene las tres apps y el cálculo de las propuestas con plantillas. Para la señal oficial, el lector usa la última lectura si está disponible y marca su estado como desactualizado. Con la red caída y sin lectura previa, el modo oficial no habilita alivio. La demo reproduce el evento con un estado seguro y distinguible.

Evidencia de contingencias [Guía sin conexión](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/OFFLINE.md) · [Integración ENFEN](../../src/cuotaflex/integraciones/README_ENFEN.md)

### 20 · ¿Cómo se integra con el core actual de la Caja?

Probamos un espejo de un préstamo de demo y la lectura de su cronograma en Apache Fineract. Para conectar el core de la Caja haríamos un mapeo de clientes, préstamos, cuotas y estados en un entorno de pruebas. Luego validaríamos conciliación, permisos y reversión con el equipo de tecnología, antes de conectar una operación real.

Evidencia de integración [Espejo de Fineract y prueba](../../infra/fineract/README.md)

### 21 · ¿Se envían SMS o WhatsApp reales?

En la demo, cada aviso queda en una bandeja de salida con canal, plantilla, fecha y estado. Esto permite mostrar un aviso de alerta, un recordatorio o una confirmación de aplazamiento. Antes del piloto, la Caja tendría que seleccionar el canal, aprobar las plantillas, validar el consentimiento aplicable y medir entrega y atención de reclamos.

Evidencia de avisos [Bandeja de salida](../../src/cuotaflex/integraciones/README_ENFEN.md)

## Implementación y alcance

### 22 · ¿Cuánto cuesta implementarlo y qué datos necesitan?

El costo depende del esfuerzo de integración con el core, la preparación de datos, la operación y el canal de aviso. Presentaríamos una estimación a partir del entorno de pruebas. Para el piloto necesitamos ventas verificables por mes, margen, egresos, obligaciones, historial de pagos y datos del préstamo. La Caja define el acceso por rol y la retención.

Evidencia para estimar alcance [Espejo de Fineract](../../infra/fineract/README.md) · [Validación de ventas](../../resultados/backtest.md)

### 23 · ¿Cómo decidirían si el piloto se amplía?

Empezaríamos por agricultura y pesca en La Libertad con una comparación controlada. Mediríamos en ambos grupos atraso, default, margen neto, monto colocado y reclamos. También registraríamos cuántos asesores aceptan o corrigen una recomendación. Antes de ampliar el alcance, la Caja definiría los umbrales, revisaría la evidencia y acordaría las condiciones de seguimiento.

Evidencia para elegir los rubros [Resultados por rubro](../../resultados/resumen.json)

### 24 · ¿Qué se construyó antes y qué parte en el evento?

Antes de la final ya estaban el motor, las tres apps y la fase de calibración e integraciones. La preparación añadió QA, casos sintéticos y material de presentación. Para la declaración final, registraremos con Stefano el punto de partida, el trabajo realizado durante el evento, los recursos usados y los commits que corresponden a cada etapa.

Evidencia de trazabilidad [Plan de la final y declaración](../fases/fase-3/lote-c-plan-final.md) · [Historial del repositorio](https://github.com/Defartion/Hackathon-Caja-Trujillo/commits/main/)
