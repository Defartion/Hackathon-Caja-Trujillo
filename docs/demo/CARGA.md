# Carga ligera de CuotaFlex

Medición del 2026-11-24T12:43:40-05:00 en macOS-26.6.2-arm64-arm-64bit, Python 3.12.14 y 8 núcleos lógicos.

Se ejecutaron 10 usuarios concurrentes durante 120 s en una API local desechable. Se completaron 4591 intentos en 120.3 s, incluidas las solicitudes que seguían en curso al cerrar la ventana.
Se usaron datos sintéticos, ENFEN en modo demo y plantillas del agente. Las simulaciones de tamaño Rápido usaron 150 créditos × 80 escenarios, alternando Base y Año El Niño con tres semillas consecutivas desde 2026.

| Endpoint | Intentos | Mezcla real | p50 (ms) | p95 (ms) | Error | Detalle |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `POST /motor/propuesta` | 2296 | 50.0% | 245.3 | 631.3 | 0.00% | — |
| `GET /cliente/prestamos/{id}` | 918 | 20.0% | 33.2 | 102.3 | 0.00% | — |
| `POST /agente/sesion/{id}/mensaje` | 918 | 20.0% | 147.0 | 514.0 | 0.00% | — |
| `POST /simulacion/correr` | 459 | 10.0% | 35.8 | 206.2 | 0.00% | — |

La API tuvo 116.5 MiB de RSS al iniciar la carga y un máximo de 180.3 MiB. El árbol completo, incluidos los trabajadores de simulación, alcanzó 1141.1 MiB en 117 muestras.
En simulación hubo 6 respuestas calculadas y 453 servidas desde caché.

## Método e interpretación

- La mezcla programada es 50 % propuestas, 20 % vistas, 20 % chat y 10 % simulaciones. Cada usuario inicia su siguiente petición al terminar la anterior.
- Los percentiles usan rango más cercano sobre respuestas exitosas. La latencia incluye HTTP y lectura del cuerpo. Los fallos HTTP, de transporte y de lectura cuentan en el porcentaje de error.
- Se excluye la preparación de la cartera sintética, el préstamo activo y una sesión por usuario. El tiempo límite por fase HTTP es de 45 s.
- La RSS se muestrea aproximadamente una vez por segundo. La suma del árbol puede contar páginas compartidas en más de un proceso.

Las rutas distintas de simulación quedaron por debajo de 3 s en p95.

## Reproducir

```bash
python scripts/carga.py
```
