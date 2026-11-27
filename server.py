"""Punto de entrada único para el despliegue (Vercel u otro host): API + las tres apps en una sola URL.

    /api/...     → API de CuotaFlex (la misma de src/cuotaflex/api/main.py)
    /asesor/     → app del asesor
    /cliente/    → app del cliente
    /tablero/    → tablero de simulación
    /            → redirige a /asesor/

Las apps compiladas viven en public/<app>/ (se generan con scripts/construir_web_despliegue.sh).
En Vercel el sistema de archivos es de solo lectura salvo /tmp, y la memoria no se conserva entre
reinicios de la función: por eso la base SQLite va a /tmp y, si al arrancar no hay préstamos, se
siembran los de demo. Localmente: `uvicorn server:app --port 8000` y abrir http://localhost:8000/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

EN_VERCEL = bool(os.getenv("VERCEL"))
if EN_VERCEL:  # rutas escribibles y una sola CPU por función
    os.environ.setdefault("CUOTAFLEX_DB", "/tmp/cuotaflex.db")
    os.environ.setdefault("NOTIFICACIONES_ARCHIVO", "/tmp/outbox.jsonl")
    os.environ.setdefault("CUOTAFLEX_SIM_PROCESOS", "1")
    os.environ.setdefault("ENFEN_REVISION_AUTOMATICA", "0")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, RedirectResponse  # noqa: E402

from cuotaflex.api import main as api  # noqa: E402

if EN_VERCEL:
    try:
        from cuotaflex.integraciones import enfen

        enfen.RUTA_CACHE = Path("/tmp/enfen_cache.json")
    except Exception:  # el lector del ENFEN es opcional para el arranque
        pass

PUBLICO = RAIZ / "public"
APPS = ("asesor", "cliente", "tablero")


def _sembrar_si_vacio() -> None:
    """Tras un arranque en frío la demo nunca queda vacía."""
    # Si no se pudo leer la instantánea (Upstash caído), no se siembra: sembrar borra la instantánea guardada.
    if os.getenv("CUOTAFLEX_SEMBRAR_DEMO", "1") != "1" or api.DB["loans"] or api.CARGA_FALLIDA:
        return
    try:
        from cuotaflex.api.routers.admin import reset

        reset(sembrar=True)
        api.guardar_instantanea()
    except Exception as exc:  # no impedir el arranque por la siembra
        print(f"[cuotaflex] no se pudo sembrar la demo: {exc}", file=sys.stderr)


_sembrar_si_vacio()

app = FastAPI(title="CuotaFlex · demo", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api.app)


@app.get("/", include_in_schema=False)
def inicio():
    """Página para elegir el rol (public/index.html); si no existe, va directo al asesor."""
    portada = PUBLICO / "index.html"
    if portada.is_file():
        return FileResponse(portada)
    return RedirectResponse("/asesor/")


@app.get("/{nombre}", include_in_schema=False)
def sin_barra(nombre: str):
    if nombre in APPS:
        return RedirectResponse(f"/{nombre}/")
    raise HTTPException(404)


@app.get("/{nombre}/{ruta:path}", include_in_schema=False)
def estatico(nombre: str, ruta: str):
    """Sirve los archivos de cada app; las rutas desconocidas vuelven a index.html (apps de una página)."""
    if nombre not in APPS:
        raise HTTPException(404)
    base = (PUBLICO / nombre).resolve()
    archivo = (base / ruta).resolve()
    if ruta and archivo.is_file() and base in archivo.parents:
        return FileResponse(archivo)
    indice = base / "index.html"
    if not indice.is_file():
        raise HTTPException(503, f"La app {nombre} no está compilada (scripts/construir_web_despliegue.sh).")
    return FileResponse(indice, headers={"Cache-Control": "no-cache"})
