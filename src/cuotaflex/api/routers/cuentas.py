"""Crear cuenta e ingresar con correo y contraseña (además del PIN por rol de routers/auth.py).

POST /auth/registro   crea la cuenta y deja la sesión iniciada (mismo token que el PIN, con el nombre).
POST /auth/ingresar   valida correo y contraseña; si se indica `rol`, la cuenta debe ser de ese rol.

Van bajo /auth, que es público en las reglas del middleware: cada ruta valida lo suyo.
Quién puede registrarse lo decide CUOTAFLEX_REGISTRO (ver cuotaflex/cuentas.py).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ... import cuentas
from . import auth

router = APIRouter(prefix="/auth", tags=["cuentas"])


class Registro(BaseModel):
    rol: Literal["asesor", "cliente", "supervisor"]
    nombre: str = Field(max_length=200)
    correo: str = Field(max_length=200)
    contrasena: str = Field(max_length=200)
    codigo: str | None = Field(None, max_length=64, description="PIN del rol, si el rol lo exige para registrarse")


class Ingreso(BaseModel):
    correo: str = Field(max_length=200)
    contrasena: str = Field(max_length=200)
    rol: Literal["asesor", "cliente", "supervisor"] | None = Field(None, description="rol de la app desde la que se entra")


def _sesion(cuenta: dict) -> dict:
    token = auth.emitir_token(cuenta["rol"], extra={"id": cuenta["id"], "nombre": cuenta["nombre"]})
    return {"token": token, "rol": cuenta["rol"], "expira_en_s": auth.DURACION_S, "usuario": cuenta}


def _error(e: cuentas.ErrorCuenta) -> JSONResponse:
    """`detail` es texto, como en el resto de la API; `campo` dice qué dato corregir (si aplica)."""
    return JSONResponse({"detail": e.mensaje, "campo": e.campo}, status_code=e.estado)


@router.post("/registro", status_code=201)
def registro(datos: Registro):
    try:
        cuenta = cuentas.registrar(datos.rol, datos.nombre, datos.correo, datos.contrasena, datos.codigo,
                                   auth._pin(datos.rol))
    except cuentas.ErrorCuenta as e:
        return _error(e)
    return _sesion(cuenta)


@router.post("/ingresar")
def ingresar(datos: Ingreso):
    try:
        cuenta = cuentas.ingresar(datos.correo, datos.contrasena, datos.rol)
    except cuentas.ErrorCuenta as e:
        return _error(e)
    return _sesion(cuenta)
