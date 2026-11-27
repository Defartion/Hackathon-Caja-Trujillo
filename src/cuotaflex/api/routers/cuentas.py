"""Crear cuenta e ingresar con correo y contraseña (además del PIN por rol de routers/auth.py).

POST /auth/registro   crea la cuenta y deja la sesión iniciada (mismo token que el PIN, con el nombre).
POST /auth/ingresar   valida correo y contraseña; si se indica `rol`, la cuenta debe ser de ese rol.
GET  /auth/yo         quién tiene la sesión (para el perfil); responde 200 también sin sesión.

Van bajo /auth, que es público en las reglas del middleware: cada ruta valida lo suyo.
Quién puede registrarse lo decide CUOTAFLEX_REGISTRO (ver cuotaflex/cuentas.py).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header
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
    extra = {"id": cuenta["id"], "nombre": cuenta["nombre"]}
    if cuenta["rol"] == "cliente":  # fase 4: si la cuenta ya vinculó su préstamo, la sesión solo ve ese préstamo
        from ... import llaves

        extra.update(llaves.vinculo_cuenta(cuenta["id"]))
    token = auth.emitir_token(cuenta["rol"], extra=extra)
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


@router.get("/yo")
def yo(authorization: str | None = Header(None)):
    """Perfil de la sesión. Sin token válido responde {"sesion": false} (no 401, para no ensuciar la consola)."""
    token = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else ""
    datos = auth.datos_token(token) if token else None
    if not datos:
        return {"sesion": False}
    perfil = {"sesion": True, "rol": datos["rol"], "metodo": "pin", "id": None, "nombre": None, "correo": None,
              "creado": None, "expira": datos["exp"]}
    if datos.get("id") is not None:
        cuenta = cuentas.por_id(datos["id"])
        perfil.update(metodo="cuenta", id=datos["id"], nombre=datos.get("nombre"))
        if cuenta:
            perfil.update(nombre=cuenta["nombre"], correo=cuenta["correo"], creado=cuenta["creado"])
    elif datos.get("usuario"):  # fase 4: usuario + PIN personal
        perfil.update(metodo="personal", nombre=datos.get("nombre"), usuario=datos["usuario"])
    elif datos.get("prestamo") is not None:  # fase 4: código del préstamo
        perfil.update(metodo="codigo", nombre=datos.get("nombre"))
    if datos.get("prestamo") is not None:
        perfil["prestamo"] = datos["prestamo"]
    return perfil
