# Fase 3 · Lote A — Persistencia, roles y despliegue

**Rama:** `fase-3/lote-a-despliegue`

## Objetivo
Llegar a la final con una demo **estable, desplegada y reiniciable**: los datos no se pierden al
reiniciar la API, cada rol entra a su app, las cuatro piezas (API más tres apps) se levantan con un solo
comando y hay una URL pública por app. Esto pesa en "funcionamiento y demo", que vale 35% en la final.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/api/main.py` (solo lo indicado abajo) y `src/cuotaflex/persistencia.py` (nuevo)
- `src/cuotaflex/api/routers/auth.py` y `src/cuotaflex/api/routers/espejo_automatico.py` (nuevos)
- `web/*/src/App.tsx`, `web/*/src/api.ts`, `web/*/src/components/Login.tsx` (nuevo) y `web/*/Dockerfile` (nuevo)
- `Dockerfile`, `docker-compose.yml`, `.env.example`, `deploy/**` y `scripts/reset_demo.(sh|ps1)` (nuevos)
- `tests/test_fase3_a.py` (nuevo)

**No toques:** `routers/asesor.py` (el lote B agrega ahí los casos estrella), `tests/e2e/**` ni `docs/**` fuera de `deploy/`.

## Regla de compatibilidad
Los routers usan `api.DB["clients"]` y `api.DB["loans"]` como dicts, y modifican los préstamos
directamente (`l["cuotas"][j] = ...`). **No cambies esa interfaz.** La persistencia va "por debajo".

## Tareas

### 1. Persistencia por instantánea (`persistencia.py`)
- SQLite en `data/cuotaflex.db` (ruta configurable con `CUOTAFLEX_DB`). Una tabla `entidades(tipo, id, json, actualizado)` y otra `meta(clave, valor)` para el contador de IDs.
- `cargar(DB)` al iniciar la API: llena `DB` y deja `_ids` en el máximo ID más uno.
- `guardar(DB)`: escribe todo en una transacción. Con decenas de préstamos es instantáneo.
- **Middleware** en `main.py`: después de cada `POST`, `PUT`, `PATCH` o `DELETE` con respuesta 2xx, llama a `guardar(DB)` bajo un candado.
- `CUOTAFLEX_PERSISTENCIA=0` la desactiva. **Debe quedar desactivada por defecto en las pruebas** (en `tests/conftest.py`, solo si no rompe nada; si no, en tu propio archivo de pruebas con monkeypatch).
- `POST /admin/reset` (solo rol supervisor): vacía `DB` y la base de datos, y opcionalmente vuelve a sembrar los casos de demo llamando a `/cliente/demo-seed`.

### 2. Roles simples (`routers/auth.py`)
- Roles: `asesor`, `cliente` y `supervisor`, con PIN de demo configurable por entorno (`PIN_ASESOR`, `PIN_CLIENTE`, `PIN_SUPERVISOR`).
- `POST /auth/login` con `{rol, pin}` devuelve un token firmado (HMAC con `CUOTAFLEX_SECRETO`) que dura 12 h.
- Dependencia `requiere_rol(...)`. **Solo actúa si `CUOTAFLEX_AUTH=1`**. Por defecto está apagada, para que las pruebas y los demás lotes no se rompan.
- Con la autenticación encendida:
  - las rutas de escritura de `/fineract-provider/**` y `/motor/**` requieren asesor o supervisor;
  - `/cliente/**` requiere cliente o asesor;
  - `/simulacion/**`, `/alertas/**` y `/admin/**` requieren supervisor.
  - Aplícalo con un middleware por prefijo en `main.py`, sin editar los otros routers.
- **Frontends:** una pantalla `Login.tsx` en cada app que solo aparece si `GET /auth/config` dice `{"auth": true}`. El token va en `sessionStorage` (dentro de try/catch) y se envía en `Authorization: Bearer` desde `api.ts`.

### 3. Espejo automático en Fineract (`routers/espejo_automatico.py`)
- Con `CORE_ESPEJO=1`, cada préstamo que pasa a `Active` en el core simulado se replica en Fineract usando la función del lote B de la fase 2 (`routers/core_fineract.py`).
- Hazlo con un middleware o un hook que observe `POST /loans/{id}?command=disburse`, **sin editar `core_fineract.py`**.
- Si Fineract no responde, se registra la advertencia y el flujo sigue con el core simulado (plan B automático).

### 4. Contenedores y despliegue
- `Dockerfile` de la API (Python 3.11 slim, usuario no root, `uvicorn` con 2 workers… **ojo**: con `DB` en memoria y varios workers, cada uno tiene su copia. Usa **1 worker**).
- `web/*/Dockerfile`: compila con Node y sirve estático con un servidor ligero. `VITE_API_URL` va como argumento de compilación.
- `docker-compose.yml`: `api`, `asesor`, `cliente` y `tablero`, más el perfil opcional `fineract` que reutiliza `infra/fineract/`.
- `deploy/RAILWAY.md` (u otra plataforma gratuita, documentada): pasos para desplegar los cuatro servicios con sus variables de entorno y un volumen para `data/`. Anota las URLs públicas resultantes en `deploy/URLS.md`.
- `scripts/reset_demo.sh` (y `.ps1`): llama a `/admin/reset` y siembra los datos de demo. Debe correr en menos de 10 s.

### 5. Variables de entorno
`.env.example` con todas las variables del proyecto, comentadas y agrupadas: API, autenticación, persistencia, ENFEN (`ENFEN_MODO`), Fineract, espejo y proveedor de IA (sin valores reales).

## Pruebas (`tests/test_fase3_a.py`)
- Persistencia: se crea un préstamo, se aplaza una cuota, se "reinicia" (nueva `DB`, `cargar`) y el préstamo conserva sus cuotas modificadas y el contador de IDs.
- Con `CUOTAFLEX_AUTH=1`, una escritura sin token devuelve 401, con el rol equivocado devuelve 403, y con el rol correcto devuelve 200.
- Con `CUOTAFLEX_AUTH` apagado, todo funciona como antes.
- `/admin/reset` deja `DB` vacía.
- El espejo automático no rompe el desembolso cuando Fineract no está disponible.
- **Las 111 pruebas existentes siguen pasando.**

## Criterios de aceptación
- [ ] `docker compose up` levanta la API y las tres apps. Al reiniciar la API, los préstamos siguen ahí.
- [ ] Con la autenticación encendida, cada app pide su PIN y solo deja hacer lo que corresponde a su rol.
- [ ] Desplegado en una plataforma pública, con las URLs en `deploy/URLS.md` y la demo funcionando desde un celular (app del cliente).
- [ ] `reset_demo` deja la demo limpia en menos de 10 s.
- [ ] `pytest` pasa completo.
