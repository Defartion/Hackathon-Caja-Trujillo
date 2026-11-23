# Fase 2 · Lote C — Disparador ENFEN y notificaciones

**Rama:** `fase-2/lote-c-enfen`

## Objetivo
Que la cláusula El Niño se active con la **fuente oficial** y no con un interruptor manual, y que el
cliente reciba avisos útiles. Es muy relevante para el pitch: el ENFEN mantiene la **"Alerta de El Niño
Costero"** en 2026 (comunicados oficiales 1 a 15 de 2026), así que la solución responde a un riesgo real
y presente en la región.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/integraciones/enfen.py` (nuevo). Si `integraciones/__init__.py` no existe en tu rama, créalo vacío; el lote B también lo crea y en la integración se resuelve en un segundo.
- `src/cuotaflex/notificaciones/**` (nuevo)
- `src/cuotaflex/api/routers/alertas.py` (nuevo)
- `src/cuotaflex/api/routers/cliente.py`: **solo la función `estado_el_nino()`**
- `web/tablero/src/components/EstadoEnfen.tsx` (nuevo) y una línea en `web/tablero/src/App.tsx` para mostrarlo
- `tests/test_fase2_c.py` y `tests/fixtures/enfen/**` (nuevos)

## Fuentes oficiales
- El SENAMHI publica todos los comunicados oficiales del ENFEN en gob.pe ("Comunicados oficiales del ENFEN"), en PDF.
- También están en `enfen.imarpe.gob.pe` (sección de descargas) y en el SINIA del MINAM.
- Cada comunicado trae en la primera página: **número, fecha y "Estado del sistema de alerta: …"**. Los estados posibles son "No Activo", "Vigilancia de El Niño Costero", "Alerta de El Niño Costero" y sus equivalentes para La Niña.

Verifica las URLs vigentes tú mismo y anótalas en el README. No dependas de una sola fuente.

## Tareas

### 1. Lector del ENFEN (`integraciones/enfen.py`)
- `obtener_ultimo_comunicado() -> Comunicado`, con `numero`, `fecha`, `estado` (enum: NO_ACTIVO, VIGILANCIA_NINO, ALERTA_NINO, VIGILANCIA_NINA, ALERTA_NINA), `magnitud` (si aparece: débil, moderada, fuerte o extraordinaria), `url_fuente` y `obtenido_en`.
- Estrategia en este orden:
  1. Página de la colección de comunicados.
  2. Descarga del PDF más reciente.
  3. Extracción de texto con `pypdf`.
  4. Expresión regular sobre "Estado del sistema de alerta: …".
- **Parser robusto:** sin importar tildes ni mayúsculas, tolerante a saltos de línea dentro de la frase. Pruébalo con al menos 4 PDFs reales guardados en `tests/fixtures/enfen/`, uno por estado distinto si los encuentras (los de 2025 y 2026 cubren "No Activo", "Vigilancia" y "Alerta").
- **Caché** en disco (`data/enfen_cache.json`) con 6 h de validez y **respaldo**: si la red falla, usa el último valor en caché y márcalo `desactualizado: true`.
- **Modo demo:** `ENFEN_MODO=oficial|demo`. En demo, el estado lo fija `POST /alertas/enfen/demo`, para poder mostrar el cambio en vivo.

### 2. Conectar con la app del cliente
- Reescribe **solo** `estado_el_nino()` en `routers/cliente.py` para que use `enfen.estado_actual()`. Mantén exactamente el mismo formato de salida que usa hoy la app del cliente (revisa las pruebas del lote B de la fase 1). Agrega campos nuevos solo si no rompen nada.
- `activo` es verdadero solo con ALERTA_NINO. VIGILANCIA_NINO se muestra como aviso preventivo, sin alivio.

### 3. Motor de alertas (`routers/alertas.py`, prefijo `/alertas`)
- `GET /alertas/enfen`: el estado actual, con fuente, fecha y si está desactualizado.
- `POST /alertas/enfen/revisar`: fuerza una lectura. Si el estado **cambió**, genera los eventos y las notificaciones.
- `GET /alertas/impacto`: préstamos con cláusula El Niño en rubros expuestos, con número, saldo y cuotas de alivio disponibles por rubro y región, a partir de `api.main.DB`.
- **Tarea programada:** al iniciar la API, un hilo en segundo plano revisa cada 6 h, activable con `ENFEN_REVISION_AUTOMATICA=1` y apagado en las pruebas.

### 4. Notificaciones (`notificaciones/`)
- `Outbox` en memoria (y en `data/outbox.jsonl`), con canal (sms o whatsapp), destinatario (loanId), plantilla, texto, fecha y estado (pendiente o enviado-simulado).
- **No envíes mensajes reales.** Todo es simulado.
- Plantillas en español sencillo, de 160 caracteres o menos para SMS:
  - **Recordatorio de cuota:** 3 días antes, con monto y fecha.
  - **Aviso de temporada baja:** cuando la próxima cuota es "baja", con un mensaje positivo.
  - **Alerta El Niño activa:** "puedes usar tu alivio", con instrucciones.
  - **Vigilancia El Niño:** un aviso preventivo sin alivio.
  - **Aplazamiento confirmado:** con el nuevo monto y el costo adicional.
- `GET /alertas/notificaciones?loanId=` y `POST /alertas/notificaciones/generar-recordatorios`.

### 5. Indicador en el tablero
`EstadoEnfen.tsx`: un distintivo en la cabecera del tablero con el estado oficial ("Alerta de El Niño Costero · Comunicado N° X, fecha"), con color por estado y enlace a la fuente. Al hacer clic, muestra el impacto en la cartera (`/alertas/impacto`).

## Pruebas (`tests/test_fase2_c.py`)
- El parser extrae el estado correcto de cada PDF guardado.
- Sin red (mock), se usa la caché y se marca como desactualizada.
- Un cambio a ALERTA_NINO genera notificaciones solo para los préstamos con cláusula.
- `estado_el_nino()` conserva su formato y **las pruebas del lote B de la fase 1 siguen pasando**.
- Ninguna plantilla de SMS pasa de 160 caracteres.
- **Ninguna prueba descarga de internet:** todo con fixtures.

## Criterios de aceptación
- [ ] Con `ENFEN_MODO=oficial`, la API muestra el estado del último comunicado real, con su número y fecha.
- [ ] Con `ENFEN_MODO=demo`, se puede cambiar el estado en vivo y la app del cliente muestra el banner.
- [ ] El outbox muestra las notificaciones generadas por el cambio de estado.
- [ ] El tablero muestra el distintivo del ENFEN y el impacto en la cartera.
- [ ] `pytest` pasa completo.
