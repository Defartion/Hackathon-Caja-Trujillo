"""Bandeja de salida simulada. Nada se envía de verdad: "enviar" solo cambia el estado del mensaje.

Vive en memoria y deja una bitácora en `data/outbox.jsonl` (una línea por mensaje creado o enviado).
La bitácora no se vuelve a cargar al iniciar: los préstamos del core de demo también empiezan de cero.
`NOTIFICACIONES_ARCHIVO` cambia la ruta; vacía, desactiva la bitácora.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import count
from pathlib import Path

from ..config import RAIZ
from .plantillas import LARGO_SMS, largo_sms, para_canal

log = logging.getLogger(__name__)

CANALES = ("sms", "whatsapp")
PENDIENTE = "pendiente"
ENVIADO = "enviado-simulado"


def _ahora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def archivo_por_defecto() -> Path | None:
    valor = os.getenv("NOTIFICACIONES_ARCHIVO")
    if valor is None:
        return RAIZ / "data" / "outbox.jsonl"
    return Path(valor) if valor.strip() else None


@dataclass
class Notificacion:
    id: int
    canal: str                # sms | whatsapp
    destinatario: int         # loanId
    plantilla: str
    texto: str
    fecha: str
    estado: str = PENDIENTE   # pendiente | enviado-simulado
    enviado_en: str | None = None
    clave: str = ""           # evita repetir el mismo aviso
    evento: int | None = None # cambio de estado del ENFEN que lo originó

    def a_dict(self) -> dict:
        return asdict(self)


class Outbox:
    def __init__(self, archivo: Path | None = None):
        self.archivo = archivo
        self._mensajes: list[Notificacion] = []
        self._claves: set[str] = set()
        self._ids = count(1)
        self._lock = threading.Lock()

    def agregar(self, *, canal: str, destinatario: int, plantilla: str, texto: str, clave: str = "",
                evento: int | None = None) -> Notificacion | None:
        """Encola un mensaje. Devuelve None si ya existe uno con la misma clave."""
        if canal not in CANALES:
            raise ValueError(f"canal debe ser uno de {CANALES}")
        texto = para_canal(texto, canal)
        if canal == "sms" and largo_sms(texto) > LARGO_SMS:
            log.warning("SMS de %d caracteres para el préstamo %s (%s)", largo_sms(texto), destinatario, plantilla)
        with self._lock:
            if clave and clave in self._claves:
                return None
            mensaje = Notificacion(next(self._ids), canal, int(destinatario), plantilla, texto, _ahora_iso(),
                                   clave=clave, evento=evento)
            self._mensajes.append(mensaje)
            if clave:
                self._claves.add(clave)
            self._anotar(mensaje)
        return mensaje

    def listar(self, destinatario: int | None = None) -> list[Notificacion]:
        """Mensajes del más reciente al más antiguo, opcionalmente de un solo préstamo."""
        with self._lock:
            mensajes = [m for m in self._mensajes if destinatario is None or m.destinatario == destinatario]
        return mensajes[::-1]

    def enviar_pendientes(self) -> list[Notificacion]:
        """Simula el envío: marca los pendientes como enviado-simulado."""
        with self._lock:
            enviados = [m for m in self._mensajes if m.estado == PENDIENTE]
            for mensaje in enviados:
                mensaje.estado, mensaje.enviado_en = ENVIADO, _ahora_iso()
                self._anotar(mensaje)
        return enviados

    def vaciar(self) -> None:
        with self._lock:
            self._mensajes.clear()
            self._claves.clear()

    def _anotar(self, mensaje: Notificacion) -> None:
        if self.archivo is None:
            return
        try:
            self.archivo.parent.mkdir(parents=True, exist_ok=True)
            with self.archivo.open("a", encoding="utf-8") as f:
                f.write(json.dumps(mensaje.a_dict(), ensure_ascii=False) + "\n")
        except OSError as e:
            log.warning("No se pudo escribir la bitácora del outbox (%s): %s", self.archivo, e)


outbox = Outbox(archivo_por_defecto())
