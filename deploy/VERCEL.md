# Despliegue gratuito en Vercel (una sola URL)

Todo va en **un solo proyecto de Vercel, en el plan Hobby (gratis)**:

| Ruta | Qué es |
|---|---|
| `/` | redirige a `/asesor/` |
| `/asesor/` | app del asesor (PIN de asesor) |
| `/cliente/?loanId=N` | app del cliente (PIN de cliente) |
| `/tablero/` | tablero de simulación (PIN de supervisor) |
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
| `PIN_ASESOR`, `PIN_CLIENTE`, `PIN_SUPERVISOR` | PIN propios (**no** 1111, 2222 ni 3333) |
| `ENFEN_MODO` | `demo` (u `oficial` para leer el comunicado real) |

5. **Deploy.** La URL queda como `https://<proyecto>.vercel.app`. Anótala en `deploy/URLS.md`.

## Qué tener en cuenta
- **Memoria no persistente:** cada reinicio de la función empieza de cero. `server.py` vuelve a sembrar los préstamos de demo al arrancar, así que nunca queda vacía. Lo que registres durante la demo (préstamos nuevos, aplazamientos, la alerta El Niño encendida a mano) puede perderse tras un rato sin uso. El flujo de propuesta y simulación no guarda nada, así que siempre funciona.
- **Primera visita tras un rato sin uso:** tarda unos segundos más. Ábrela unos minutos antes de presentar.
- **Tablero:** en Vercel corre en un solo proceso. Usa el tamaño "Rápido" en la demo (~6 s en local).
- **Dependencias:** `requirements.txt` solo trae lo que necesita la API (~310 MB, debajo del límite de 500 MB de Vercel). Lo de desarrollo está en `requirements-dev.txt`.

## Probarlo localmente igual que en Vercel
```bash
python -m venv .venv-prod && .venv-prod/bin/pip install -r requirements.txt
VERCEL=1 CUOTAFLEX_AUTH=1 .venv-prod/bin/uvicorn server:app --port 8000   # http://localhost:8000/
```
