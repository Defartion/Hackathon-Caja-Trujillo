# Guion de la final · Thinku

La versión principal dura **6 min 20 s**, incluida la demo. La versión corta dura **3 min**. Las franjas reservan tiempo para clics, pausas y cambios de voz. Los nombres identifican el reparto propuesto para el ensayo.

Antes de salir, abre la presentación y las pestañas del asesor, cliente y tablero. Carga E001 y E003 en la bandeja. Desembolsa E002 en el core de demo y abre su préstamo en la app cliente con `?loanId=<id>&demo=1`. Deja la alerta de demo apagada y la cuota original a la vista. Conserva las capturas por si una pantalla tarda en responder. [Guion y capturas de los casos estrella](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md)

## Versión principal · 6:20

### 0:00–0:40 · André · Lámina 1

> Rosa cultiva arroz en Chepén. En la siembra paga insumos y mano de obra, mientras que la mayor parte de sus ventas llega después de la cosecha. Una cuota fija le exige el mismo pago en ambos momentos. Aunque pueda sostener el crédito durante la campaña, un mes de poca caja puede empujarla al atraso. Nuestra pregunta fue cómo diseñar un crédito que siga el flujo de Rosa y que la Caja pueda evaluar antes de prestarle.

### 0:40–1:20 · Stefano · Láminas 2 y 3

> En La Libertad, la estacionalidad también afecta a la pesca y al comercio de campaña. La mora de microempresa de cajas municipales observada en la referencia SBS estuvo entre 5 % y 5,7 % en 2026. Es una medición de cartera en un mes. Nuestra simulación cuenta atrasos a lo largo del crédito. El comunicado del ENFEN del trece de noviembre mantuvo la Alerta de El Niño Costero. Thinku adapta el calendario al flujo del negocio con cuota fija, fija con aplazamientos o estacional, según lo que el motor determine para cada solicitud.

### 1:20–2:00 · Sebastián · Lámina 4

> Primero estimamos ventas por mes y su incertidumbre. Usamos el escenario conservador p25 para dimensionar la cuota en función del excedente después de gastos y otras deudas. Probamos las tres modalidades en escenarios compartidos de ventas y El Niño. La selección busca menor incumplimiento y conserva un piso de valor presente frente a la fija. Después optimizamos el cronograma y dejamos la decisión en la bitácora. Si la solicitud queda fuera de capacidad, el motor revisa el plazo y el monto. Joaquín va a mostrar cómo se ven estas decisiones en las apps.

### 2:00–3:45 · Joaquín · Lámina 5 y demo en vivo

**2:00–2:35 · Rosa, E001.** Frente a la ficha del asesor, abre **Bitácora del agente** y señala **Selección por simulación**. Muestra las cuotas de siembra y cosecha.

> En Rosa, el motor eligió cuotas estacionales. Miren el cronograma. En los meses de siembra del primer año paga ciento cincuenta soles con noventa y un céntimos. El pago sube a setecientos setenta y seis soles con trece céntimos en cosecha, cuando el negocio vende más. La bitácora muestra las modalidades que se evaluaron.

**2:35–3:10 · Martín, E002.** Abre el préstamo activo en la app cliente. Activa la alerta de demo, muestra el banner y pulsa **Usar alivio**. Si alcanza el tiempo, abre el distintivo en el tablero.

> Martín se dedica a la pesca artesanal en Pacasmayo. Aquí reproducimos la alerta en modo demo. Su siguiente cuota pasa de trescientos quince soles con ochenta céntimos a ciento diez soles con cincuenta y tres céntimos. La app muestra el cronograma ajustado, con el saldo diferido y sus intereses. En el tablero podemos ver los préstamos cubiertos.

**3:10–3:45 · Luis, E003.** Vuelve al asesor. Abre el chat, pulsa **¿Por qué bajó el monto?** y señala **Cifras verificadas**. Regresa a la lámina de impacto.

> Luis tiene una bodega y ya paga otras deudas. Pidió ocho mil soles y el motor propuso cinco mil ochocientos. En el chat pregunto por qué bajó. La respuesta consulta la bitácora y pasa una verificación de cifras. Esta es la misma decisión que el asesor ve en la ficha.

### 3:45–4:42 · Sebastián · Láminas 6 y 7

> Probamos una cartera sintética de seiscientos créditos en doscientos escenarios. En la simulación completa, el default pasa de 4,76 % a 2,05 % y el atraso de más de treinta días de 10,36 % a 4,82 %. El margen neto sobre cartera sube de 19,24 % a 25,69 %, con una colocación menor. Al mantener monto y plazo, el cronograma baja el default a 3,45 %. El ajuste de monto y plazo explica la caída adicional a 2,05 % en esta comparación. La prueba de sensibilidad conserva la ventaja en default cuando duplicamos la volatilidad de ventas, aunque aumenta el riesgo de ambas estrategias. La cobertura fuera de muestra del rango p10 a p90 fue 79,5 % en datos sintéticos.

### 4:42–5:29 · Stefano · Láminas 8 y 9

> Antes de ofrecer el crédito, mostramos la tasa efectiva anual, las cuotas y el costo adicional del aplazamiento. La bitácora conserva los motivos de elegibilidad y cada cifra en las respuestas del agente debe venir del motor. La evaluación probó treinta consultas sintéticas en modo local y con un proveedor simulado. Detectó los dos borradores inválidos y usó una respuesta de respaldo. También probamos el espejo con Apache Fineract. La otra integración consulta el comunicado del ENFEN, lo cruza con préstamos elegibles y prepara avisos simulados. El modo local conserva el recorrido cuando perdemos internet.

### 5:29–6:20 · André · Láminas 10 a 12

> El agente produce una propuesta, compara alternativas y puede recalcularla cuando el asesor cambia los parámetros. El tablero permite evaluar escenarios de cartera. El chat hace consultable la decisión y conserva el vínculo con el motor. Para probarlo con la Caja, proponemos un piloto en agricultura y pesca en La Libertad. Necesitamos ventas mensuales verificables, margen, gastos, obligaciones y registros de pago. La Caja definiría los límites de riesgo, supervisaría las decisiones y mediría atraso, rentabilidad y reclamos junto con la colocación. Somos André, Sebastián, Stefano y Joaquín. El valor para Rosa es recibir un calendario que pueda pagar. Para la Caja, es saber cómo se llegó a esa decisión y poder comprobar sus resultados.

## Versión corta · 3:00

Para la versión corta, deja las fichas de Rosa y Luis abiertas junto al préstamo activo de Martín. Muestra una acción por caso y regresa a impacto. Si la transición del navegador se demora, usa la imagen del resultado y continúa.

### 0:00–0:30 · André · Gancho

> Rosa cultiva arroz en Chepén. Durante la siembra tiene gastos y pocas ventas. En cosecha recibe gran parte de sus ingresos. La cuota fija le pide el mismo pago cada mes. Thinku estima el flujo, compara modalidades de crédito y ajusta el cronograma a la capacidad de pago. La bitácora le permite al asesor revisar el cálculo antes de tomar una decisión.

### 0:30–1:35 · Joaquín · Demo E001, E002 y E003

> Esta es Rosa. En su ficha se ve que el motor eligió cuotas estacionales y asignó pagos menores en siembra. Aquí está Martín. El modo demo reproduce una alerta del ENFEN y el alivio reduce su próxima cuota de trescientos quince soles con ochenta céntimos a ciento diez con cincuenta y tres. El saldo diferido genera intereses. Por último, Luis solicitó ocho mil soles. Como ya tiene otras deudas, el agente propuso cinco mil ochocientos y puede explicar el ajuste con cifras verificadas.

### 1:35–2:22 · Sebastián · Impacto y robustez

> Sobre seiscientos créditos sintéticos en doscientos escenarios, el default baja de 4,76 % a 2,05 % en la simulación completa. Solo con el cronograma, manteniendo monto y plazo, llega a 3,45 %. El margen neto sobre cartera sube de 19,24 % a 25,69 % con menor colocación. También probamos qué ocurre si sube la volatilidad, si cambia el ahorro o si El Niño se vuelve más probable. Thinku tuvo menor default en los escenarios analizados. El piloto mediría si el efecto aparece en la cartera real.

### 2:22–3:00 · Stefano y André · Integraciones, piloto y cierre

**Stefano · 2:22–2:42**

> Fineract recibe el espejo del préstamo de prueba y el ENFEN aporta la señal oficial. Mostramos tasa anual y costo adicional del aplazamiento. El agente se apoya en cálculos verificables y puede funcionar con plantillas cuando el proveedor no está disponible.

**André · 2:42–3:00**

> El siguiente paso es un piloto controlado en La Libertad. La Caja revisaría la política, supervisaría al asesor y mediría colocación, atraso, rentabilidad y experiencia del cliente. Thinku ayuda a elegir una propuesta que el negocio pueda sostener durante su campaña.

## Referencias para el ensayo

- Cifras de cartera, comparación a monto y plazo constantes y calibración SBS. [Cambios de la fase 2](../../resultados/CAMBIOS_FASE2.md) · [Resumen](../../resultados/resumen.json)
- Validación del pronóstico y escenario de volatilidad. [Backtest](../../resultados/backtest.md) · [Sensibilidad](../../resultados/sensibilidad.md)
- Datos de la alerta y alcance del agente. [ENFEN](../../src/cuotaflex/integraciones/README_ENFEN.md) · [Evaluación](../../evaluacion/REPORTE.md)
