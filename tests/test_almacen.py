"""Almacén duradero (fase 4): Upstash por REST con un Redis falso, SQLite y memoria."""
from __future__ import annotations

import json

import httpx
import pytest

from cuotaflex import almacen, cuentas, persistencia


class RedisFalso:
    """Imita la API REST de Upstash: POST con el comando como arreglo JSON → {"result": ...}."""

    def __init__(self):
        self.datos: dict[str, str] = {}
        self.comandos: list[list[str]] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        if pedido.headers.get("authorization") != "Bearer secreto-falso":
            return httpx.Response(401, json={"error": "Unauthorized"})
        cmd = json.loads(pedido.content)
        self.comandos.append(cmd)
        op, args = cmd[0].upper(), cmd[1:]
        if op == "GET":
            r = self.datos.get(args[0])
        elif op == "SET":
            if len(args) > 2 and args[2].upper() == "NX" and args[0] in self.datos:
                r = None
            else:
                self.datos[args[0]] = args[1]
                r = "OK"
        elif op == "DEL":
            r = sum(self.datos.pop(k, None) is not None for k in args)
        elif op == "INCR":
            self.datos[args[0]] = str(int(self.datos.get(args[0], "0")) + 1)
            r = int(self.datos[args[0]])
        elif op == "SCAN":
            prefijo = args[2][:-1].replace("\\", "")
            r = ["0", [k for k in self.datos if k.startswith(prefijo)]]
        else:
            return httpx.Response(400, json={"error": f"comando no soportado: {op}"})
        return httpx.Response(200, json={"result": r})


@pytest.fixture
def upstash(monkeypatch):
    falso = RedisFalso()
    monkeypatch.setenv("KV_REST_API_URL", "https://falso.upstash.io/")
    monkeypatch.setenv("KV_REST_API_TOKEN", "secreto-falso")
    monkeypatch.setattr(almacen, "_cliente_http", httpx.Client(transport=httpx.MockTransport(falso)))
    yield falso


def _operaciones_basicas():
    assert almacen.leer("x") is None
    assert almacen.escribir("x", "1") is True
    assert almacen.escribir("x", "2", solo_si_no_existe=True) is False
    assert almacen.leer("x") == "1"
    assert almacen.incrementar("n") == 1 and almacen.incrementar("n") == 2
    almacen.escribir_json("equipo:ana", {"nombre": "Ana Ñique"})
    almacen.escribir_json("equipo:luis", {"nombre": "Luis"})
    assert almacen.claves("equipo:") == ["equipo:ana", "equipo:luis"]
    assert almacen.leer_json("equipo:ana") == {"nombre": "Ana Ñique"}
    almacen.borrar("equipo:ana", "x")
    assert almacen.claves("equipo:") == ["equipo:luis"] and almacen.leer("x") is None


def test_upstash(upstash):
    assert almacen.estado() == {"tipo": "upstash", "duradero": True}
    _operaciones_basicas()
    assert all(k.startswith("thinku:") for k in upstash.datos)


def test_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("CUOTAFLEX_PERSISTENCIA", "1")
    monkeypatch.setenv("CUOTAFLEX_DB", str(tmp_path / "kv.db"))
    assert almacen.estado() == {"tipo": "sqlite", "duradero": True}
    _operaciones_basicas()
    monkeypatch.setenv("VERCEL", "1")
    assert almacen.duradero() is False  # en Vercel, SQLite vive en /tmp


def test_memoria():
    almacen.vaciar_memoria()
    assert almacen.estado() == {"tipo": "memoria", "duradero": False}
    _operaciones_basicas()
    almacen.vaciar_memoria()


def test_credenciales_malas_dan_error_claro(upstash, monkeypatch):
    monkeypatch.setenv("KV_REST_API_TOKEN", "otro")
    with pytest.raises(almacen.ErrorAlmacen, match="401"):
        almacen.leer("x")


def test_instantanea_del_core_en_upstash_y_recarga_entre_instancias(upstash, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_PERSISTENCIA", "1")
    db = {"clients": {1: {"id": 1, "nombre": "Rosa"}}, "loans": {2: {"id": 2, "cuotas": [1.5, 2.5]}}}
    persistencia.guardar(db, 3)
    assert not persistencia.desactualizada()
    leido: dict = {}
    assert persistencia.cargar(leido) == 3
    assert leido["loans"][2]["cuotas"] == [1.5, 2.5] and leido["clients"][1]["nombre"] == "Rosa"
    # otra instancia escribe: esta queda desactualizada hasta recargar
    upstash.datos["thinku:core:version"] = "99"
    assert persistencia.desactualizada()
    persistencia.cargar(leido)
    assert not persistencia.desactualizada()
    persistencia.borrar()
    vacio: dict = {}
    assert persistencia.cargar(vacio) == 1 and vacio["loans"] == {}


def test_cuentas_en_upstash(upstash):
    cuentas.borrar_todo()
    c = cuentas.registrar("cliente", "Rosa Quispe", "Rosa@Ejemplo.pe", "arroz2026", None, "2222")
    assert cuentas.buscar("rosa@ejemplo.pe")["id"] == c["id"]
    assert cuentas.por_id(c["id"])["correo"] == "rosa@ejemplo.pe"
    with pytest.raises(cuentas.ErrorCuenta):
        cuentas.registrar("cliente", "Rosa Quispe", "rosa@ejemplo.pe", "arroz2026", None, "2222")
    assert cuentas.ingresar("ROSA@ejemplo.pe", "arroz2026")["id"] == c["id"]
    cuentas.borrar_todo()
    assert cuentas.buscar("rosa@ejemplo.pe") is None
