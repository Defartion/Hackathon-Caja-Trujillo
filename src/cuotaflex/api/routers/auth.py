"""Roles simples con PIN de demo y token firmado (fase 3).

Solo actúa con CUOTAFLEX_AUTH=1; por defecto está apagado para que las pruebas y el desarrollo
funcionen igual que antes. Variables: PIN_ASESOR, PIN_CLIENTE, PIN_SUPERVISOR, CUOTAFLEX_SECRETO.
El control por prefijo de ruta se aplica como middleware en api/main.py (`permiso_requerido`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

ROLES = ("asesor", "cliente", "supervisor")
DURACION_S = 12 * 3600
_PINS_DEMO = {"asesor": "1111", "cliente": "2222", "supervisor": "3333"}
_SECRETO_EFIMERO = secrets.token_hex(32)

# (prefijo, métodos o None = todos, roles permitidos). Gana la primera coincidencia.
REGLAS: list[tuple[str, set[str] | None, set[str]]] = [
    ("/auth", None, set()),                                   # público
    ("/docs", None, set()), ("/openapi.json", None, set()), ("/redoc", None, set()),
    ("/admin", None, {"supervisor"}),
    ("/simulacion", None, {"supervisor"}),
    ("/alertas", None, {"supervisor"}),
    ("/core", None, {"supervisor"}),
    ("/motor", None, {"asesor", "supervisor"}),
    ("/agente", None, {"asesor", "supervisor"}),
    ("/cliente", None, {"cliente", "asesor", "supervisor"}),
    ("/fineract-provider", {"GET"}, {"cliente", "asesor", "supervisor"}),
    ("/fineract-provider", None, {"asesor", "supervisor"}),
]


def activa() -> bool:
    return os.getenv("CUOTAFLEX_AUTH", "0").strip() == "1"


def _secreto() -> bytes:
    return (os.getenv("CUOTAFLEX_SECRETO") or _SECRETO_EFIMERO).encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def emitir_token(rol: str, ahora: float | None = None) -> str:
    cuerpo = _b64(json.dumps({"rol": rol, "exp": int((time.time() if ahora is None else ahora) + DURACION_S)}).encode())
    firma = _b64(hmac.new(_secreto(), cuerpo.encode(), hashlib.sha256).digest())
    return f"{cuerpo}.{firma}"


def verificar_token(token: str) -> str | None:
    """Devuelve el rol si el token es válido y no venció."""
    try:
        cuerpo, firma = token.split(".")
        esperada = _b64(hmac.new(_secreto(), cuerpo.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            return None
        datos = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
        return datos["rol"] if datos["exp"] > time.time() and datos["rol"] in ROLES else None
    except Exception:
        return None


def permiso_requerido(ruta: str, metodo: str) -> set[str] | None:
    """Roles permitidos para la ruta; set() = pública; None = sin regla (se exige cualquier rol)."""
    for prefijo, metodos, roles in REGLAS:
        if (ruta == prefijo or ruta.startswith(prefijo + "/")) and (metodos is None or metodo in metodos):
            return roles
    return None


def _pin(rol: str) -> str:
    return os.getenv(f"PIN_{rol.upper()}", _PINS_DEMO[rol])


class Login(BaseModel):
    rol: Literal["asesor", "cliente", "supervisor"]
    pin: str


@router.get("/config")
def config():
    return {"auth": activa(), "roles": list(ROLES)}


@router.post("/login")
def login(datos: Login):
    if not hmac.compare_digest(datos.pin, _pin(datos.rol)):
        raise HTTPException(401, "PIN incorrecto")
    return {"token": emitir_token(datos.rol), "rol": datos.rol, "expira_en_s": DURACION_S}
