"""Espejo automático en Apache Fineract (fase 3).

Con CORE_ESPEJO=1, cada préstamo que se desembolsa en el core simulado se replica en Fineract en un
hilo aparte, reutilizando `core_fineract.crear_espejo` (lote B de la fase 2). Si Fineract no responde,
se registra la advertencia y la demo sigue con el core simulado: plan B automático.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from collections import deque
from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/core", tags=["core"])
log = logging.getLogger("cuotaflex.espejo")
_RUTA = re.compile(r"/fineract-provider/api/v1/loans/(\d+)$")
HISTORIAL: deque[dict] = deque(maxlen=100)


def activo() -> bool:
    return os.getenv("CORE_ESPEJO", "0").strip() == "1"


def replicar(loan_id: int) -> dict:
    from .core_fineract import crear_espejo

    registro = {"loanId": loan_id, "fecha": datetime.now().isoformat(timespec="seconds")}
    try:
        resultado = crear_espejo(loan_id)
        registro.update(ok=True, resultado=resultado)
    except Exception as exc:  # Fineract apagado o error: no se interrumpe la demo
        registro.update(ok=False, error=getattr(exc, "detail", None) or str(exc))
        log.warning("Espejo en Fineract falló para el préstamo %s: %s", loan_id, registro["error"])
    HISTORIAL.append(registro)
    return registro


def programar(ruta: str, sincrono: bool = False) -> bool:
    """Llamado por el middleware tras un desembolso exitoso. Devuelve True si programó el espejo."""
    m = _RUTA.search(ruta)
    if not (activo() and m):
        return False
    if sincrono:
        replicar(int(m.group(1)))
    else:
        threading.Thread(target=replicar, args=(int(m.group(1)),), daemon=True).start()
    return True


@router.get("/espejo-automatico")
def estado_espejo():
    return {"activo": activo(), "ultimos": list(HISTORIAL)[-10:]}
