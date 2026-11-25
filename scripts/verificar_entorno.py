"""¿Está lista esta laptop para la final? Responde en verde o rojo.

Se ejecuta con los lanzadores `scripts/verificar_entorno.sh` (Linux o Mac) y `scripts/verificar_entorno.ps1`
(Windows), que buscan un Python y llaman a este archivo. También funciona directo:

    python scripts/verificar_entorno.py              # todo, con pytest rápido (~20 s) y compilación de las apps
    python scripts/verificar_entorno.py --rapido     # solo lo que no tarda: sin pytest ni compilación
    python scripts/verificar_entorno.py --completo   # con pytest completo (~80 s)

Devuelve 0 si no hay nada en rojo y 1 si falta algo. Las comprobaciones reciben sus dependencias
(ejecutar comandos, buscar programas, puertos, disco) para poder probarlas con mocks: tests/test_fase3_c.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APPS = ("asesor", "cliente", "tablero")
PUERTOS = (8000, 5173, 5174, 5175)  # API, asesor, cliente y tablero
PYTHON_MINIMO = (3, 10)
NODE_MINIMO = (18, 0)
DISCO_MINIMO_GB = 1.0
DISCO_RECOMENDADO_GB = 3.0
# pytest rápido: sin la calibración ni la simulación del tablero (las más lentas), ni e2e ni Fineract.
PYTEST_RAPIDO = ["-m", "not e2e and not fineract", "--ignore=tests/e2e", "--ignore=tests/test_fase2_a.py",
                 "--ignore=tests/test_lote_c_simulacion.py"]

OK, AVISO, FALLA = "ok", "aviso", "falla"
_ETIQUETA = {OK: "[OK]   ", AVISO: "[AVISO]", FALLA: "[FALLA]"}
_COLOR = {OK: "\033[32m", AVISO: "\033[33m", FALLA: "\033[31m"}
_NORMAL = "\033[0m"


@dataclass
class Resultado:
    nombre: str
    estado: str           # ok | aviso | falla
    detalle: str
    ayuda: str = ""       # qué hacer si no está en verde


def version_de(texto: str) -> tuple[int, ...] | None:
    """'v22.19.0' o 'Python 3.12.10' -> (22, 19, 0). None si no hay versión."""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", texto or "")
    return tuple(int(x) for x in m.groups() if x is not None) if m else None


def cumple(version: tuple[int, ...] | None, minima: tuple[int, ...]) -> bool:
    return version is not None and version[:len(minima)] >= minima


def ejecutar(comando: list[str], cwd: Path | None = None, timeout: float = 600) -> subprocess.CompletedProcess:
    """Ejecuta sin shell y nunca lanza: devuelve el código y la salida combinada."""
    try:
        return subprocess.run(comando, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(comando, 127, "", f"No se encontró {comando[0]}")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(comando, 124, "", f"Se agotó el tiempo ({timeout:.0f} s)")
    except OSError as e:
        return subprocess.CompletedProcess(comando, 126, "", str(e))


def _cola(proceso: subprocess.CompletedProcess, lineas: int = 3) -> str:
    texto = "\n".join(x for x in (proceso.stdout, proceso.stderr) if x).strip().splitlines()
    return " | ".join(texto[-lineas:])


# ---------------------------------------------------------------- comprobaciones

def revisar_python(version: tuple[int, ...] | None = None, ejecutable: str | None = None) -> Resultado:
    version = version or tuple(sys.version_info[:3])
    ejecutable = ejecutable or sys.executable
    texto = ".".join(map(str, version))
    en_venv = ".venv" in re.split(r"[\\/]", ejecutable)  # separa rutas de Windows y de Linux/Mac por igual
    lugar = "entorno .venv del proyecto" if en_venv else ejecutable
    if not cumple(version, PYTHON_MINIMO):
        return Resultado("Python", FALLA, f"Python {texto} ({lugar})",
                         f"Instala Python {PYTHON_MINIMO[0]}.{PYTHON_MINIMO[1]} o más y crea el entorno: python -m venv .venv")
    if not en_venv:
        return Resultado("Python", AVISO, f"Python {texto} fuera de .venv ({lugar})",
                         "Recomendado: python -m venv .venv e instalar ahí las dependencias")
    return Resultado("Python", OK, f"Python {texto} ({lugar})")


def revisar_node(buscar=shutil.which, correr=ejecutar) -> Resultado:
    node, npm = buscar("node"), buscar("npm")
    if not node:
        return Resultado("Node", FALLA, "Node no está instalado",
                         f"Instala Node {NODE_MINIMO[0]} LTS o más (https://nodejs.org)")
    version = version_de(correr([node, "--version"], timeout=30).stdout)
    texto = ".".join(map(str, version)) if version else "desconocida"
    if not cumple(version, NODE_MINIMO):
        return Resultado("Node", FALLA, f"Node {texto}", f"Las apps (Vite) necesitan Node {NODE_MINIMO[0]} o más")
    if not npm:
        return Resultado("Node", FALLA, f"Node {texto}, pero falta npm", "Reinstala Node con npm incluido")
    return Resultado("Node", OK, f"Node {texto} y npm")


def requisitos(ruta: Path) -> list[tuple[str, str]]:
    """(nombre, versión mínima) de cada línea activa de requirements.txt."""
    salida = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        m = re.match(r"([A-Za-z0-9_.\-]+)\s*(?:>=\s*([0-9][0-9.]*))?", linea)
        if m:
            salida.append((m.group(1), m.group(2) or ""))
    return salida


def _version_instalada(nombre: str) -> str | None:
    from importlib import metadata

    try:
        return metadata.version(nombre)
    except metadata.PackageNotFoundError:
        return None


def revisar_dependencias_python(ruta: Path | None = None, version_instalada=_version_instalada) -> Resultado:
    ruta = ruta or RAIZ / "requirements.txt"
    faltan, viejas = [], []
    paquetes = requisitos(ruta)
    for nombre, minima in paquetes:
        instalada = version_instalada(nombre)
        if instalada is None:
            faltan.append(nombre)
        elif minima and not cumple(version_de(instalada), version_de(minima) or (0,)):
            viejas.append(f"{nombre} {instalada} < {minima}")
    if faltan or viejas:
        partes = ([f"faltan {', '.join(faltan)}"] if faltan else []) + ([", ".join(viejas)] if viejas else [])
        return Resultado("Dependencias de Python", FALLA, "; ".join(partes),
                         "pip install -r requirements.txt (dentro de .venv)")
    return Resultado("Dependencias de Python", OK, f"{len(paquetes)} paquetes de requirements.txt instalados")


def revisar_dependencias_node(raiz: Path | None = None, apps=APPS) -> Resultado:
    raiz = raiz or RAIZ
    problemas = []
    for app in apps:
        carpeta = raiz / "web" / app
        paquete = json.loads((carpeta / "package.json").read_text(encoding="utf-8"))
        nombres = {**paquete.get("dependencies", {}), **paquete.get("devDependencies", {})}
        faltan = [n for n in nombres if not (carpeta / "node_modules" / n / "package.json").exists()]
        if not (carpeta / "node_modules").is_dir():
            problemas.append(f"{app}: sin node_modules")
        elif faltan:
            problemas.append(f"{app}: faltan {', '.join(sorted(faltan))}")
    if problemas:
        return Resultado("Dependencias de las apps", FALLA, "; ".join(problemas),
                         "En cada carpeta web/<app>: npm ci")
    return Resultado("Dependencias de las apps", OK, f"node_modules completos en {', '.join(apps)}")


def revisar_pytest(completo: bool = False, correr=ejecutar, python: str | None = None) -> Resultado:
    comando = [python or sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"]
    if not completo:
        comando += PYTEST_RAPIDO
    inicio = time.monotonic()
    proceso = correr(comando, cwd=RAIZ, timeout=900)
    segundos = time.monotonic() - inicio
    resumen = _cola(proceso, 1)
    nombre = "pytest completo" if completo else "pytest rápido"
    if proceso.returncode != 0:
        return Resultado(nombre, FALLA, resumen or f"código {proceso.returncode}",
                         "Corre pytest para ver el detalle; no se presenta con pruebas en rojo")
    return Resultado(nombre, OK, f"{resumen} ({segundos:.0f} s)")


def revisar_compilacion(raiz: Path | None = None, apps=APPS, buscar=shutil.which, correr=ejecutar) -> Resultado:
    raiz = raiz or RAIZ
    npm = buscar("npm")
    if not npm:
        return Resultado("Compilación de las apps", FALLA, "npm no está disponible", "Instala Node con npm")
    fallas = []
    for app in apps:
        proceso = correr([npm, "run", "build"], cwd=raiz / "web" / app, timeout=600)
        if proceso.returncode != 0:
            fallas.append(f"{app} ({_cola(proceso, 2) or proceso.returncode})")
    if fallas:
        return Resultado("Compilación de las apps", FALLA, "; ".join(fallas),
                         "Entra a web/<app> y corre npm run build para ver el error")
    return Resultado("Compilación de las apps", OK, f"{', '.join(apps)} compilan")


def puerto_ocupado(puerto: int) -> bool:
    """Ocupado si algo responde en localhost (IPv4 o IPv6) o si no se puede reservar el puerto."""
    for familia, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(familia, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex((host, puerto)) == 0:
                    return True
        except OSError:
            continue  # sin IPv6 en esta máquina
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", puerto))
    except OSError:
        return True
    return False


def revisar_puertos(puertos=PUERTOS, ocupado=puerto_ocupado) -> Resultado:
    nombres = {8000: "API", 5173: "asesor", 5174: "cliente", 5175: "tablero"}
    tomados = [f"{p} ({nombres.get(p, '?')})" for p in puertos if ocupado(p)]
    if tomados:
        return Resultado("Puertos", FALLA, f"ocupados: {', '.join(tomados)}",
                         "Cierra lo que esté usando esos puertos (o detén una demo anterior) antes de empezar")
    return Resultado("Puertos", OK, f"libres: {', '.join(map(str, puertos))}")


def revisar_docker(buscar=shutil.which, correr=ejecutar) -> Resultado:
    docker = buscar("docker")
    if not docker:
        return Resultado("Docker (opcional)", AVISO, "no está instalado",
                         "Solo hace falta para Fineract; la demo funciona con el core simulado")
    version = version_de(correr([docker, "--version"], timeout=30).stdout)
    if correr([docker, "info"], timeout=60).returncode != 0:
        return Resultado("Docker (opcional)", AVISO, "instalado, pero el servicio no está corriendo",
                         "Abre Docker Desktop si vas a mostrar Fineract")
    texto = ".".join(map(str, version)) if version else ""
    return Resultado("Docker (opcional)", OK, f"Docker {texto} corriendo".replace("  ", " "))


def revisar_disco(ruta: Path | None = None, uso=shutil.disk_usage) -> Resultado:
    libre_gb = uso(ruta or RAIZ).free / 1024**3
    detalle = f"{libre_gb:.1f} GB libres"
    if libre_gb < DISCO_MINIMO_GB:
        return Resultado("Espacio en disco", FALLA, detalle, "Libera espacio: compilar y grabar video necesita varios GB")
    if libre_gb < DISCO_RECOMENDADO_GB:
        return Resultado("Espacio en disco", AVISO, detalle, f"Se recomiendan {DISCO_RECOMENDADO_GB:.0f} GB o más")
    return Resultado("Espacio en disco", OK, detalle)


# ---------------------------------------------------------------- informe

def comprobaciones(args: argparse.Namespace) -> list:
    """Lista de funciones a ejecutar, en el orden en que se muestran."""
    lista = [revisar_python, revisar_node, revisar_dependencias_python, revisar_dependencias_node,
             revisar_puertos, revisar_docker, revisar_disco]
    if not args.rapido and not args.sin_pruebas:
        lista.append(lambda: revisar_pytest(completo=args.completo))
    if not args.rapido and not args.sin_compilar:
        lista.append(revisar_compilacion)
    return lista


def _preparar_salida() -> None:
    """Fuera de la consola de Windows (Git Bash, tuberías) se escribe en UTF-8 para que no se rompan las tildes."""
    try:
        if os.getenv("VERIFICAR_COLOR") == "1" or not sys.stdout.isatty():
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def _activar_colores() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("VERIFICAR_COLOR") == "1":  # el lanzador .sh sabe si hay una terminal (también en Git Bash)
        return True
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":  # habilita las secuencias ANSI en la consola de Windows
        try:
            import ctypes

            kernel = ctypes.windll.kernel32
            manejador = kernel.GetStdHandle(-11)
            modo = ctypes.c_uint32()
            if kernel.GetConsoleMode(manejador, ctypes.byref(modo)):
                kernel.SetConsoleMode(manejador, modo.value | 0x0004)
        except Exception:
            return False
    return True


def imprimir(resultado: Resultado, colores: bool) -> None:
    etiqueta = _ETIQUETA[resultado.estado]
    if colores:
        etiqueta = f"{_COLOR[resultado.estado]}{etiqueta}{_NORMAL}"
    print(f"{etiqueta} {resultado.nombre}: {resultado.detalle}", flush=True)
    if resultado.ayuda and resultado.estado != OK:
        print(f"          → {resultado.ayuda}", flush=True)


def main(argv: list[str] | None = None, lista=None) -> int:
    _preparar_salida()  # antes de argparse: --help también lleva tildes
    parser = argparse.ArgumentParser(description="Verifica que la laptop está lista para la final de CuotaFlex.")
    parser.add_argument("--rapido", action="store_true", help="sin pytest ni compilación (unos segundos)")
    parser.add_argument("--completo", action="store_true", help="pytest completo en lugar del rápido")
    parser.add_argument("--sin-pruebas", action="store_true", help="no corre pytest")
    parser.add_argument("--sin-compilar", action="store_true", help="no compila las tres apps")
    args = parser.parse_args(argv)
    colores = _activar_colores()
    print(f"CuotaFlex · verificación del entorno ({RAIZ})", flush=True)
    resultados = []
    for revisar in (lista if lista is not None else comprobaciones(args)):
        try:
            resultado = revisar()
        except Exception as e:  # una comprobación con errores se informa, no corta el resto
            resultado = Resultado(getattr(revisar, "__name__", "comprobación"), FALLA, f"error inesperado: {e}")
        resultados.append(resultado)
        imprimir(resultado, colores)
    fallas = sum(r.estado == FALLA for r in resultados)
    avisos = sum(r.estado == AVISO for r in resultados)
    if fallas:
        final = Resultado("Resultado", FALLA, f"faltan {fallas} cosa(s) antes de presentar")
    else:
        final = Resultado("Resultado", OK, "laptop lista para la final" + (f" ({avisos} aviso(s))" if avisos else ""))
    print()
    imprimir(final, colores)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
