# CuotaFlex · Fase 4 · Lote C — para Stefano

Hola Stefano. Aquí está tu parte de la **fase 4: ajustar CuotaFlex a las preguntas frecuentes del NEG-01**, publicadas por la organización el 24 de noviembre en la plataforma (Desafíos → NEG-01 → Preguntas frecuentes). **Léelas primero, son 5 minutos.**

## Por qué hay una fase 4
Las FAQ dejan claro qué se evalúa:
- una herramienta del **Asesor de Negocios** que **estima el ciclo económico** del cliente (patrón de sector y zona con fuentes públicas, ajustado con la captura del asesor, **sin historial de pagos**);
- que en el mismo lugar **construye un plan nuevo** con cuotas y periodos variables, con **Cuota/UN ≤ factor en cada etapa**, TED base 360, seguros, prelación seguros → interés → capital, pendientes sin capitalizar y TCEA;
- una **vista para el Asesor de Riesgos y el comité**;
- la **comparación con la cuota fija en escenarios adversos**.

**No se medirá la mora de una cartera real.** Solo cuentan créditos nuevos, con el plan fijo desde el desembolso.

## Cómo trabajamos en esta fase
- **Contratos:** `docs/fases/fase-4/CONTRATOS.md` define qué recibe y qué devuelve cada pieza. Hay JSON de ejemplo en `tests/fixtures/contratos/` (caso Rosa) para no depender de los demás.
- **Plazo:** terminar antes del **30 de noviembre**, para integrar y ensayar el 1 y 2 de diciembre. La final es el **3 y 4 de diciembre**.

## Antes de empezar
```bash
git checkout main && git pull
pip install -r requirements.txt -r requirements-dev.txt
pytest                                    # deben pasar todas
git checkout -b fase-4/lote-c-comite
```
Al terminar: haz `git push -u origin fase-4/lote-c-comite` y **abre el Pull Request** a `main`.

---

## Fase 4 · Lote C — Flujo del asesor y vista para el Asesor de Riesgos y el comité

**Rama:** `fase-4/lote-c-comite`

## Objetivo
Las FAQ dicen qué se espera ver: una herramienta donde el **Asesor de Negocios estima el ciclo y, en el
mismo lugar, propone el plan** a partir del monto, la TEA, los seguros y el plazo. Para el comité se
espera **el ciclo en gráfico, las cuotas, Cuota/UN por etapa, los supuestos** y la comparación con la
cuota fija en escenarios adversos. El **Asesor de Riesgos valida** y el **comité aprueba**.

## Archivos (exclusivos)
- `web/asesor/src/pages/NuevaSolicitud.tsx`, `web/asesor/src/pages/Comite.tsx` y `web/asesor/src/components/plan/**` (nuevos)
- `web/asesor/src/contratos.ts` (tipos del contrato) y `web/asesor/src/mocks/**` (copia de los JSON de `tests/fixtures/contratos/`)
- `web/asesor/src/App.tsx`: solo las rutas nuevas y un enlace "Nueva solicitud"
- `web/asesor/src/pages/Bandeja.tsx`: solo el botón "Nueva solicitud"
- `tests/e2e/test_fase4_c.py` (nuevo)

**No toques** `components/ChatAgente.tsx` (lote D), `sesion.tsx` ni `api.ts`. Si necesitas llamadas nuevas, ponlas en `src/apiPlan.ts`.

**Contrato:** `docs/fases/fase-4/CONTRATOS.md`. Trabaja con **mocks** (`VITE_MOCK=1` usa los JSON de `src/mocks/`) hasta que A y B estén listos. Así no dependes de ellos.

## Tareas
1. **Nueva solicitud** (`/nueva`), un asistente de 3 pasos:
   1. **Negocio:** sector, actividad y zona (con `GET /ciclo/catalogo`; en mock, una lista fija) y la captura del asesor (ventas en meses alto, normal y bajo, qué meses, costos %, gastos operativos y tributarios, carga familiar, otras deudas y evidencias opcionales). Con validaciones y ayudas en lenguaje de campo.
   2. **Ciclo estimado:** gráfico de 12 a 24 meses con la UN p50, una banda p10–p90 y colores por etapa (cima, normal y valle). Los supuestos y las fuentes se pueden desplegar. Botón "Ajustar meses" para volver al paso 1.
   3. **Crédito y plan:**
      - **Datos:** monto, **TEA editable** (avisa si supera el tope), plazo, producto (factor 0.65 o 0.85, editable a la baja) y seguros (desgravamen y multirriesgo con valor asegurable). Al cambiarlos se llama a `POST /plan/proponer`.
      - **Gráfico:** cuotas del plan adaptado frente a la cuota fija, sobre la línea factor × UN.
      - **Tabla por periodo:** cuota, seguros, interés, capital, pendientes, saldo, **Cuota/UN con semáforo** y tipo (gracia o solo interés).
      - **Resumen comparado:** total pagado, interés, seguros, TCEA, meses de gracia y etapas sobre el factor.
      - Si no es factible, muestra los `ajustes_sugeridos` con un botón para aplicar cada uno.
2. **Vista para el comité** (`/comite/:id`): una página limpia, **imprimible y exportable a PDF** con CSS de impresión, que incluye:
   - el encabezado de la solicitud;
   - el gráfico del ciclo;
   - el plan con Cuota/UN por etapa;
   - el máximo Cuota/UN frente al factor;
   - la tabla de **estrés** (fija contra adaptado por escenario);
   - los supuestos y las fuentes;
   - la explicación del agente (si el lote D expone `GET /agente/explicacion-comite`; si no, un espacio reservado).

   Además, un bloque de **validación del Asesor de Riesgos**: aprobar, observar con comentario o rechazar. Se guarda en `localStorage` dentro de try/catch y queda impreso con la fecha. Es una maqueta del flujo, sin datos reales.
3. **Mantener lo existente:** la bandeja y la ficha actual siguen funcionando. Los aplazamientos durante la vida del crédito y el alivio de El Niño en vivo **se ocultan en la app del asesor** con un aviso "fuera del alcance del reto (créditos vigentes = reprogramación)". No borres código.
4. **Calidad:** funciona en 1366×768, la impresión cabe en A4 vertical en 2 o 3 páginas, no hay errores de consola y `npm run build` pasa.

## Pruebas (e2e, en modo mock)
- La nueva solicitud completa los 3 pasos con el caso Rosa y muestra 0 etapas sobre el factor en el adaptado y más de 0 en la fija.
- Un caso no factible muestra los ajustes, y al aplicar uno se vuelve factible (mock con dos respuestas).
- La vista del comité muestra el ciclo, el plan, el estrés y los supuestos, y `window.print` no rompe la página.

## Criterios de aceptación
- [ ] Flujo de 3 pasos y vista del comité funcionando en mock y luego contra la API real en la integración.
- [ ] PDF del comité exportado de los 3 casos estrella en `docs/demo/comite/`.
- [ ] Capturas en `web/asesor/README.md`.

---

## Reglas para trabajar en paralelo

1. **Rama por lote:** `fase-4/lote-a-plan`, `fase-4/lote-b-ciclo`, `fase-4/lote-c-comite`, `fase-4/lote-d-pitch-agente`.
2. **Archivos exclusivos:** cada lote solo crea o modifica los archivos que su `.md` marca como suyos. Si necesitas tocar otro archivo, avísalo al equipo antes.
3. **Contratos primero:** todo lo que se pasa entre lotes sigue `docs/fases/fase-4/CONTRATOS.md`. Mientras otro lote no esté listo, se trabaja con los JSON de `tests/fixtures/contratos/`.
4. **Endpoints nuevos:** van en un archivo propio dentro de `src/cuotaflex/api/routers/`, con una variable `router`. La API lo registra sola, sin tocar `main.py`.
5. **Frontends:** cada uno vive en su carpeta dentro de `web/` con su propio `package.json`. Puertos fijos: asesor 5173, cliente 5174, tablero 5175. El CORS ya los permite.
6. **Dependencias de Python nuevas:** se agregan en `requirements-<lote>.txt`, no en `requirements.txt`. Se consolidan al cerrar la fase.
7. **Pruebas:** cada lote agrega `tests/test_<lote>.py`, y `pytest` debe pasar antes del PR.
8. **Datos:** solo sintéticos. Nunca datos reales de clientes.
9. **Commits:** a nombre de cada integrante, sin coautores automáticos.


10. **Commits desde tu propia cuenta de GitHub**, para la declaración de propiedad intelectual.
