"""Plantillas de mensajes para el cliente, en español sencillo.

Cada SMS cabe en un solo mensaje: 160 caracteres del alfabeto GSM-7. Las vocales con tilde (á, í, ó, ú) no
existen en GSM-7 y harían que el teléfono use UCS-2, donde solo caben 70 caracteres; por eso el texto del
canal SMS se escribe sin ellas (la ñ, la é, ¡ y ¿ sí existen). WhatsApp conserva las tildes.
"""
from __future__ import annotations

import unicodedata
from datetime import date

FIRMA = "CuotaFlex"  # marca de la solución: no se firma a nombre de la Caja
LARGO_SMS = 160
LARGO_NOMBRE = 12

PLANTILLAS = {
    "recordatorio_cuota": "Recordatorio de cuota (3 días antes)",
    "temporada_baja": "Aviso de temporada baja",
    "alerta_el_nino": "Alerta El Niño activa",
    "vigilancia_el_nino": "Vigilancia El Niño (preventivo, sin alivio)",
    "aplazamiento_confirmado": "Aplazamiento confirmado",
}

MESES = {"ene": "enero", "feb": "febrero", "mar": "marzo", "abr": "abril", "may": "mayo", "jun": "junio",
         "jul": "julio", "ago": "agosto", "set": "setiembre", "oct": "octubre", "nov": "noviembre",
         "dic": "diciembre"}

_GSM7 = frozenset("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "ÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
_GSM7_EXTENDIDO = frozenset("^{}\\[~]|€")  # cada uno ocupa 2 caracteres
_A_GSM7 = str.maketrans({"á": "a", "í": "i", "ó": "o", "ú": "u", "Á": "A", "Í": "I", "Ó": "O", "Ú": "U",
                         "“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "…": "...", "°": "o"})


def a_gsm7(texto: str) -> str:
    """Texto apto para un SMS GSM-7: quita las tildes que no existen y reemplaza lo demás."""
    salida = []
    for c in texto.translate(_A_GSM7):
        if c in _GSM7 or c in _GSM7_EXTENDIDO:
            salida.append(c)
        else:
            base = unicodedata.normalize("NFKD", c)[0]
            salida.append(base if base in _GSM7 else "?")
    return "".join(salida)


def largo_sms(texto: str) -> int:
    """Caracteres que ocupa el texto en un SMS GSM-7 (los del alfabeto extendido cuentan doble)."""
    fuera = sorted({c for c in texto if c not in _GSM7 and c not in _GSM7_EXTENDIDO})
    if fuera:
        raise ValueError(f"Caracteres fuera de GSM-7: {''.join(fuera)}")
    return sum(2 if c in _GSM7_EXTENDIDO else 1 for c in texto)


def para_canal(texto: str, canal: str) -> str:
    return a_gsm7(texto) if canal == "sms" else texto


def soles(monto: float) -> str:
    return f"S/ {monto:,.2f}"


def primer_nombre(nombre: str | None) -> str:
    partes = (nombre or "").split()
    return partes[0][:LARGO_NOMBRE].capitalize() if partes else "Hola"


def recordatorio_cuota(nombre: str | None, numero: int, total: int, monto: float, vence: date) -> str:
    return (f"Hola {primer_nombre(nombre)}, tu cuota {numero} de {total} de {soles(monto)} vence el "
            f"{vence:%d/%m}. Págala a tiempo y cuida tu buen historial. {FIRMA}")


def temporada_baja(nombre: str | None, mes: str, monto: float) -> str:
    return (f"¡Buenas noticias, {primer_nombre(nombre)}! En {MESES.get(mes, mes)} tu cuota baja a "
            f"{soles(monto)} por temporada baja. Aprovecha para ahorrar un poco. {FIRMA}")


def alerta_el_nino(nombre: str | None) -> str:
    return (f"{primer_nombre(nombre)}: el ENFEN declaró Alerta de El Niño Costero. Puedes usar tu alivio y pagar "
            f"solo la cuota mínima. En la app toca 'Usar alivio'. {FIRMA}")


def vigilancia_el_nino(nombre: str | None) -> str:
    return (f"{primer_nombre(nombre)}: el ENFEN activó la Vigilancia de El Niño Costero. Aún no hay alivio. "
            f"Si puedes, ahorra para tus cuotas. Te avisaremos. {FIRMA}")


def aplazamiento_confirmado(nombre: str | None, numero: int, nueva_cuota: float, costo_adicional: float) -> str:
    return (f"{primer_nombre(nombre)}, aplazamos tu cuota {numero}: ahora pagas {soles(nueva_cuota)}. El costo "
            f"adicional es {soles(costo_adicional)} y se reparte en tus próximas cuotas. {FIRMA}")
