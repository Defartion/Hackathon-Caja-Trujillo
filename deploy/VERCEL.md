# Despliegue gratuito en Vercel (una sola URL)

Todo va en **un solo proyecto de Vercel, en el plan Hobby (gratis)**:

| Ruta | Qué es |
|---|---|
| `/` | portada para elegir el rol |
| `/asesor/` | app del asesor (usuario + PIN personal) |
| `/cliente/?loanId=N` | app del cliente (número de préstamo + código) |
| `/tablero/` | tablero del supervisor (usuario + PIN personal) |
| `/api/...` | API de CuotaFlex (`/api/docs` para la documentación) |

`server.py` es el punto de entrada: monta la API en `/api` y sirve las apps compiladas desde `public/`.

## Antes de cada despliegue
Si cambió algo en `web/*`, vuelve a compilar las apps y confirma `public/`:
```bash
scripts/construir_web_despliegue.sh
git add public && git commit -m "Apps compiladas para el despliegue"
```

## Primera vez
1. Entra a vercel.com con tu cuenta de GitHub y elige el plan **Hobby** (no pide tarjeta).
2. **Add New → Project** e importa `Defartion/Hackathon-Caja-Trujillo`.
3. Framework preset: **FastAPI**, o "Other" si no lo detecta. Root directory: la raíz del repo. No hace falta comando de build.
4. **Variables de entorno** (Settings → Environment Variables):

| Variable | Valor |
|---|---|
| `CUOTAFLEX_AUTH` | `1` |
| `CUOTAFLEX_SECRETO` | un texto largo y aleatorio |
| `PIN_ASESOR`, `PIN_CLIENTE`, `PIN_SUPERVISOR` | PIN generales de demostración (**no** 1111, 2222 ni 3333) |
| `CUOTAFLEX_PIN_GENERAL` | opcional: `0` apaga los PIN generales cuando todo el equipo ya tiene su llave |
| `CUOTAFLEX_REGISTRO` | opcional: `cliente` (por defecto), `codigo` o `no`. Ver deploy/README.md |
| `ENFEN_MODO` | `demo` (u `oficial` para leer el comunicado real) |

5. **Deploy.** La URL queda como `https://<proyecto>.vercel.app`. Anótala en `deploy/URLS.md`.
6. **Almacén duradero (recomendado, gratis):** pestaña **Storage → Create Database → Upstash for Redis**, plan
   **Free**, y conéctalo al proyecto. Vercel agrega solo `KV_REST_API_URL` y `KV_REST_API_TOKEN`. Vuelve a
   desplegar. Desde ahí duran las llaves del equipo, las cuentas y los préstamos que registren en la demo.
   La pantalla **Equipo** del supervisor avisa si todavía no hay almacén duradero.

## Llaves personales (fase 4)
Cada persona entra con la suya; los PIN generales quedan solo como llave maestra de demostración.

| Quién | Entra con | Quién se la da |
|---|---|---|
| Cliente | número de préstamo + código de 6 dígitos | el asesor: lo ve al desembolsar y en el detalle del préstamo, con botón para WhatsApp. Puede generar otro y el anterior deja de servir |
| Asesor | usuario + PIN personal | un supervisor, en **Equipo** |
| Supervisor | usuario + PIN personal | otro supervisor, en **Equipo** (el primero entra con el PIN general para crearse) |

- Con su código, el cliente **solo ve su préstamo**: si cambia el número del enlace, la API responde 403.
- Desactivar a alguien o cambiarle el PIN **corta sus sesiones abiertas** en segundos.
- El código del cliente se calcula con `CUOTAFLEX_SECRETO`: si cambias el secreto, cambian todos los códigos.
- Tras 5 intentos fallidos se bloquea el ingreso por 10 minutos.

## Qué tener en cuenta
- **Sin Upstash, memoria no persistente:** cada reinicio de la función empieza de cero. `server.py` vuelve a sembrar los préstamos de demo al arrancar, así que nunca queda vacía. Lo que registres durante la demo (préstamos nuevos, aplazamientos, la alerta El Niño encendida a mano) puede perderse tras un rato sin uso. El flujo de propuesta y simulación no guarda nada, así que siempre funciona.
- **Sin Upstash, cuentas y llaves del equipo** también viven en `/tmp` y pueden desaparecer tras un rato sin uso. Los códigos de los préstamos de demo (N° 2 y 4) no cambian, y los PIN generales siempre funcionan. Con Upstash (paso 6) todo esto dura.
- **Primera visita tras un rato sin uso:** tarda unos segundos más. Ábrela unos minutos antes de presentar.
- **Tablero:** en Vercel corre en un solo proceso. Usa el tamaño "Rápido" en la demo (~6 s en local).
- **Dependencias:** `requirements.txt` solo trae lo que necesita la API (~310 MB, debajo del límite de 500 MB de Vercel). Lo de desarrollo está en `requirements-dev.txt`.

## Probarlo localmente igual que en Vercel
```bash
python -m venv .venv-prod && .venv-prod/bin/pip install -r requirements.txt
VERCEL=1 CUOTAFLEX_AUTH=1 .venv-prod/bin/uvicorn server:app --port 8000   # http://localhost:8000/
```
