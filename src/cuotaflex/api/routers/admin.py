"""Administración de la demo (fase 3): reinicio limpio y siembra de casos."""
from __future__ import annotations

from itertools import count

from fastapi import APIRouter

from ... import persistencia

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
def reset(sembrar: bool = True):
    """Vacía el core simulado y la base de datos; opcionalmente siembra los préstamos de demo."""
    from .. import main as api

    with api._candado_db:
        for tabla in api.DB.values():
            tabla.clear()
        api._ids = count(1)
        persistencia.borrar()
    sembrados = []
    if sembrar:
        from .cliente import demo_seed

        sembrados = [demo_seed("estacional"), demo_seed("aplazamiento")]
    return {"ok": True, "prestamos": len(api.DB["loans"]), "sembrados": sembrados}
