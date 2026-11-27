"""Persistencia por instantánea del core simulado (fase 3).

Los routers usan `api.main.DB` como dicts y modifican los préstamos en sitio. En lugar de cambiar esa
interfaz, después de cada escritura exitosa se guarda una instantánea completa en SQLite, y al iniciar
la API se vuelve a cargar. Con decenas o cientos de préstamos es instantáneo.

Variables de entorno:
  CUOTAFLEX_PERSISTENCIA=0  la desactiva (las pruebas la desactivan por defecto)
  CUOTAFLEX_DB              ruta del archivo SQLite (por defecto data/cuotaflex.db)
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import threading
import zlib
from datetime import date, datetime
from pathlib import Path

import numpy as np

from .config import RAIZ

_candado = threading.Lock()
TIPOS = ("clients", "loans")


def activa() -> bool:
    return os.getenv("CUOTAFLEX_PERSISTENCIA", "1").strip() != "0"


def ruta_db() -> Path:
    return Path(os.getenv("CUOTAFLEX_DB", str(RAIZ / "data" / "cuotaflex.db")))


def _a_json(x):
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (date, datetime)):
        return x.isoformat()
    raise TypeError(f"no serializable: {type(x).__name__}")


def _conectar() -> sqlite3.Connection:
    ruta = ruta_db()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS entidades (tipo TEXT, id INTEGER, json TEXT, actualizado TEXT, "
                "PRIMARY KEY (tipo, id))")
    con.execute("CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT)")
    return con


# ------------------------------------------------- Upstash (fase 4): la instantánea dura también en Vercel

_CLAVE_REMOTA = "core:instantanea"
_CLAVE_VERSION = "core:version"
_version_local: str | None = None


def _remota() -> bool:
    from . import almacen  # import tardío: almacen usa este módulo

    return almacen.remoto()


def _guardar_remota(db: dict[str, dict], siguiente_id: int) -> None:
    global _version_local
    from . import almacen

    datos = {"siguiente_id": int(siguiente_id),
             "entidades": {t: {str(i): e for i, e in db.get(t, {}).items()} for t in TIPOS}}
    crudo = json.dumps(datos, default=_a_json, ensure_ascii=False).encode()
    almacen.escribir(_CLAVE_REMOTA, base64.b64encode(zlib.compress(crudo, 6)).decode())
    _version_local = str(almacen.incrementar(_CLAVE_VERSION))


def _cargar_remota(db: dict[str, dict]) -> int:
    global _version_local
    from . import almacen

    _version_local = almacen.leer(_CLAVE_VERSION)
    texto = almacen.leer(_CLAVE_REMOTA)
    for t in TIPOS:
        db.setdefault(t, {}).clear()
    if not texto:
        return 1
    datos = json.loads(zlib.decompress(base64.b64decode(texto)))
    for t in TIPOS:
        for i, e in datos["entidades"].get(t, {}).items():
            db[t][int(i)] = e
    maximo = max([i for t in TIPOS for i in db[t]] + [0])
    return max(int(datos.get("siguiente_id", 1)), maximo + 1)


def desactualizada() -> bool:
    """True si otra instancia guardó una versión más nueva en Upstash (hay que recargar)."""
    if not (activa() and _remota()):
        return False
    from . import almacen

    try:
        return almacen.leer(_CLAVE_VERSION) != _version_local
    except almacen.ErrorAlmacen as e:  # Upstash caído: se sigue con lo que hay en memoria
        print(f"[persistencia] no se pudo revisar la versión en Upstash: {e}")
        return False


def guardar(db: dict[str, dict], siguiente_id: int) -> None:
    """Escribe la instantánea completa en una transacción."""
    if _remota():
        with _candado:
            _guardar_remota(db, siguiente_id)
        return
    ahora = datetime.now().isoformat(timespec="seconds")
    filas = [(t, int(i), json.dumps(e, default=_a_json, ensure_ascii=False), ahora)
             for t in TIPOS for i, e in db.get(t, {}).items()]
    with _candado, _conectar() as con:
        con.execute("DELETE FROM entidades")
        con.executemany("INSERT INTO entidades VALUES (?, ?, ?, ?)", filas)
        con.execute("INSERT OR REPLACE INTO meta VALUES ('siguiente_id', ?)", (str(siguiente_id),))


def cargar(db: dict[str, dict]) -> int:
    """Llena `db` desde SQLite y devuelve el siguiente ID a usar (1 si no hay datos)."""
    if _remota():
        with _candado:
            return _cargar_remota(db)
    if not ruta_db().exists():
        return 1
    with _candado, _conectar() as con:
        filas = con.execute("SELECT tipo, id, json FROM entidades").fetchall()
        meta = dict(con.execute("SELECT clave, valor FROM meta").fetchall())
    for t in TIPOS:
        db.setdefault(t, {}).clear()
    for tipo, i, js in filas:
        db.setdefault(tipo, {})[int(i)] = json.loads(js)
    maximo = max([i for t in TIPOS for i in db[t]] + [0])
    return max(int(meta.get("siguiente_id", 1)), maximo + 1)


def borrar() -> None:
    if _remota():
        global _version_local
        from . import almacen

        with _candado:
            almacen.borrar(_CLAVE_REMOTA)
            _version_local = str(almacen.incrementar(_CLAVE_VERSION))
        return
    with _candado:
        if ruta_db().exists():
            with _conectar() as con:
                con.execute("DELETE FROM entidades")
                con.execute("DELETE FROM meta")
