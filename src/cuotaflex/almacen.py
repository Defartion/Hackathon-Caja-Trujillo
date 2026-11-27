"""Almacén clave-valor para lo que debe sobrevivir a un reinicio (fase 4: llaves personales).

Elige el backend en este orden:
  1. Upstash Redis por REST, si hay credenciales: UPSTASH_REDIS_REST_URL/_TOKEN o KV_REST_API_URL/_TOKEN
     (los nombres que Vercel agrega al conectar Upstash desde su pestaña Storage). Es el que dura en Vercel.
  2. SQLite (tabla `kv` en CUOTAFLEX_DB) si la persistencia está activa: local y Docker.
  3. Memoria del proceso (pruebas o CUOTAFLEX_PERSISTENCIA=0).

`duradero()` dice si lo guardado sobrevive a un reinicio. En Vercel sin Upstash, SQLite vive en /tmp y se
pierde cuando la función se recicla: por eso ahí no cuenta como duradero.
Las claves llevan el prefijo `thinku:` para no chocar si la base se comparte con otra cosa.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading

import httpx

from . import persistencia

PREFIJO = "thinku:"
_candado = threading.Lock()
_memoria: dict[str, str] = {}
_cliente_http: httpx.Client | None = None  # las pruebas inyectan un transporte falso


class ErrorAlmacen(RuntimeError):
    """El almacén remoto no respondió o rechazó la operación."""


# ---------------------------------------------------------------- qué backend usar

def _credenciales() -> tuple[str, str] | None:
    url = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN")
    return (url.rstrip("/"), token) if url and token else None


def tipo() -> str:
    if _credenciales():
        return "upstash"
    return "sqlite" if persistencia.activa() else "memoria"


def remoto() -> bool:
    return tipo() == "upstash"


def duradero() -> bool:
    t = tipo()
    return t == "upstash" or (t == "sqlite" and not os.getenv("VERCEL"))


def estado() -> dict:
    """Para /auth/config y la pantalla Equipo."""
    return {"tipo": tipo(), "duradero": duradero()}


# ---------------------------------------------------------------- Upstash (REST)

def _redis(*comando):
    url, token = _credenciales()  # type: ignore[misc]
    cliente = _cliente_http or httpx
    try:
        r = cliente.post(url, json=[str(c) for c in comando], headers={"Authorization": f"Bearer {token}"},
                         timeout=8)
    except httpx.HTTPError as e:
        raise ErrorAlmacen(f"No se pudo conectar con Upstash: {e}") from e
    try:
        datos = r.json()
    except ValueError:
        datos = {}
    if r.status_code >= 400 or "error" in datos:
        raise ErrorAlmacen(f"Upstash respondió {r.status_code}: {datos.get('error', r.text[:200])}")
    return datos.get("result")


# ---------------------------------------------------------------- SQLite

def _conectar() -> sqlite3.Connection:
    ruta = persistencia.ruta_db()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS kv (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
    return con


# ---------------------------------------------------------------- operaciones

def leer(clave: str) -> str | None:
    k = PREFIJO + clave
    t = tipo()
    if t == "upstash":
        return _redis("GET", k)
    if t == "sqlite":
        with _candado, _conectar() as con:
            fila = con.execute("SELECT valor FROM kv WHERE clave = ?", (k,)).fetchone()
        return fila[0] if fila else None
    with _candado:
        return _memoria.get(k)


def escribir(clave: str, valor: str, solo_si_no_existe: bool = False) -> bool:
    """Guarda `valor`. Con `solo_si_no_existe`, no pisa una clave existente y devuelve False."""
    k = PREFIJO + clave
    t = tipo()
    if t == "upstash":
        r = _redis("SET", k, valor, "NX") if solo_si_no_existe else _redis("SET", k, valor)
        return r == "OK"
    if t == "sqlite":
        with _candado, _conectar() as con:
            if solo_si_no_existe:
                cur = con.execute("INSERT OR IGNORE INTO kv VALUES (?, ?)", (k, valor))
                return cur.rowcount == 1
            con.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (k, valor))
            return True
    with _candado:
        if solo_si_no_existe and k in _memoria:
            return False
        _memoria[k] = valor
        return True


def borrar(*claves: str) -> None:
    if not claves:
        return
    ks = [PREFIJO + c for c in claves]
    t = tipo()
    if t == "upstash":
        _redis("DEL", *ks)
    elif t == "sqlite":
        with _candado, _conectar() as con:
            con.executemany("DELETE FROM kv WHERE clave = ?", [(k,) for k in ks])
    else:
        with _candado:
            for k in ks:
                _memoria.pop(k, None)


def claves(prefijo: str) -> list[str]:
    """Claves (sin el prefijo global) que empiezan con `prefijo`, ordenadas."""
    base = PREFIJO + prefijo
    t = tipo()
    if t == "upstash":
        encontradas: set[str] = set()
        cursor = "0"
        patron = base.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?").replace("[", "\\[") + "*"
        for _ in range(1000):
            cursor, lote = _redis("SCAN", cursor, "MATCH", patron, "COUNT", 200)
            encontradas.update(lote)
            if str(cursor) == "0":
                break
        todas = encontradas
    elif t == "sqlite":
        with _candado, _conectar() as con:
            todas = {f[0] for f in con.execute("SELECT clave FROM kv WHERE substr(clave, 1, ?) = ?",
                                               (len(base), base))}
    else:
        with _candado:
            todas = {k for k in _memoria if k.startswith(base)}
    return sorted(k[len(PREFIJO):] for k in todas)


def incrementar(clave: str) -> int:
    k = PREFIJO + clave
    t = tipo()
    if t == "upstash":
        return int(_redis("INCR", k))
    if t == "sqlite":
        with _candado, _conectar() as con:
            fila = con.execute("SELECT valor FROM kv WHERE clave = ?", (k,)).fetchone()
            n = int(fila[0]) + 1 if fila else 1
            con.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (k, str(n)))
            return n
    with _candado:
        n = int(_memoria.get(k, "0")) + 1
        _memoria[k] = str(n)
        return n


def leer_json(clave: str):
    v = leer(clave)
    return json.loads(v) if v else None


def escribir_json(clave: str, valor, solo_si_no_existe: bool = False) -> bool:
    return escribir(clave, json.dumps(valor, ensure_ascii=False), solo_si_no_existe)


def vaciar_memoria() -> None:
    """Solo para pruebas: olvida lo guardado en memoria."""
    with _candado:
        _memoria.clear()
