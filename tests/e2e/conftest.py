"""Servicios locales y Chromium para los recorridos de la demo."""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urlsplit

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_E2E = Path(__file__).resolve().parent
APPS = ("asesor", "cliente", "tablero")
HOST = "127.0.0.1"
BUCLE_LOCAL = {HOST, "::1", "localhost"}


def pytest_addoption(parser):
    parser.addoption("--capturas", action="store_true", help="Guarda las capturas E2E en docs/demo/capturas.")


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: recorrido de la demo en Chromium con servicios locales.")


def _ejecutar_e2e(config):
    if config.getoption("--capturas") or re.search(r"\be2e\b", config.getoption("-m")):
        return True
    rutas = (Path(arg.split("::", 1)[0]).resolve() for arg in config.args)
    return any(ruta == CARPETA_E2E or CARPETA_E2E in ruta.parents for ruta in rutas)


def _puerto_libre(candidatos=(0,)):
    for puerto in candidatos:
        with socket.socket() as reservado:
            try:
                reservado.bind((HOST, puerto))
            except OSError:
                continue
            return reservado.getsockname()[1]
    pytest.fail("No hay puertos libres en el rango 51xx que acepta el CORS de la API.")


@dataclass
class Servicio:
    comando: list[str]
    carpeta: Path
    entorno: dict[str, str]
    url: str
    log: Path
    salud: str = "/"
    proceso: subprocess.Popen | None = None

    def iniciar(self):
        with self.log.open("ab") as salida:
            self.proceso = subprocess.Popen(
                self.comando, cwd=self.carpeta, env=self.entorno,
                stdout=salida, stderr=subprocess.STDOUT,
            )
        limite = monotonic() + 75
        with httpx.Client(timeout=1, trust_env=False) as cliente:
            while monotonic() < limite and self.proceso.poll() is None:
                try:
                    if cliente.get(self.url + self.salud).is_success:
                        return
                except httpx.TransportError:
                    pass
                sleep(0.1)
        pytest.fail(f"No arrancó el servicio {self.url}.\n{self.log.read_text(errors='replace')[-4000:]}")

    def detener(self):
        if self.proceso is None or self.proceso.poll() is not None:
            return
        self.proceso.terminate()
        try:
            self.proceso.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.proceso.kill()
            self.proceso.wait(timeout=8)


@dataclass
class EntornoDemo:
    api: Servicio
    apps: dict[str, str]


@pytest.fixture(scope="session")
def navegador(pytestconfig):
    if not _ejecutar_e2e(pytestconfig):
        pytest.skip("Ejecuta pytest -m e2e o pytest tests/e2e para iniciar los navegadores.")
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(args=["--disable-background-networking"])
        except playwright.Error as error:
            if "Executable doesn't exist" in str(error):
                pytest.skip("Instala Chromium con python -m playwright install chromium.")
            raise
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture(scope="session")
def demo(navegador, tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("cuotaflex-e2e")
    python_env = {k: v for k, v in os.environ.items() if not k.startswith("FINERACT_")}
    python_env.update(
        PYTHONPATH=str(RAIZ / "src"),
        ENFEN_MODO="demo",
        ENFEN_REVISION_AUTOMATICA="0",
        CUOTAFLEX_LLM="0",
        NOTIFICACIONES_ARCHIVO=str(carpeta / "notificaciones.jsonl"),
        CUOTAFLEX_SIM_PROCESOS="1",
    )
    nodo = shutil.which("node")
    if nodo is None:
        pytest.fail("Instala Node.js para servir las tres apps compiladas.")
    herramientas_vite = {app: RAIZ / "web" / app / "node_modules/vite/bin/vite.js" for app in APPS}
    for ruta in herramientas_vite.values():
        if not ruta.is_file():
            pytest.fail(f"Ejecuta npm ci en {ruta.parents[3]} antes de ejecutar E2E.")

    puerto = _puerto_libre()
    url_api = f"http://{HOST}:{puerto}"
    api = Servicio(
        [sys.executable, "-m", "uvicorn", "cuotaflex.api.main:app", "--host", HOST, "--port", str(puerto)],
        RAIZ, python_env, url_api, carpeta / "api.log", "/openapi.json",
    )
    vite_env = dict(os.environ, VITE_API_URL=url_api)
    urls = {}
    with ExitStack() as limpieza:
        limpieza.callback(api.detener)
        api.iniciar()
        for app, vite in herramientas_vite.items():
            proyecto = RAIZ / "web" / app
            destino = carpeta / app
            compilacion = subprocess.run(
                [nodo, str(vite), "build", "--outDir", str(destino), "--emptyOutDir"],
                cwd=proyecto, env=vite_env, capture_output=True, text=True, timeout=90,
            )
            if compilacion.returncode:
                pytest.fail(f"No se pudo compilar {app}.\n{compilacion.stdout}\n{compilacion.stderr}")

            puerto = _puerto_libre(range(5180, 5200))
            url = f"http://{HOST}:{puerto}"
            preview = Servicio(
                [nodo, str(vite), "preview", "--host", HOST, "--port", str(puerto),
                 "--strictPort", "--outDir", str(destino)],
                proyecto, vite_env, url, carpeta / f"{app}.log",
            )
            limpieza.callback(preview.detener)
            preview.iniciar()
            urls[app] = url
        yield EntornoDemo(api, urls)


@pytest.fixture
def captura(pytestconfig):
    def guardar(original, nombre: str):
        if pytestconfig.getoption("--capturas"):
            destino = RAIZ / "docs" / "demo" / "capturas"
            destino.mkdir(parents=True, exist_ok=True)
            original.screenshot(path=destino / f"{nombre}.png", animations="disabled")
    return guardar


@pytest.fixture
def explorador(navegador, demo):
    contexto = navegador.new_context(
        viewport={"width": 1366, "height": 900}, locale="es-PE", service_workers="block",
    )
    errores, recursos_externos, diagnosticos_api, fallos_api = [], [], [], []
    sin_api = False

    def vigilar_ruta(ruta):
        url = urlsplit(ruta.request.url)
        if url.scheme in {"http", "https"} and url.hostname not in BUCLE_LOCAL:
            recursos_externos.append(ruta.request.url)
            ruta.abort("internetdisconnected")
        else:
            ruta.continue_()

    def vigilar_consola(mensaje):
        if mensaje.type != "error":
            return
        url = mensaje.location.get("url", "")
        if sin_api and url.startswith(demo.api.url + "/") and mensaje.text.endswith("net::ERR_CONNECTION_REFUSED"):
            diagnosticos_api.append(mensaje.text)
            return
        errores.append(f"{url} {mensaje.text}".strip())

    def vigilar_fallo(pedido):
        if sin_api and pedido.url.startswith(demo.api.url + "/") and pedido.failure == "net::ERR_CONNECTION_REFUSED":
            fallos_api.append(pedido.url)

    def vigilar_pagina(pagina):
        pagina.on("console", vigilar_consola)
        pagina.on("pageerror", lambda error: errores.append(str(error)))
        pagina.on("requestfailed", vigilar_fallo)

    def desconectar_api():
        nonlocal sin_api
        demo.api.detener()
        sin_api = True

    contexto.on("page", vigilar_pagina)
    contexto.route("**/*", vigilar_ruta)
    try:
        yield contexto, desconectar_api
    finally:
        contexto.close()
        if sin_api:
            demo.api.iniciar()
            assert fallos_api, "Chromium no detectó la caída real de la API."
            # Chromium representa conexiones rehusadas como diagnósticos de red.
            # Excluimos solo los del origen y la caída real que provoca esta prueba.
            assert len(diagnosticos_api) <= len(fallos_api), diagnosticos_api
        assert not recursos_externos, f"Recursos externos detectados: {recursos_externos}"
        assert not errores, f"Errores de JavaScript o de consola: {errores}"
