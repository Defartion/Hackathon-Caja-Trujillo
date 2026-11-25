"""Fase 4 · Lote A: POST /plan/proponer (contrato en docs/fases/fase-4/CONTRATOS.md §2)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from ...plan import proponer_plan
from ...plan.servicio import ErrorSolicitud

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/proponer")
def proponer(solicitud: dict = Body(...)):
    try:
        return proponer_plan(solicitud)
    except ErrorSolicitud as e:
        raise HTTPException(422, str(e))
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(422, f"Solicitud inválida: {e}")
