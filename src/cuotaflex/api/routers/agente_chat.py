"""Sesiones locales del agente del asesor."""
from __future__ import annotations

from collections import OrderedDict
from math import isfinite
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from ...agente_chat import SesionChat
from .asesor import RUBROS, ClienteSolicitud

router = APIRouter(prefix="/agente", tags=["agente"])
_sesiones: OrderedDict[str, SesionChat] = OrderedDict()
_bloqueo = Lock()
_MAX_SESIONES = 128


class Mensaje(BaseModel):
    texto: str = Field(min_length=1, max_length=1000)

    @field_validator("texto", mode="before")
    @classmethod
    def sin_bordes(cls, texto):
        return texto.strip() if isinstance(texto, str) else texto


def _sesion(sesion_id: str) -> SesionChat:
    with _bloqueo:
        sesion = _sesiones.get(sesion_id)
        if sesion is None:
            raise HTTPException(404, "La sesión no existe o expiró. Abre de nuevo el chat.")
        _sesiones.move_to_end(sesion_id)
        return sesion


@router.post("/sesion")
def iniciar_sesion(solicitud: ClienteSolicitud):
    if solicitud.rubro not in RUBROS:
        raise HTTPException(422, f"rubro inválido; use {list(RUBROS)}")
    valores = list(solicitud.model_dump(exclude={"historial_ventas"}).values())
    valores.extend(solicitud.historial_ventas or ())
    if any(isinstance(valor, float) and not isfinite(valor) for valor in valores):
        raise HTTPException(422, "La solicitud solo admite valores numéricos finitos.")
    sesion = SesionChat(solicitud)
    sesion_id = uuid4().hex
    with _bloqueo:
        _sesiones[sesion_id] = sesion
        if len(_sesiones) > _MAX_SESIONES:
            _sesiones.popitem(last=False)
    return {"sesion_id": sesion_id, "propuesta": sesion.propuesta}


@router.post("/sesion/{sesion_id}/mensaje")
def enviar_mensaje(sesion_id: str, mensaje: Mensaje):
    return _sesion(sesion_id).responder(mensaje.texto)


@router.get("/explicacion")
def obtener_explicacion(sesion_id: str, audiencia: Literal["cliente", "asesor"] = "cliente"):
    return _sesion(sesion_id).explicar(audiencia)
