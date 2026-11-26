# Fase 4 · Lote C — Flujo del asesor y vista para el Asesor de Riesgos y el comité

> **Actualización (25 nov):** el Asesor ya tiene un menú lateral (`web/asesor/src/Lateral.tsx`). "Nueva solicitud" y
> "Comité de créditos" ya aparecen en el menú marcados como *pronto*. Para activarlas: agrega tus rutas `/nueva` y
> `/comite` en `App.tsx` y quita `pronto: true` de esas dos opciones en `OPCIONES_ASESOR` (`Lateral.tsx`). Ya no hace
> falta el botón "Nueva solicitud" en `Bandeja.tsx` ni un enlace en la cabecera: el menú los reemplaza.

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
