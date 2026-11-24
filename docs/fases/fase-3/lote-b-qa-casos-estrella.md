# Fase 3 · Lote B — QA de punta a punta, casos estrella y modo sin conexión

**Rama:** `fase-3/lote-b-qa`

## Objetivo
Que la demo **no falle frente al jurado**:
- pruebas automáticas que recorren las tres apps como lo haría una persona;
- tres "casos estrella" preparados que cuentan la historia del producto;
- un modo sin conexión por si la red del evento falla;
- Fineract funcionando también en Windows.

## Archivos de este lote (exclusivos)
- `tests/e2e/**` (nuevo): pruebas con Playwright para Python
- `src/cuotaflex/api/routers/asesor.py`: **solo la función `cartera_demo`** y funciones auxiliares nuevas en ese archivo
- `src/cuotaflex/demo/casos_estrella.py` (nuevo)
- `scripts/carga.py`, `scripts/demo_offline.sh` y `.ps1` (nuevos)
- `infra/fineract/up.ps1` y `infra/fineract/README.md` (para la parte de Windows)
- `docs/demo/**` (nuevo)
- `tests/test_fase3_b.py` (nuevo)

**No toques:** `api/main.py`, `web/*/src/App.tsx` ni `web/*/src/api.ts` (son del lote A).

## Tareas

### 1. Tres casos estrella (`demo/casos_estrella.py`)
Son clientes sintéticos con parámetros fijos (no aleatorios), pensados para contar la historia en 5 minutos:

| ID | Caso | Lo que debe mostrar la demo |
|---|---|---|
| `E001` | **Rosa, agricultora de arroz en Chepén** | La selección por simulación elige la cuota **estacional**: cuotas altas en cosecha y bajas en siembra. El default baja claramente frente a la fija. Incluye la cláusula El Niño |
| `E002` | **Martín, pescador artesanal en Pacasmayo** | Con la alerta del ENFEN activa, la app del cliente muestra el banner y el alivio reduce su cuota. El tablero muestra la cartera cubierta |
| `E003` | **Luis, bodeguero en Trujillo con otras deudas** | El agente **reduce el monto** para no sobreendeudar y lo explica en la bitácora y en el chat ("¿por qué bajó el monto?") |

- Ajusta los parámetros de cada caso (ventas, margen, gasto, otras cuotas y meses) hasta que el motor **realmente** produzca ese resultado. Fíjalo con pruebas.
- `cartera_demo` devuelve los 3 casos estrella **al inicio** de la lista (con su `historial_ventas` e `indice_estacionalidad`), seguidos de la cartera sintética de siempre. Mantén el formato exacto y que `n` cuente solo la cartera sintética, para no romper las pruebas existentes.
- `docs/demo/CASOS_ESTRELLA.md`: guion de cada caso, con qué pantallas abrir, qué decir y qué cifra señalar. Agrega capturas.

### 2. Pruebas de punta a punta (`tests/e2e/`)
- Playwright para Python. Un `conftest.py` que levanta la API (uvicorn en un puerto libre) y sirve las tres apps compiladas (`vite preview`), y las apaga al terminar.
- Márcalas con `@pytest.mark.e2e` y deja que se salten si no está instalado Chromium, para que `pytest` normal siga rápido.
- Flujos mínimos:
  1. **Asesor:** abre E001 → ve la bitácora con "Selección por simulación" → pregunta al chat "¿y a 24 meses?" → la respuesta trae "cifras verificadas" → registra, aprueba y desembolsa.
  2. **Cliente:** abre el préstamo del paso 1 (`?loanId=`) → ve la próxima cuota → pide la vista previa de un aplazamiento si aplica, o revisa el cronograma.
  3. **ENFEN:** activa la alerta en modo demo → el banner aparece en la app del cliente y el distintivo en el tablero → usa el alivio en E002.
  4. **Tablero:** escenario "Base" en tamaño Rápido → aparecen los 4 indicadores → el escenario "Año El Niño" cambia las cifras.
  5. **Errores:** con la API apagada, cada app muestra un mensaje legible y no una pantalla en blanco.
- Ninguna prueba debe dejar errores en la consola del navegador: haz que falle si aparece alguno.
- Guarda capturas de cada paso en `docs/demo/capturas/` con un script (`--capturas`).

### 3. Carga ligera (`scripts/carga.py`)
- 10 usuarios simultáneos durante 2 minutos (con `asyncio` y `httpx`), con esta mezcla:
  - 50% propuestas;
  - 20% vistas del cliente;
  - 20% mensajes al chat;
  - 10% simulaciones en tamaño Rápido.
- Reporta p50, p95, el error % por endpoint y la memoria de la API. El resultado va en `docs/demo/CARGA.md`.
- Si algo supera 3 s en p95 (fuera de la simulación), documenta la causa y una solución propuesta. No toques el motor.

### 4. Modo sin conexión (`scripts/demo_offline.sh` y `.ps1`)
- Levanta todo **sin internet**: API local con `ENFEN_MODO=demo`, core simulado, agente sin proveedor de IA y las tres apps compiladas.
- Verifica que ninguna pantalla intente cargar recursos externos (fuentes o CDN). Si encuentras alguno, anótalo en `docs/demo/OFFLINE.md` para que lo corrija el dueño de esa app.
- Prueba real: corta el wifi y recorre los tres casos estrella.

### 5. Fineract en Windows
- Prueba `infra/fineract/up.ps1` en Windows con Docker Desktop. Si no funciona bien, documenta el camino con WSL2 paso a paso en `infra/fineract/README.md`.
- Mide el tiempo de arranque y la memoria en la laptop que se llevará a la final.

## Pruebas (`tests/test_fase3_b.py`, sin navegador)
- Los tres casos estrella producen su resultado: E001 estacional con menos default que la fija; E002 con cláusula El Niño; E003 con monto aprobado menor que el solicitado.
- `cartera-demo` empieza con E001, E002 y E003 y mantiene el resto de la lista y su formato.
- **Las pruebas existentes siguen pasando.**

## Criterios de aceptación
- [ ] Los 3 casos estrella son reproducibles y tienen guion con capturas.
- [ ] Los 5 flujos de punta a punta pasan localmente, sin errores de consola.
- [ ] Reporte de carga con p50 y p95.
- [ ] La demo completa funciona sin internet.
- [ ] Fineract probado en Windows, o el camino con WSL documentado.
