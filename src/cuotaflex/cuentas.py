"""Cuentas de usuario con correo y contraseña (complementan el PIN por rol de la fase 3).

Cada cuenta tiene nombre, correo, rol y la contraseña guardada como hash scrypt con sal propia
(PBKDF2-SHA256 si el Python del servidor no trae scrypt). Nunca se guarda la contraseña.

Dónde viven:
  - Con persistencia activa (CUOTAFLEX_PERSISTENCIA, la de siempre) van en la tabla `cuentas` del mismo
    archivo SQLite que la instantánea del core (CUOTAFLEX_DB). Reiniciar la demo (/admin/reset) no las borra.
  - Sin persistencia (las pruebas) viven en memoria mientras corre la API.

Quién puede crear cuenta (variable CUOTAFLEX_REGISTRO):
  cliente  (por defecto) el cliente se registra solo; asesor y supervisor necesitan el PIN de su rol
           como código de autorización.
  codigo   todos los roles necesitan el PIN de su rol.
  no       no se crean cuentas nuevas (las existentes siguen entrando).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
from datetime import datetime

from . import persistencia

ROLES = ("asesor", "cliente", "supervisor")
MIN_CONTRASENA = 8
MAX_CONTRASENA = 128
MAX_INTENTOS = 5            # intentos fallidos por correo...
VENTANA_INTENTOS_S = 600    # ...dentro de esta ventana antes de bloquear el ingreso

_candado = threading.Lock()
_memoria: dict[str, dict] = {}           # correo -> cuenta (sin persistencia)
_fallidos: dict[str, list[float]] = {}   # correo -> momentos de intentos fallidos
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ErrorCuenta(Exception):
    """Error de negocio con código HTTP y un mensaje listo para mostrar a la persona."""

    def __init__(self, estado: int, mensaje: str, campo: str | None = None):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje
        self.campo = campo


# ---------------------------------------------------------------- política de registro

def politica_registro() -> dict[str, str]:
    """Qué necesita cada rol para crear una cuenta: 'libre', 'codigo' o 'no'."""
    modo = os.getenv("CUOTAFLEX_REGISTRO", "cliente").strip().lower()
    if modo in ("0", "no", "cerrado", "ninguno"):
        return {r: "no" for r in ROLES}
    if modo == "codigo":
        return {r: "codigo" for r in ROLES}
    return {"asesor": "codigo", "cliente": "libre", "supervisor": "codigo"}


# ---------------------------------------------------------------- validación

def normalizar_correo(correo: str) -> str:
    return unicodedata.normalize("NFKC", correo or "").strip().lower()


def validar_nombre(nombre: str) -> str:
    limpio = " ".join(unicodedata.normalize("NFKC", nombre or "").split())
    if len(limpio) < 3 or sum(c.isalpha() for c in limpio) < 2:
        raise ErrorCuenta(400, "Escribe tu nombre completo.", "nombre")
    if len(limpio) > 80:
        raise ErrorCuenta(400, "El nombre puede tener hasta 80 caracteres.", "nombre")
    return limpio


def validar_correo(correo: str) -> str:
    limpio = normalizar_correo(correo)
    if not _RE_CORREO.match(limpio) or len(limpio) > 120:
        raise ErrorCuenta(400, "Escribe un correo válido, por ejemplo nombre@correo.com.", "correo")
    return limpio


def validar_contrasena(contrasena: str) -> str:
    c = contrasena or ""
    if len(c) < MIN_CONTRASENA:
        raise ErrorCuenta(400, f"La contraseña necesita al menos {MIN_CONTRASENA} caracteres.", "contrasena")
    if len(c) > MAX_CONTRASENA:
        raise ErrorCuenta(400, f"La contraseña puede tener hasta {MAX_CONTRASENA} caracteres.", "contrasena")
    if not any(x.isalpha() for x in c) or not any(x.isdigit() for x in c):
        raise ErrorCuenta(400, "Usa letras y números en la contraseña.", "contrasena")
    return c


# ---------------------------------------------------------------- hash de contraseñas

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hashear(contrasena: str) -> str:
    sal = secrets.token_bytes(16)
    try:
        h = hashlib.scrypt(contrasena.encode(), salt=sal, n=2**14, r=8, p=1, dklen=32)
        return f"scrypt$16384$8$1${_b64(sal)}${_b64(h)}"
    except (AttributeError, ValueError):  # OpenSSL sin scrypt
        h = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal, 310_000)
        return f"pbkdf2$310000${_b64(sal)}${_b64(h)}"


def verificar(contrasena: str, guardado: str) -> bool:
    try:
        partes = guardado.split("$")
        if partes[0] == "scrypt":
            n, r, p, sal, h = int(partes[1]), int(partes[2]), int(partes[3]), _unb64(partes[4]), _unb64(partes[5])
            calc = hashlib.scrypt(contrasena.encode(), salt=sal, n=n, r=r, p=p, dklen=len(h))
        elif partes[0] == "pbkdf2":
            it, sal, h = int(partes[1]), _unb64(partes[2]), _unb64(partes[3])
            calc = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal, it)
        else:
            return False
        return hmac.compare_digest(calc, h)
    except Exception:
        return False


# Hash fijo para comparar aunque el correo no exista (mismo tiempo de respuesta).
_HASH_SENUELO = hashear(secrets.token_hex(12))


# ---------------------------------------------------------------- almacenamiento

def _conectar() -> sqlite3.Connection:
    ruta = persistencia.ruta_db()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS cuentas (id INTEGER PRIMARY KEY AUTOINCREMENT, correo TEXT UNIQUE NOT NULL, "
                "nombre TEXT NOT NULL, rol TEXT NOT NULL, hash TEXT NOT NULL, creado TEXT NOT NULL)")
    return con


def _fila_a_cuenta(fila) -> dict:
    i, correo, nombre, rol, h, creado = fila
    return {"id": int(i), "correo": correo, "nombre": nombre, "rol": rol, "hash": h, "creado": creado}


def buscar(correo: str) -> dict | None:
    correo = normalizar_correo(correo)
    if persistencia.activa():
        with _candado, _conectar() as con:
            fila = con.execute("SELECT id, correo, nombre, rol, hash, creado FROM cuentas WHERE correo = ?",
                               (correo,)).fetchone()
        return _fila_a_cuenta(fila) if fila else None
    with _candado:
        c = _memoria.get(correo)
        return dict(c) if c else None


def _guardar_nueva(correo: str, nombre: str, rol: str, h: str) -> dict:
    creado = datetime.now().isoformat(timespec="seconds")
    if persistencia.activa():
        try:
            with _candado, _conectar() as con:
                cur = con.execute("INSERT INTO cuentas (correo, nombre, rol, hash, creado) VALUES (?, ?, ?, ?, ?)",
                                  (correo, nombre, rol, h, creado))
                return {"id": int(cur.lastrowid), "correo": correo, "nombre": nombre, "rol": rol, "hash": h,
                        "creado": creado}
        except sqlite3.IntegrityError:
            raise ErrorCuenta(409, "Ya existe una cuenta con ese correo. Ingresa con tu contraseña.", "correo")
    with _candado:
        if correo in _memoria:
            raise ErrorCuenta(409, "Ya existe una cuenta con ese correo. Ingresa con tu contraseña.", "correo")
        cuenta = {"id": len(_memoria) + 1, "correo": correo, "nombre": nombre, "rol": rol, "hash": h, "creado": creado}
        _memoria[correo] = cuenta
        return dict(cuenta)


def publica(cuenta: dict) -> dict:
    """Lo que se puede devolver al navegador (nunca el hash)."""
    return {k: cuenta[k] for k in ("id", "nombre", "correo", "rol")}


# ---------------------------------------------------------------- casos de uso

def registrar(rol: str, nombre: str, correo: str, contrasena: str, codigo: str | None, pin_del_rol: str) -> dict:
    """Crea la cuenta y la devuelve (sin hash). `pin_del_rol` es el PIN vigente del rol pedido."""
    if rol not in ROLES:
        raise ErrorCuenta(400, "Rol no válido.", "rol")
    regla = politica_registro()[rol]
    if regla == "no":
        raise ErrorCuenta(403, "La creación de cuentas está desactivada. Ingresa con el PIN de tu rol.")
    nombre = validar_nombre(nombre)
    correo = validar_correo(correo)
    contrasena = validar_contrasena(contrasena)
    if regla == "codigo" and not hmac.compare_digest((codigo or "").strip(), pin_del_rol):
        raise ErrorCuenta(403, f"El código de autorización no es correcto. Es el PIN de {rol} que te dio tu equipo.",
                          "codigo")
    return publica(_guardar_nueva(correo, nombre, rol, hashear(contrasena)))


def _bloqueado(correo: str, ahora: float) -> bool:
    with _candado:
        recientes = [t for t in _fallidos.get(correo, []) if ahora - t < VENTANA_INTENTOS_S]
        _fallidos[correo] = recientes
        return len(recientes) >= MAX_INTENTOS


def ingresar(correo: str, contrasena: str, rol: str | None = None) -> dict:
    """Valida correo y contraseña y devuelve la cuenta (sin hash)."""
    correo = normalizar_correo(correo)
    ahora = time.time()
    if _bloqueado(correo, ahora):
        raise ErrorCuenta(429, "Demasiados intentos fallidos. Espera 10 minutos o entra con el PIN de tu rol.")
    cuenta = buscar(correo) if correo else None
    if not verificar(contrasena or "", cuenta["hash"] if cuenta else _HASH_SENUELO) or not cuenta:
        with _candado:
            _fallidos.setdefault(correo, []).append(ahora)
        raise ErrorCuenta(401, "Correo o contraseña incorrectos.")
    with _candado:
        _fallidos.pop(correo, None)
    if rol and cuenta["rol"] != rol:
        raise ErrorCuenta(403, f"Esta cuenta es de {cuenta['rol']}. Entra desde la app de {cuenta['rol']}.")
    return publica(cuenta)


def borrar_todo() -> None:
    """Solo para pruebas: vacía las cuentas y los intentos fallidos."""
    with _candado:
        _memoria.clear()
        _fallidos.clear()
    if persistencia.activa() and persistencia.ruta_db().exists():
        with _candado, _conectar() as con:
            con.execute("DELETE FROM cuentas")
