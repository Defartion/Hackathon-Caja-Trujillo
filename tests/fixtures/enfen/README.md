# Fixtures del ENFEN (fase 2 · lote C)

Comunicados y páginas **reales y públicos** del ENFEN, descargados el 23 nov 2026. Las pruebas
(`tests/test_fase2_c.py`) los usan para no salir a internet.

De cada PDF se guardó **solo la página 1**, que es donde está el estado del sistema de alerta, para no
inflar el repositorio (2,5 MB en total). El texto que extrae pypdf es idéntico al de la página 1 original.

| Archivo | Comunicado | Fecha | Estado | Por qué está |
|---|---|---|---|---|
| `comunicado-20-2026.pdf` | Oficial N° 20-2026 | 13 nov 2026 | Alerta de El Niño Costero | El vigente. Formato nuevo: línea suelta "Alerta de El Niño Costero¹", sin "Estado del sistema de alerta:". Magnitud extraordinaria |
| `comunicado-17-2026.pdf` | Oficial N° 17-2026 | 28 set 2026 | Alerta de El Niño Costero | Primer comunicado con el formato nuevo. **Errata**: el PDF dice "28 septiembre 2027" |
| `comunicado-03-2026.pdf` | Oficial N° 03-2026 | 13 feb 2026 | Alerta de El Niño Costero | Activación de la alerta, magnitud débil |
| `comunicado-01-2026.pdf` | Oficial N° 01-2026 | 15 ene 2026 | Vigilancia de El Niño Costero | Cambio desde "No Activo" |
| `comunicado-13-2025.pdf` | Oficial N° 13-2025 | 18 dic 2025 | No Activo | "No Activo¹" con la llamada a nota pegada |
| `comunicado-extraordinario-01-2025.pdf` | **Extraordinario** N° 01-2025 | 28 feb 2025 | Vigilancia de El Niño Costero | Serie distinta de la oficial; gob.pe lo lista el 27 feb |
| `comunicado-09-2024.pdf` | Oficial N° 09-2024 | 14 jun 2024 | Vigilancia de La Niña Costera | Estado de La Niña |
| `comunicado-11-2022.pdf` | Oficial N° 11-2022 | 14 nov 2022 | Alerta de La Niña Costera | Estado en MAYÚSCULAS |
| `gobpe-coleccion.html` | Colección "Comunicados oficiales del ENFEN" (hoja 1) | 23 nov 2026 | — | Listado de la fuente principal |
| `gobpe-ficha-20-2026.html` | Ficha del N° 20-2026 en gob.pe | 23 nov 2026 | — | Enlace al PDF |
| `imarpe-comunicados.html` | enfen.imarpe.gob.pe/comunicados | 23 nov 2026 | — | Recuadro "Último comunicado" con la descarga directa |

## Origen

- Colección de gob.pe (SENAMHI): <https://www.gob.pe/institucion/senamhi/colecciones/1308-comunicados-enfen>
- Ficha del N° 20-2026: <https://www.gob.pe/institucion/senamhi/informes-publicaciones/8827660-comunicado-oficial-enfen-n-20-2026>
- Comunicados de IMARPE: <https://enfen.imarpe.gob.pe/comunicados/>
- PDF (todos en `cdn.www.gob.pe/uploads/document/file/`):
  - N° 20-2026: `10965414/8827660-comunicado-oficial-enfen-n-20-2026.pdf`
  - N° 17-2026: `10703704/8654940-comunicado_of_enfen-n-17-2026.pdf`
  - N° 03-2026: `9449581/7739096-comunicado_of_enfen-n-03-2026.pdf`
  - N° 01-2026: `9296731/7624862-comunicado_of_enfen-n-01-2026-15-01-2026%282%29.pdf`
  - N° 13-2025: `9174628/7532712-comunicado_of_enfen-n-13-2025.pdf`
  - Extraordinario N° 01-2025: `7708213/6523595-comunicado-extraordinario-enfen-n01-2025.pdf`
  - N° 09-2024: `6483942/5661164-comunicado_of_enfen-n-09-2024.pdf`
  - N° 11-2022: `3836780/Comunicado_Of_ENFEN%20N%C2%B0%2011-2022.pdf.pdf`

El parser también se probó, fuera de las pruebas automáticas, con los 39 comunicados de 2022 a 2026 que
publica gob.pe (los 33 de 2025-2026 y seis de 2022-2024): reconoció el número, la fecha y el estado de todos.
