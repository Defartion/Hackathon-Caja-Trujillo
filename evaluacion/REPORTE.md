# Evaluación del agente CuotaFlex

Se evaluaron 30 consultas con clientes sintéticos. 21 casos exigen cifras concretas con unidad. En todos se verifica el respaldo de las cifras emitidas.

| Modo | Casos | Exactitud de cifras | Herramienta correcta | Cumplimiento | Respuestas del LLM | p50 (ms) | p95 (ms) | Costo medio por consulta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Sin LLM | 30 | 100% | 100% | 100% | 0/30 | 0.7 | 46.9 | USD 0.00 |
| LLM simulado | 30 | 100% | 100% | 100% | 28/30 | 0.7 | 39.2 | USD 0.00 |

Los controles descartaron 2 de 2 borradores del LLM simulado con una cifra inventada o una garantía indebida. La respuesta de respaldo conservó las cifras esperadas y pasó los controles de cumplimiento.

## Cómo se midió

- **Exactitud.** Cada cifra debe estar respaldada por los resultados de las herramientas y cada cifra esperada debe aparecer con su unidad.
- **Herramienta.** La lista de herramientas usadas debe incluir la esperada por el caso.
- **Cumplimiento.** Se aplican las reglas del chat del asesor y las frases prohibidas del caso.
- **Latencia.** Los percentiles miden el procesamiento del mensaje con la sesión ya iniciada.
- **LLM simulado.** Las pruebas le indican la herramienta que debe solicitar. El orquestador ejecuta la llamada y el simulador redacta con los resultados. Su porcentaje de herramienta mide esa integración, mientras que la fila sin LLM mide el enrutamiento por palabras clave.
- **Costo.** Los modos locales tienen costo de API de USD 0.00. En modo real se usan los tokens informados por el proveedor y las tarifas indicadas al ejecutar el análisis.

La ejecución registrada usa los dos modos locales.

## Reproducir

```bash
python evaluacion/evaluar.py
```

Usa `--llm-real` con el proveedor y su clave configurados para añadir una corrida externa con los mismos casos sintéticos. Las opciones `--usd-por-millon-entrada` y `--usd-por-millon-salida` permiten calcular su costo.
