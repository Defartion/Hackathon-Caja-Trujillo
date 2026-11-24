"""Persistencia por instantánea del core simulado (fase 3).

Los routers usan `api.main.DB` como dicts y modifican los préstamos en sitio. En lugar de cambiar esa
interfaz, después de cada escritura exitosa se guarda una instantánea completa en SQLite, y al iniciar
la API se vuelve a cargar. Con decenas o cientos de préstamos es instantáneo.

Variables de entorno:
  CUOTAFLEX_PERSISTENCIA=0  la desactiva (las pruebas la desactivan por defecto)
  CUOTAFLEX_DB              ruta del archivo SQLite (por defecto data/cuotaflex.db)
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
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


def guardar(db: dict[str, dict], siguiente_id: int) -> None:
    """Escribe la instantánea completa en una transacción."""
    ahora = datetime.now().isoformat(timespec="seconds")
    filas = [(t, int(i), json.dumps(e, default=_a_json, ensure_ascii=False), ahora)
             for t in TIPOS for i, e in db.get(t, {}).items()]
    with _candado, _conectar() as con:
        con.execute("DELETE FROM entidades")
        con.executemany("INSERT INTO entidades VALUES (?, ?, ?, ?)", filas)
        con.execute("INSERT OR REPLACE INTO meta VALUES ('siguiente_id', ?)", (str(siguiente_id),))


def cargar(db: dict[str, dict]) -> int:
    """Llena `db` desde SQLite y devuelve el siguiente ID a usar (1 si no hay datos)."""
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
    with _candado:
        if ruta_db().exists():
            with _conectar() as con:
                con.execute("DELETE FROM entidades")
                con.execute("DELETE FROM meta")
