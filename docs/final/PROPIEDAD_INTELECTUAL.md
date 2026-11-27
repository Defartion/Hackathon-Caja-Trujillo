# Declaración de propiedad intelectual

> **Borrador para revisión del equipo.** Andre (lote D) usa este texto en el pitch y en la respuesta a
> "¿Qué parte construyeron antes y qué parte en el evento?". Las bases piden que el motor y el módulo se
> desarrollen durante la final; lo que se construya pasa a la Caja si el equipo gana.

## 1. En una frase (para el pitch)

Antes de la final construimos el motor de Thinku, sus integraciones (Fineract y ENFEN), el agente y las
tres apps, siempre con datos sintéticos. **En la final construimos un módulo nuevo: pago por ventas y pago a
cosecha.** Todo usa librerías de código abierto con licencias permisivas.

## 2. Lo que existía antes del evento

Fuente: historial de `main` en GitHub. Cada commit está hecho desde la cuenta de su autor.

| Fase | Fechas | Qué se construyó | Commits | Cuentas de GitHub |
|---|---|---|---|---|
| 0 · Base | 22 nov 2026 | Motor (datos sintéticos, pronóstico, políticas, optimizador MILP y agente), simulación Monte Carlo, API compatible con Fineract y concepto preliminar | `9587c24` | Sebastian Pelaez |
| 1 · Demo y concepto | 22–23 nov 2026 | App del asesor, app del cliente, tablero de simulación y Concept Solution | `90ec9fb` … `fe826cd` (14 commits) | Sebastian Pelaez, stefanods29, JDiazD33, ARamirezA |
| 2 · Calidad e integración real | 23–24 nov 2026 | Calibración con la SBS, selección por simulación, espejo en Apache Fineract, disparador ENFEN con notificaciones y agente con herramientas y salvaguardas | `60b08e9` … `e321845` (13 commits) | Sebastian Pelaez, stefanods29, JDiazD33 |
| 3 · Preparación de la final | 24 nov – 1 dic 2026 | Persistencia y despliegue, QA y casos estrella, plan de la final (este lote) y pitch | desde `cf6d9de` (se completa al integrar la fase 3) | Todo el equipo |

El equipo confirma a qué integrante corresponde cada cuenta: Sebastian, Joaquin, Stefano y Andre.

**Corte verificable:** al cerrar la fase 3 (2 de diciembre) se crea en `main` la etiqueta `antes-de-la-final`.
Todo commit posterior a esa etiqueta se hizo durante el evento.

## 3. Lo que se construirá durante el evento (3 y 4 de diciembre)

| Pieza | Detalle | Dónde quedará |
|---|---|---|
| **Módulo "pago por ventas" y "pago a cosecha"** | Regla de pago en la simulación, dos modalidades candidatas en la selección por simulación, políticas, API y pantallas | Motor, `routers/pago_ventas.py`, apps del asesor y del cliente, tablero, `tests/test_modulo_en_vivo.py` |
| Recalibración | Con los datos o parámetros que entregue la Caja, si los entrega | `config/parametros.yaml` y `resultados/` |
| Ajustes de demo y pitch | Textos y datos, nunca código en las 3 horas previas | `docs/pitch/` y datos de demo |

Antes del evento solo existe el **diseño** del módulo (`docs/final/MODULO_EN_VIVO.md`), sin una línea de su
código. Durante la final se trabaja en ramas `final/*` con commits desde la cuenta de cada integrante.

## 4. Datos

- **Clientes:** 100% sintéticos (`src/cuotaflex/datos.py`). Nunca se usaron datos reales de clientes.
- **Fuentes públicas:**
  - Comunicados oficiales del ENFEN (gob.pe/SENAMHI y enfen.imarpe.gob.pe). Las pruebas incluyen la página 1 de
    8 comunicados, con su origen en `tests/fixtures/enfen/README.md`.
  - Cifras de mora de la SBS, usadas como referencia para calibrar la cartera sintética.
- **Datos de la Caja en el evento:** se usan solo como indiquen las bases y no se suben a repositorios públicos.

## 5. Software de terceros y licencias

Revisión del 24 nov 2026 sobre las versiones instaladas: **no hay licencias GPL ni AGPL** entre las 70
distribuciones de Python ni entre los 116 paquetes de npm de las tres apps.

### Python (`requirements.txt`)

| Paquete | Versión probada | Licencia | Uso |
|---|---|---|---|
| numpy | 2.5.5 | BSD-3-Clause (incluye partes 0BSD, MIT, Zlib y CC0-1.0) | Cálculo numérico |
| pandas | 2.3.3 | BSD-3-Clause | Tablas de datos |
| scipy | 1.18.1 | BSD-3-Clause | Estadística |
| pyyaml | 6.0.4 | MIT | Parámetros |
| cvxpy | 1.9.3 | Apache-2.0 | Modelo de optimización del cronograma |
| highspy (HiGHS) | 1.16.0 | MIT | Solver MILP |
| statsforecast | 2.1.1 | Apache-2.0 | Pronóstico |
| fastapi | 0.165.0 | MIT | API |
| uvicorn | 0.54.0 | BSD-3-Clause | Servidor de la API |
| httpx | 0.28.1 | BSD-3-Clause | Cliente HTTP (ENFEN, pruebas) |
| pytest | 9.2.0 | MIT | Pruebas |
| pypdf | 7.1.1 | BSD-3-Clause | Lectura de los comunicados del ENFEN |
| matplotlib | 3.11.2 | Licencia de matplotlib (basada en la PSF, compatible con BSD) | Figuras del concepto |

**Opcionales, no instalados por defecto:**
- `anthropic`: SDK del proveedor de IA. El servicio es de pago y está sujeto a sus términos; sin clave, el agente usa plantillas.
- `chronos-forecasting`: pronóstico alternativo.
- `sdv`: **Business Source License 1.1**, que no es una licencia de código abierto. Según su ficha en PyPI,
  es gratuita solo para uso no comercial. No debe usarse en lo que pase a la Caja sin revisar esa licencia.

### JavaScript (`web/*/package.json`)

| Paquete | Apps | Licencia |
|---|---|---|
| react y react-dom 18.3.1 | asesor, cliente, tablero | MIT |
| react-router-dom 6.30.6 | asesor | MIT |
| recharts 2.15.4 | asesor, tablero | MIT |
| lucide-react 1.78.0 | cliente | ISC |
| vite 5.4.21 / 6.4.6 | asesor y tablero / cliente | MIT |
| @vitejs/plugin-react 4.7.0 | las tres | MIT |
| typescript 5.6.3 | las tres | Apache-2.0 |
| @types/react y @types/react-dom | las tres | MIT |

### Dependencias transitivas que conviene conocer

| Paquete | Licencia | Nota |
|---|---|---|
| certifi, tqdm (Python) | MPL-2.0 (tqdm, además MIT) | Copyleft débil, por archivo: solo obliga si se modifican sus propios archivos. Se usan sin cambios |
| caniuse-lite (npm) | CC-BY-4.0 | Datos de compatibilidad de navegadores que se usan al compilar; no va en el producto |

### Infraestructura y servicios

| Componente | Licencia | Uso |
|---|---|---|
| Apache Fineract 1.12.1 | Apache-2.0 | Core bancario de demo, en Docker (`infra/fineract/`), opcional |
| PostgreSQL 16 | PostgreSQL License | Base de datos de Fineract, en Docker, opcional |
| Proveedores de IA (Anthropic u OpenAI) | Términos de cada servicio | Opcionales; el agente funciona sin ellos |

Para entregar el código a la Caja hay que conservar los avisos de licencia de estas librerías. Ninguna impide
el uso comercial (salvo SDV, que no se usa).

## 6. Herramientas de IA usadas para desarrollar (por confirmar)

La organización pidió confirmar qué herramientas de IA están permitidas (pendiente en `NOTAS.md`). Cada
integrante completa su fila:

| Integrante | Herramienta | Para qué |
|---|---|---|
| Stefano | Claude Code (asistente de programación) | Lote C de las fases 2 y 3: código, pruebas y documentos, revisados por Stefano. *Confirmar antes de publicar* |
| Sebastian | _completar_ | |
| Joaquin | _completar_ | |
| Andre | _completar_ | |

El producto, además, **usa** IA generativa de forma opcional (el agente del asesor, con verificación de cifras
y respaldo con plantillas). Esto se declara en el concepto y en el pitch.

## 7. Revisión del equipo

- [ ] Sebastian
- [ ] Joaquin
- [ ] Stefano
- [ ] Andre (texto del pitch alineado con esta declaración)
