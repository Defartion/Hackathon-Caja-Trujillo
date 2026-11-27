"""Llaves personales (fase 4): cada persona entra con la suya.

- Cliente: número de préstamo + código de 6 dígitos que le entrega su asesor. El código se calcula (HMAC con
  CUOTAFLEX_SECRETO) a partir de un identificador aleatorio del préstamo y una versión: no se guarda aparte y no
  se pierde si el servidor se reinicia. Generar otro sube la versión, así que el anterior y las sesiones abiertas
  con él dejan de servir. Con ese código el cliente solo ve SU préstamo.
- Asesor y supervisor: usuario + PIN personal de 6 dígitos que crea un supervisor en la pantalla Equipo. El PIN se
  guarda con hash (como las contraseñas) en el almacén duradero; desactivar a la persona o cambiarle el PIN corta
  sus sesiones abiertas.
- Los PIN generales de cada rol (PIN_ASESOR, PIN_CLIENTE, PIN_SUPERVISOR) quedan como llave maestra de
  demostración: sirven para crear al primer supervisor y para el jurado. Se apagan con CUOTAFLEX_PIN_GENERAL=0.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
import unicodedata
from datetime import datetime

from . import almacen, cuentas

DIGITOS = 6
MAX_INTENTOS = 5          # intentos fallidos por préstamo o usuario...
VENTANA_S = 600           # ...dentro de esta ventana antes de bloquear
CACHE_EQUIPO_S = 15       # cada cuánto se vuelve a mirar si una persona sigue activa
ROLES_EQUIPO = ("asesor", "supervisor")

_candado = threading.Lock()
_fallidos: dict[str, list[float]] = {}
_cache_equipo: dict[str, tuple[float, dict | None]] = {}

_RE_PRESTAMO = re.compile(r"^/cliente/prestamos/(\d+)(?:/.*)?$")
_RE_FINERACT = re.compile(r"^/fineract-provider/api/v1/loans/(\d+)$")
_RE_USUARIO = re.compile(r"^[a-z0-9][a-z0-9.]{1,40}$")


class ErrorLlave(Exception):
    def __init__(self, estado: int, mensaje: str, campo: str | None = None):
        super().__init__(mensaje)
        self.estado, self.mensaje, self.campo = estado, mensaje, campo


def pin_general_activo() -> bool:
    return os.getenv("CUOTAFLEX_PIN_GENERAL", "1").strip() != "0"


def _secreto() -> bytes:
    from .api.routers import auth  # import tardío: auth importa módulos de este paquete

    return auth._secreto()


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- intentos fallidos

def _bloqueado(clave: str) -> bool:
    ahora = time.time()
    with _candado:
        recientes = [t for t in _fallidos.get(clave, []) if ahora - t < VENTANA_S]
        _fallidos[clave] = recientes
        return len(recientes) >= MAX_INTENTOS


def _fallo(clave: str) -> None:
    with _candado:
        _fallidos.setdefault(clave, []).append(time.time())


def _acierto(clave: str) -> None:
    with _candado:
        _fallidos.pop(clave, None)


def _revisar_bloqueo(clave: str) -> None:
    if _bloqueado(clave):
        raise ErrorLlave(429, "Demasiados intentos fallidos. Espera unos minutos e intenta de nuevo.")


# ---------------------------------------------------------------- cliente: código por préstamo

def preparar_prestamo(prestamo: dict, uid: str | None = None) -> None:
    """Le da al préstamo su identificador de llave (si no tiene) y la versión 1 del código."""
    if uid:
        prestamo["llaveUid"] = uid
    prestamo.setdefault("llaveUid", secrets.token_hex(8))
    prestamo.setdefault("llaveVersion", 1)


def codigo_cliente(prestamo: dict) -> str:
    preparar_prestamo(prestamo)
    mensaje = f"cliente|{prestamo['llaveUid']}|{int(prestamo['llaveVersion'])}".encode()
    d = hmac.new(_secreto(), mensaje, hashlib.sha256).digest()
    return f"{int.from_bytes(d[:8], 'big') % 10 ** DIGITOS:0{DIGITOS}d}"


def regenerar_codigo(prestamo: dict) -> str:
    preparar_prestamo(prestamo)
    prestamo["llaveVersion"] = int(prestamo["llaveVersion"]) + 1
    return codigo_cliente(prestamo)


def _db():
    from .api import main as api

    return api.DB


def _nombre_cliente(prestamo: dict) -> str | None:
    c = _db()["clients"].get(prestamo.get("clientId"), {})
    return c.get("nombre") or None


def _validar_codigo(lid: int, codigo: str) -> dict:
    clave = f"cliente:{int(lid)}"
    _revisar_bloqueo(clave)
    prestamo = _db()["loans"].get(int(lid))
    limpio = re.sub(r"\s", "", codigo or "")
    if prestamo is None or not prestamo.get("llaveUid") or not hmac.compare_digest(codigo_cliente(prestamo), limpio):
        _fallo(clave)
        raise ErrorLlave(401, "Número de préstamo o código incorrecto. Revísalos o pide un código nuevo a tu asesor.",
                         "codigo")
    _acierto(clave)
    return prestamo


def entrar_cliente(lid: int, codigo: str) -> dict:
    """Datos para el token del cliente que entra con el código de su préstamo."""
    p = _validar_codigo(lid, codigo)
    return {"prestamo": int(lid), "llave": p["llaveUid"], "v": int(p["llaveVersion"]), "nombre": _nombre_cliente(p)}


def vinculo_cuenta(cuenta_id: int) -> dict:
    """Préstamo vinculado a una cuenta de cliente (correo y contraseña), o {} si aún no tiene."""
    v = almacen.leer_json(f"vinculo:{int(cuenta_id)}")
    return {"prestamo": v["prestamo"], "llave": v["llave"]} if v else {}


def vincular_cuenta(cuenta_id: int, lid: int, codigo: str) -> dict:
    """La cuenta queda ligada al préstamo; desde ahí, al ingresar con correo ve solo ese préstamo."""
    p = _validar_codigo(lid, codigo)
    vinculo = {"prestamo": int(lid), "llave": p["llaveUid"]}
    almacen.escribir_json(f"vinculo:{int(cuenta_id)}", {**vinculo, "desde": _ahora()})
    return vinculo


# ---------------------------------------------------------------- equipo: usuario + PIN personal

def _pin_nuevo() -> str:
    while True:
        pin = f"{secrets.randbelow(10 ** DIGITOS):0{DIGITOS}d}"
        pasos = {int(b) - int(a) for a, b in zip(pin, pin[1:])}
        if len(set(pin)) >= 3 and pasos not in ({1}, {-1}):  # nada de 111111 ni 123456
            return pin


def _base_usuario(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    partes = re.findall(r"[a-z0-9]+", texto)
    return (".".join(partes[:2]) if partes else "usuario")[:30]


def _publica(p: dict) -> dict:
    return {k: p.get(k) for k in ("usuario", "nombre", "rol", "activo", "creado", "creado_por", "actualizado")}


def _leer_persona(usuario: str) -> dict | None:
    return almacen.leer_json(f"equipo:{usuario}")


def _guardar_persona(p: dict) -> None:
    almacen.escribir_json(f"equipo:{p['usuario']}", p)
    with _candado:
        _cache_equipo.pop(p["usuario"], None)


def crear_persona(nombre: str, rol: str, creado_por: str | None) -> tuple[dict, str]:
    if rol not in ROLES_EQUIPO:
        raise ErrorLlave(422, "El rol debe ser asesor o supervisor.", "rol")
    nombre = cuentas.validar_nombre(nombre)
    base, pin = _base_usuario(nombre), _pin_nuevo()
    ahora = _ahora()
    for n in range(1, 200):
        usuario = base if n == 1 else f"{base}{n}"
        persona = {"usuario": usuario, "nombre": nombre, "rol": rol, "activo": True, "hash": cuentas.hashear(pin),
                   "version": 1, "creado": ahora, "creado_por": creado_por, "actualizado": ahora}
        if almacen.escribir_json(f"equipo:{usuario}", persona, solo_si_no_existe=True):
            return _publica(persona), pin
    raise ErrorLlave(409, "No se pudo crear un usuario único para ese nombre.")


def listar_equipo() -> list[dict]:
    personas = [almacen.leer_json(k) for k in almacen.claves("equipo:")]
    return sorted((_publica(p) for p in personas if p), key=lambda p: (p["creado"] or "", p["usuario"]))


def _persona(usuario: str) -> dict:
    p = _leer_persona(usuario.strip().lower())
    if not p:
        raise ErrorLlave(404, "No existe ese usuario.")
    return p


def nuevo_pin(usuario: str) -> tuple[dict, str]:
    p = _persona(usuario)
    pin = _pin_nuevo()
    p.update(hash=cuentas.hashear(pin), version=int(p["version"]) + 1, actualizado=_ahora())
    _guardar_persona(p)
    _acierto(f"personal:{p['usuario']}")
    return _publica(p), pin


def cambiar_estado(usuario: str, activo: bool, quien: str | None) -> dict:
    p = _persona(usuario)
    if not activo and quien and quien == p["usuario"]:
        raise ErrorLlave(409, "No puedes desactivar tu propio acceso.")
    if bool(p["activo"]) != activo:
        p.update(activo=activo, version=int(p["version"]) + 1, actualizado=_ahora())
        _guardar_persona(p)
    return _publica(p)


def entrar_personal(usuario: str, pin: str, rol: str | None = None) -> tuple[str, dict]:
    """(rol, datos para el token) de un asesor o supervisor que entra con su usuario y PIN."""
    usuario = (usuario or "").strip().lower()
    clave = f"personal:{usuario}"
    _revisar_bloqueo(clave)
    p = _leer_persona(usuario) if _RE_USUARIO.match(usuario) else None
    if p is None or not cuentas.verificar(re.sub(r"\s", "", pin or ""), p["hash"]):
        if p is None:
            cuentas.verificar(pin or "", cuentas._HASH_SENUELO)  # mismo tiempo de respuesta exista o no
        _fallo(clave)
        raise ErrorLlave(401, "Usuario o PIN incorrecto.", "pin")
    if not p["activo"]:
        raise ErrorLlave(403, "Tu acceso está desactivado. Habla con tu supervisor.")
    if rol and p["rol"] != rol:
        raise ErrorLlave(403, f"Tu usuario es de {p['rol']}. Entra desde la app de {p['rol']}.")
    _acierto(clave)
    return p["rol"], {"usuario": p["usuario"], "nombre": p["nombre"], "v": int(p["version"])}


def persona_vigente(usuario: str, version) -> bool:
    ahora = time.time()
    with _candado:
        guardado = _cache_equipo.get(usuario)
    if guardado is None or ahora - guardado[0] > CACHE_EQUIPO_S:
        p = _leer_persona(usuario)
        guardado = (ahora, p)
        with _candado:
            _cache_equipo[usuario] = guardado
    p = guardado[1]
    return bool(p and p["activo"] and int(p["version"]) == int(version or 0))


# ---------------------------------------------------------------- autorización de cada solicitud

def _ruta_del_prestamo(ruta: str, metodo: str, lid: int) -> bool:
    if ruta == "/cliente/el-nino":
        return metodo == "GET"
    m = _RE_PRESTAMO.match(ruta) or (_RE_FINERACT.match(ruta) if metodo == "GET" else None)
    return bool(m) and int(m.group(1)) == lid


def revisar(datos: dict, ruta: str, metodo: str) -> tuple[int, str] | None:
    """None si la sesión puede hacer la solicitud; si no, (código HTTP, motivo)."""
    if datos.get("usuario"):
        if persona_vigente(datos["usuario"], datos.get("v")):
            return None
        return 401, "Tu acceso cambió o fue desactivado. Vuelve a ingresar con tu usuario y PIN."
    general = datos.get("id") is None and datos.get("prestamo") is None
    if general and not pin_general_activo():
        return 401, "El PIN general está desactivado. Entra con tu llave personal."
    if datos.get("rol") != "cliente" or general:
        return None
    lid = datos.get("prestamo")
    if lid is None:  # cuenta de cliente que aún no vincula su préstamo
        if ruta == "/cliente/el-nino" and metodo == "GET":
            return None
        return 403, "Vincula tu préstamo con el código que te dio tu asesor para verlo."
    p = _db()["loans"].get(int(lid))
    if p is None or p.get("llaveUid") != datos.get("llave") or (
            "v" in datos and int(p.get("llaveVersion", 1)) != int(datos["v"])):
        return 401, "Tu código ya no es válido. Pide uno nuevo a tu asesor."
    if _ruta_del_prestamo(ruta, metodo, int(lid)):
        return None
    return 403, "Con tu código solo puedes ver tu propio préstamo."


def olvidar_intentos() -> None:
    """Solo para pruebas."""
    with _candado:
        _fallidos.clear()
        _cache_equipo.clear()
