"""Llaves personales (fase 4). La lógica vive en cuotaflex/llaves.py.

POST /auth/cliente                          número de préstamo + código → sesión que solo ve ese préstamo
POST /auth/personal                         usuario + PIN personal (asesor o supervisor)
POST /auth/vincular                         una cuenta de cliente (correo) se liga a su préstamo con el código
GET  /motor/prestamos/{id}/llave            el asesor ve el código del cliente para entregárselo
POST /motor/prestamos/{id}/llave/regenerar  código nuevo: el anterior y sus sesiones dejan de servir
GET  /equipo                                supervisor: personas con llave personal
POST /equipo                                supervisor: agrega una persona (devuelve su PIN una sola vez)
POST /equipo/{usuario}/pin                  supervisor: PIN nuevo (corta las sesiones abiertas)
POST /equipo/{usuario}/estado               supervisor: activar o desactivar
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ... import almacen, cuentas, llaves
from . import auth

router = APIRouter(tags=["llaves"])


class IngresoCliente(BaseModel):
    prestamo: int = Field(ge=1, description="Número de préstamo")
    codigo: str = Field(max_length=12, description="Código de 6 dígitos que entrega el asesor")


class IngresoPersonal(BaseModel):
    usuario: str = Field(max_length=60)
    pin: str = Field(max_length=12)
    rol: Literal["asesor", "supervisor"] | None = Field(None, description="app desde la que se entra")


class NuevaPersona(BaseModel):
    nombre: str = Field(max_length=200)
    rol: Literal["asesor", "supervisor"]


class EstadoPersona(BaseModel):
    activo: bool


def _error(e: Exception) -> JSONResponse:
    estado, mensaje = getattr(e, "estado", 400), getattr(e, "mensaje", str(e))
    return JSONResponse({"detail": mensaje, "campo": getattr(e, "campo", None)}, status_code=estado)


def _sesion(rol: str, datos: dict) -> dict:
    return {"token": auth.emitir_token(rol, extra=datos), "rol": rol, "expira_en_s": auth.DURACION_S,
            "usuario": {k: v for k, v in datos.items() if k in ("nombre", "usuario", "prestamo")}}


def _datos_sesion(authorization: str | None) -> dict | None:
    token = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else ""
    return auth.datos_token(token) if token else None


def _prestamo(lid: int) -> dict | None:
    from .. import main as api

    return api.DB["loans"].get(int(lid))


# ---------------------------------------------------------------- ingreso

@router.post("/auth/cliente")
def ingresar_cliente(datos: IngresoCliente):
    try:
        return _sesion("cliente", llaves.entrar_cliente(datos.prestamo, datos.codigo))
    except llaves.ErrorLlave as e:
        return _error(e)


@router.post("/auth/personal")
def ingresar_personal(datos: IngresoPersonal):
    try:
        rol, extra = llaves.entrar_personal(datos.usuario, datos.pin, datos.rol)
    except llaves.ErrorLlave as e:
        return _error(e)
    except almacen.ErrorAlmacen:
        return JSONResponse({"detail": "No se pudo revisar tu usuario ahora. Intenta en un momento."}, status_code=503)
    return _sesion(rol, extra)


@router.post("/auth/vincular")
def vincular(datos: IngresoCliente, authorization: str | None = Header(None)):
    sesion = _datos_sesion(authorization)
    if not sesion or sesion.get("rol") != "cliente" or sesion.get("id") is None:
        return JSONResponse({"detail": "Ingresa con tu cuenta de cliente para vincular tu préstamo."}, status_code=401)
    try:
        vinculo = llaves.vincular_cuenta(sesion["id"], datos.prestamo, datos.codigo)
    except llaves.ErrorLlave as e:
        return _error(e)
    return _sesion("cliente", {"id": sesion["id"], "nombre": sesion.get("nombre"), **vinculo})


# ---------------------------------------------------------------- código del cliente (asesor)

def _llave(lid: int, regenerar: bool):
    from .. import main as api

    p = _prestamo(lid)
    if p is None:
        return JSONResponse({"detail": f"No existe el préstamo {lid}."}, status_code=404)
    with api._candado_db:
        antes = (p.get("llaveUid"), p.get("llaveVersion"))
        codigo = llaves.regenerar_codigo(p) if regenerar else llaves.codigo_cliente(p)
        cambio = antes != (p.get("llaveUid"), p.get("llaveVersion"))
    if cambio:
        api.guardar_instantanea()
    return {"prestamo": int(lid), "codigo": codigo, "version": p["llaveVersion"], "estado": p["status"]["value"],
            "cliente": llaves._nombre_cliente(p)}


@router.get("/motor/prestamos/{lid}/llave")
def ver_llave(lid: int):
    return _llave(lid, regenerar=False)


@router.post("/motor/prestamos/{lid}/llave/regenerar")
def regenerar_llave(lid: int):
    return _llave(lid, regenerar=True)


# ---------------------------------------------------------------- equipo (supervisor)

def _quien(authorization: str | None) -> tuple[str | None, str | None]:
    s = _datos_sesion(authorization) or {}
    return s.get("usuario"), s.get("nombre") or ("PIN general" if s else None)


@router.get("/equipo")
def ver_equipo():
    try:
        return {"almacen": almacen.estado(), "pin_general": llaves.pin_general_activo(), "personas": llaves.listar_equipo()}
    except almacen.ErrorAlmacen as e:
        return JSONResponse({"detail": str(e)}, status_code=503)


@router.post("/equipo", status_code=201)
def agregar_persona(datos: NuevaPersona, authorization: str | None = Header(None)):
    try:
        persona, pin = llaves.crear_persona(datos.nombre, datos.rol, _quien(authorization)[1])
    except (llaves.ErrorLlave, cuentas.ErrorCuenta) as e:
        return _error(e)
    except almacen.ErrorAlmacen as e:
        return JSONResponse({"detail": str(e)}, status_code=503)
    return {"persona": persona, "pin": pin}


@router.post("/equipo/{usuario}/pin")
def cambiar_pin(usuario: str):
    try:
        persona, pin = llaves.nuevo_pin(usuario)
    except llaves.ErrorLlave as e:
        return _error(e)
    return {"persona": persona, "pin": pin}


@router.post("/equipo/{usuario}/estado")
def cambiar_estado(usuario: str, datos: EstadoPersona, authorization: str | None = Header(None)):
    try:
        return {"persona": llaves.cambiar_estado(usuario, datos.activo, _quien(authorization)[0])}
    except llaves.ErrorLlave as e:
        return _error(e)
