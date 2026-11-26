# Despliegue de CuotaFlex (fase 3 · lote A)

## Local con Docker (recomendado para la final)
```bash
cp .env.example .env            # completar; para la demo: CUOTAFLEX_AUTH=1 y PINs propios
docker compose up --build       # API :8000 · asesor :5173 · cliente :5174 · tablero :5175
scripts/reset_demo.sh           # deja la demo limpia (Windows: .\scripts\reset_demo.ps1)
```
- Los datos viven en el volumen `datos` (SQLite): sobreviven a `docker compose restart`. Para empezar de cero: `docker compose down -v` o `reset_demo`.
- **Un solo worker de uvicorn**, a propósito: el core simulado vive en memoria y se guarda como instantánea.
- **Fineract real:** levántalo aparte con `infra/fineract/up.sh` y pon en `.env` `FINERACT_URL=https://host.docker.internal:8443/fineract-provider/api/v1`, las credenciales y `CORE_ESPEJO=1`. Si Fineract cae, la demo sigue con el core simulado. El estado del espejo se ve en `GET /core/espejo-automatico`.

## Sin Docker
```bash
pip install -r requirements.txt
PYTHONPATH=src uvicorn cuotaflex.api.main:app --port 8000 --workers 1
cd web/asesor && npm ci && npm run build && npx vite preview --port 5173   # ídem cliente (5174) y tablero (5175)
```

## Roles: cuentas y PIN
Con `CUOTAFLEX_AUTH=1`, cada app pide entrar de una de tres formas: **ingresar** con correo y contraseña,
**crear cuenta** o **entrar con el PIN** del rol (como antes):

| App | Rol | Variable | PIN de demo |
|---|---|---|---|
| Asesor (5173) | asesor | `PIN_ASESOR` | 1111 |
| Cliente (5174) | cliente | `PIN_CLIENTE` | 2222 |
| Tablero (5175) | supervisor | `PIN_SUPERVISOR` | 3333 |

**Cambia los PIN y `CUOTAFLEX_SECRETO` antes de publicar una URL.** El token dura 12 h y se guarda en la pestaña (`sessionStorage`).

Cuentas (`src/cuotaflex/cuentas.py`, rutas `POST /auth/registro` y `POST /auth/ingresar`):
- Quién puede crear cuenta lo decide `CUOTAFLEX_REGISTRO`. Por defecto (`cliente`) el cliente se registra solo y
  el asesor y el supervisor escriben el PIN de su rol como **código de autorización**: así nadie se da a sí mismo
  el rol de supervisor. Con `codigo` todos los roles lo piden; con `no` no se crean cuentas nuevas.
- La contraseña se guarda como hash scrypt con sal (nunca en texto). Pide al menos 8 caracteres con letras y números.
- Tras 5 intentos fallidos con un mismo correo, ese correo espera 10 minutos (el PIN sigue disponible).
- Las cuentas van en la tabla `cuentas` del mismo SQLite (`CUOTAFLEX_DB`). `reset_demo` no las borra.
- Una cuenta solo entra a la app de su rol. El token lleva el nombre, que se muestra en el menú de cada app.

| Prefijo | Roles |
|---|---|
| `/motor`, `/agente`, escrituras en `/fineract-provider` | asesor, supervisor |
| `/cliente`, lecturas en `/fineract-provider` | cliente, asesor, supervisor |
| `/simulacion`, `/alertas`, `/core`, `/admin` | supervisor |

Límite conocido (demo): el rol cliente no está atado a un préstamo concreto.

## Despliegue público (Railway u otra plataforma con Docker)
Son 4 servicios desde el mismo repositorio:

| Servicio | Dockerfile | Variables | Puerto |
|---|---|---|---|
| api | `Dockerfile` | las de `.env.example`, más `CUOTAFLEX_ORIGENES` con las URLs públicas de las 3 apps | `PORT` (lo pone la plataforma) |
| asesor | `web/asesor/Dockerfile` | build arg `VITE_API_URL` = URL pública de la API | `PORT` (nginx lo usa) |
| cliente | `web/cliente/Dockerfile` | ídem | ídem |
| tablero | `web/tablero/Dockerfile` | ídem | ídem |

Pasos en Railway:
1. Crea un proyecto y agrega el repo cuatro veces, una por servicio.
2. En cada servicio, en *Settings → Build*, indica la ruta del Dockerfile. El contexto es la raíz del repo.
3. En la **api**, agrega un **volumen** montado en `/app/data`. Sin volumen, cada redeploy borra los datos.
4. Despliega la API primero. Copia su URL y úsala como `VITE_API_URL` (build arg) en las 3 apps.
5. Despliega las apps y pon sus 3 URLs en `CUOTAFLEX_ORIGENES` de la API. Vuelve a desplegar la API.
6. Corre `scripts/reset_demo.sh https://<api>` y anota las URLs en `deploy/URLS.md`.

Las apps se compilan con la URL de la API dentro (Vite). Si la URL de la API cambia, hay que recompilar las apps.
