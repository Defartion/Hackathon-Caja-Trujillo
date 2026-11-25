# Pitch de CuotaFlex · Final del Cajathón

Presentación de 12 láminas para acompañar la demo. Las cifras corresponden a la simulación calibrada de la fase 2 con clientes sintéticos. El estado de la alerta se cita con la fecha del comunicado.

| Material | Uso |
| --- | --- |
| [Pitch en PDF](CuotaFlex-pitch.pdf) | Proyectar sin depender de la conexión. |
| [Presentación editable](CuotaFlex-pitch.pptx) | Editar textos y tabla de impacto en PowerPoint o Impress. |
| [Guion](GUION.md) | Reparto de voces, versión de 6:20 y versión de 3:00. |
| [Banco de preguntas](PREGUNTAS.md) | 24 preguntas con respuestas y evidencia. |
| [Resumen A4 para el jurado](one-pager-final.pdf) | Imprimir a tamaño real. El QR abre el repositorio de GitHub. |
| [Fuente del resumen](generar_one_pager.py) | Actualizar el PDF con ReportLab. |
| [Concepto v2](../concepto/v2/CONCEPT_SOLUTION.md) · [PDF](../concepto/v2/export/CuotaFlex-Solution-Concept-v2.pdf) | Consultar el detalle técnico y la figura recalculada. |
| [Casos estrella del lote B](https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/fase-3/lote-b-qa/docs/demo/CASOS_ESTRELLA.md) | Preparar las fichas E001, E002 y E003 y abrir las capturas de respaldo. |

## Ensayo cronometrado

- [Pista principal · 6:20](ensayo-6m20.m4a)
- [Pista corta · 3:00](ensayo-3m.m4a)

Son pistas de ensayo en voz sintética. Cada cambio de tramo tiene un tono breve. Los silencios reservan el tiempo previsto para navegar por las apps y cambiar de persona. Las pistas reproducen la locución del guion. Queda pendiente ensayar con las voces del equipo y obtener la revisión de un integrante.

Las pistas usan Piper con el [modelo español Sharvard](https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/sharvard/medium/MODEL_CARD), entrenado con el [corpus Spanish Harvard](https://datashare.ed.ac.uk/handle/10283/574), citado en la ficha con licencia [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

## Fuentes

- [Resultados calibrados](../../resultados/CAMBIOS_FASE2.md), [resumen numérico](../../resultados/resumen.json), [backtest](../../resultados/backtest.md) y [sensibilidad](../../resultados/sensibilidad.md).
- [Evaluación del agente](../../evaluacion/REPORTE.md). Incluye el respaldo local y un proveedor simulado.
- [Comunicado ENFEN N.º 20-2026](https://enfen.imarpe.gob.pe/download/comunicado-oficial-enfen-n-20-2026/), del 13 de noviembre, verificado el 24 de noviembre de 2026. Consultar el comunicado más reciente antes de presentar.
- La [imagen de portada](img/rosa-ilustracion.jpg) se generó con ImageGen como ilustración del caso ficticio. El encargo fue un retrato editorial sin texto ni logos de una agricultora peruana ficticia en un arrozal de Chepén, con encuadre vertical y luz matinal natural.
