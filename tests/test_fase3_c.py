"""Fase 3 · Lote C: verificador del entorno de la final (scripts/verificar_entorno.*).

Las comprobaciones reciben sus dependencias (ejecutar comandos, buscar programas, puertos, disco), así
que aquí se prueban con mocks y no dependen de lo que tenga instalado la máquina.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("verificar_entorno", RAIZ / "scripts" / "verificar_entorno.py")
ve = importlib.util.module_from_spec(_spec)
sys.modules["verificar_entorno"] = ve  # dataclasses necesita el módulo registrado
_spec.loader.exec_module(ve)


def proceso(codigo: int = 0, salida: str = "", error: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], codigo, salida, error)


def buscador(*disponibles: str):
    return lambda nombre: f"/bin/{nombre}" if nombre in disponibles else None


# ---------------------------------------------------------------- utilidades

def test_lee_versiones_y_las_compara():
    assert ve.version_de("v22.19.0") == (22, 19, 0)
    assert ve.version_de("Python 3.12.10") == (3, 12, 10)
    assert ve.version_de("Docker version 29.6.1, build 8900f1d") == (29, 6, 1)
    assert ve.version_de("sin versión") is None
    assert ve.cumple((3, 12, 1), (3, 10)) and ve.cumple((3, 10), (3, 10))
    assert not ve.cumple((3, 9, 18), (3, 10)) and not ve.cumple(None, (3, 10))


def test_lee_requirements_sin_comentarios_ni_opcionales(tmp_path):
    archivo = tmp_path / "requirements.txt"
    archivo.write_text("numpy>=1.26\npypdf>=5.0           # ENFEN\n\n# opcionales\n# sdv>=1.12\nhttpx\n",
                       encoding="utf-8")
    assert ve.requisitos(archivo) == [("numpy", "1.26"), ("pypdf", "5.0"), ("httpx", "")]


# ---------------------------------------------------------------- comprobaciones

@pytest.mark.parametrize(("version", "ejecutable", "estado"), [
    ((3, 9, 18), "/repo/.venv/bin/python", "falla"),
    ((3, 12, 10), "/repo/.venv/bin/python", "ok"),
    ((3, 12, 10), r"C:\repo\.venv\Scripts\python.exe", "ok"),
    ((3, 12, 10), "/usr/bin/python3", "aviso"),  # funciona, pero fuera del entorno del proyecto
])
def test_python(version, ejecutable, estado):
    assert ve.revisar_python(version, ejecutable).estado == estado


def test_node_falta_viejo_o_listo():
    assert ve.revisar_node(buscador()).estado == "falla"
    viejo = ve.revisar_node(buscador("node", "npm"), lambda *a, **k: proceso(salida="v16.20.2"))
    assert viejo.estado == "falla" and "16.20.2" in viejo.detalle
    sin_npm = ve.revisar_node(buscador("node"), lambda *a, **k: proceso(salida="v22.19.0"))
    assert sin_npm.estado == "falla" and "npm" in sin_npm.detalle
    listo = ve.revisar_node(buscador("node", "npm"), lambda *a, **k: proceso(salida="v22.19.0\n"))
    assert (listo.estado, listo.detalle) == ("ok", "Node 22.19.0 y npm")


def test_dependencias_de_python(tmp_path):
    archivo = tmp_path / "requirements.txt"
    archivo.write_text("numpy>=1.26\npypdf>=5.0\nfastapi>=0.110\n", encoding="utf-8")
    instaladas = {"numpy": "2.1.0", "pypdf": "4.3.1"}
    resultado = ve.revisar_dependencias_python(archivo, instaladas.get)
    assert resultado.estado == "falla"
    assert "faltan fastapi" in resultado.detalle and "pypdf 4.3.1 < 5.0" in resultado.detalle
    instaladas.update(pypdf="7.1.1", fastapi="0.165.0")
    assert ve.revisar_dependencias_python(archivo, instaladas.get).estado == "ok"


def test_dependencias_de_las_apps(tmp_path):
    for app, deps in {"cliente": ["react", "vite"], "tablero": ["recharts"]}.items():
        carpeta = tmp_path / "web" / app
        carpeta.mkdir(parents=True)
        (carpeta / "package.json").write_text(json.dumps({"dependencies": {deps[0]: "^1"},
                                                          "devDependencies": {d: "^1" for d in deps[1:]}}))
    (tmp_path / "web" / "cliente" / "node_modules" / "react").mkdir(parents=True)
    (tmp_path / "web" / "cliente" / "node_modules" / "react" / "package.json").write_text("{}")
    resultado = ve.revisar_dependencias_node(tmp_path, ("cliente", "tablero"))
    assert resultado.estado == "falla"
    assert "cliente: faltan vite" in resultado.detalle and "tablero: sin node_modules" in resultado.detalle

    for app, nombre in (("cliente", "vite"), ("tablero", "recharts")):
        modulo = tmp_path / "web" / app / "node_modules" / nombre
        modulo.mkdir(parents=True)
        (modulo / "package.json").write_text("{}")
    assert ve.revisar_dependencias_node(tmp_path, ("cliente", "tablero")).estado == "ok"


def test_puertos_ocupados_se_informan_en_rojo():
    resultado = ve.revisar_puertos(ocupado=lambda puerto: puerto in (8000, 5174))
    assert resultado.estado == "falla"
    assert "8000 (API)" in resultado.detalle and "5174 (cliente)" in resultado.detalle
    assert ve.revisar_puertos(ocupado=lambda puerto: False).estado == "ok"


def test_detecta_un_puerto_que_esta_escuchando():
    with socket.socket() as servidor:  # puerto libre que asigna el sistema, solo en localhost
        servidor.bind(("127.0.0.1", 0))
        servidor.listen()
        assert ve.puerto_ocupado(servidor.getsockname()[1])


def test_docker_es_opcional():
    assert ve.revisar_docker(buscador()).estado == "aviso"
    apagado = ve.revisar_docker(buscador("docker"), lambda cmd, **k: proceso(1 if "info" in cmd else 0, "Docker version 29.6.1"))
    assert apagado.estado == "aviso" and "no está corriendo" in apagado.detalle
    listo = ve.revisar_docker(buscador("docker"), lambda cmd, **k: proceso(0, "Docker version 29.6.1, build x"))
    assert (listo.estado, listo.detalle) == ("ok", "Docker 29.6.1 corriendo")


@pytest.mark.parametrize(("libre_gb", "estado"), [(0.5, "falla"), (2, "aviso"), (50, "ok")])
def test_espacio_en_disco(libre_gb, estado):
    uso = lambda _ruta: shutil._ntuple_diskusage(100 * 1024**3, 0, int(libre_gb * 1024**3))  # noqa: E731
    assert ve.revisar_disco(Path("."), uso).estado == estado


def test_pytest_rapido_y_completo():
    comandos = []

    def correr(comando, **kwargs):
        comandos.append(comando)
        return proceso(0, "89 passed, 1 skipped in 9.64s\n")

    rapido = ve.revisar_pytest(correr=correr, python="python")
    assert rapido.estado == "ok" and "89 passed" in rapido.detalle
    assert "--ignore=tests/test_fase2_a.py" in comandos[0] and "not e2e and not fineract" in comandos[0]
    ve.revisar_pytest(completo=True, correr=correr, python="python")
    assert comandos[1] == ["python", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"]

    falla = ve.revisar_pytest(correr=lambda *a, **k: proceso(1, "FAILED tests/test_x.py::test_y\n1 failed"))
    assert falla.estado == "falla" and "1 failed" in falla.detalle


def test_compila_cada_app_con_npm(tmp_path):
    carpetas = []

    def correr(comando, cwd=None, **kwargs):
        carpetas.append((comando[1:], Path(cwd).name))
        return proceso(1, "", "error TS2322: tipo inválido") if Path(cwd).name == "cliente" else proceso()

    assert ve.revisar_compilacion(tmp_path, buscar=buscador()).estado == "falla"  # sin npm
    resultado = ve.revisar_compilacion(tmp_path, buscar=buscador("npm"), correr=correr)
    assert carpetas == [(["run", "build"], app) for app in ve.APPS]
    assert resultado.estado == "falla" and "cliente" in resultado.detalle and "TS2322" in resultado.detalle
    ok = ve.revisar_compilacion(tmp_path, buscar=buscador("npm"), correr=lambda *a, **k: proceso())
    assert ok.estado == "ok"


# ---------------------------------------------------------------- informe y opciones

def test_el_informe_resume_en_verde_o_rojo(capsys):
    verde = [lambda: ve.Resultado("Python", "ok", "3.12"), lambda: ve.Resultado("Docker", "aviso", "apagado")]
    assert ve.main([], lista=verde) == 0
    assert "laptop lista para la final (1 aviso(s))" in capsys.readouterr().out

    def rota():
        raise RuntimeError("se cayó")

    rojo = [lambda: ve.Resultado("Node", "falla", "no está instalado", "Instala Node"), rota]
    assert ve.main([], lista=rojo) == 1
    salida = capsys.readouterr().out
    assert "[FALLA] Node: no está instalado" in salida and "Instala Node" in salida
    assert "error inesperado: se cayó" in salida and "faltan 2 cosa(s)" in salida


@pytest.mark.parametrize(("argumentos", "con_pytest", "con_compilacion"), [
    ([], True, True),
    (["--rapido"], False, False),
    (["--sin-compilar"], True, False),
    (["--sin-pruebas"], False, True),
])
def test_opciones_eligen_las_comprobaciones(argumentos, con_pytest, con_compilacion):
    import argparse

    args = argparse.Namespace(rapido="--rapido" in argumentos, completo=False,
                              sin_pruebas="--sin-pruebas" in argumentos, sin_compilar="--sin-compilar" in argumentos)
    lista = ve.comprobaciones(args)
    assert len(lista) == 7 + con_pytest + con_compilacion
    assert (ve.revisar_compilacion in lista) is con_compilacion


def test_los_lanzadores_buscan_el_venv_y_pasan_los_argumentos():
    sh = (RAIZ / "scripts" / "verificar_entorno.sh").read_text(encoding="utf-8")
    assert sh.startswith("#!/usr/bin/env bash")
    assert sh.index(".venv/bin/python") < sh.index("python3")  # primero el entorno del proyecto
    assert 'verificar_entorno.py" "$@"' in sh
    ps1 = (RAIZ / "scripts" / "verificar_entorno.ps1").read_bytes()
    assert ps1.startswith(b"\xef\xbb\xbf")  # UTF-8 con BOM: PowerShell 5.1 lee bien las tildes
    texto = ps1.decode("utf-8-sig")
    assert ".venv\\Scripts\\python.exe" in texto and "verificar_entorno.py" in texto
    assert all(f"'{opcion}'" in texto for opcion in ("--rapido", "--completo", "--sin-pruebas", "--sin-compilar"))


# ---------------------------------------------------------------- lanzadores reales (se omiten sin intérprete)

def _bash() -> str | None:
    ruta = shutil.which("bash")
    if ruta and os.name == "nt" and "system32" in ruta.lower():  # en Windows ese es el de WSL: se usa Git Bash
        git = shutil.which("git")
        candidato = Path(git).resolve().parents[1] / "bin" / "bash.exe" if git else None
        return str(candidato) if candidato and candidato.exists() else None
    return ruta


@pytest.mark.skipif(_bash() is None, reason="sin bash")
def test_el_lanzador_bash_responde():
    proceso_sh = subprocess.run([_bash(), str(RAIZ / "scripts" / "verificar_entorno.sh"), "--help"],
                                capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert proceso_sh.returncode == 0, proceso_sh.stderr
    assert "--rapido" in proceso_sh.stdout


@pytest.mark.skipif(shutil.which("powershell") is None and shutil.which("pwsh") is None, reason="sin PowerShell")
def test_el_lanzador_powershell_responde():
    shell = shutil.which("powershell") or shutil.which("pwsh")
    proceso_ps = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                 str(RAIZ / "scripts" / "verificar_entorno.ps1"), "-Ayuda"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert proceso_ps.returncode == 0, proceso_ps.stderr
    assert "--rapido" in proceso_ps.stdout
