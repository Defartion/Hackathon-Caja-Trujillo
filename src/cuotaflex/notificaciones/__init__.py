"""Notificaciones simuladas (SMS y WhatsApp) para los clientes de CuotaFlex. No se envía nada real."""
from . import plantillas
from .bandeja import CANALES, ENVIADO, PENDIENTE, Notificacion, Outbox, outbox

__all__ = ["CANALES", "ENVIADO", "PENDIENTE", "Notificacion", "Outbox", "outbox", "plantillas"]
