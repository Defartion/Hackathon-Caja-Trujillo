"""Cuentas en el navegador: crear cuenta, salir, volver a ingresar y el PIN de siempre (CUOTAFLEX_AUTH=1).

Levanta una API aparte con la autenticación encendida y compila las apps del cliente y del asesor contra
ella. Los casos de error (contraseña o código incorrectos) se prueban en tests/test_cuentas.py, porque el
navegador registra cada respuesta 401/403 como error de consola y aquí la consola debe quedar limpia.
Ejecutar: pytest tests/e2e/test_cuentas_web.py
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

RAIZ = Path(__file__).resolve().parents[2]
HOST = "127.0.0.1"


@pytest.fixture
def comprobar(navegador):
    from playwright.sync_api import expect

    return expect


def _puerto_libre(candidatos) -> int:
    for puerto in candidatos:
        with socket.socket() as reservado:
            try:
                reservado.bind((HOST, puerto))
            except OSError:
                continue
            return puerto
    pytest.fail("No hay puertos libres para la prueba de cuentas.")


@pytest.fixture(scope="module")
def con_cuentas(demo, tmp_path_factory):
    """API con CUOTAFLEX_AUTH=1 y las apps del cliente y del asesor compiladas contra ella."""
    Servicio = type(demo.api)  # la misma clase de conftest.py
    carpeta = tmp_path_factory.mktemp("cuentas-e2e")
    nodo = shutil.which("node")
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("FINERACT_")}
    entorno.update(
        PYTHONPATH=str(RAIZ / "src"), CUOTAFLEX_AUTH="1", CUOTAFLEX_PERSISTENCIA="0", CUOTAFLEX_SECRETO="prueba-e2e",
        CUOTAFLEX_REGISTRO="cliente", PIN_ASESOR="1111", ENFEN_MODO="demo", ENFEN_REVISION_AUTOMATICA="0",
        CUOTAFLEX_LLM="0", CUOTAFLEX_SIM_PROCESOS="1", NOTIFICACIONES_ARCHIVO=str(carpeta / "notificaciones.jsonl"),
    )
    puerto_api = _puerto_libre(range(5140, 5150))
    url_api = f"http://{HOST}:{puerto_api}"
    api = Servicio([sys.executable, "-m", "uvicorn", "cuotaflex.api.main:app", "--host", HOST, "--port", str(puerto_api)],
                   RAIZ, entorno, url_api, carpeta / "api.log", "/openapi.json")
    servicios = [api]
    try:
        api.iniciar()
        apps = {}
        for app in ("cliente", "asesor"):
            proyecto = RAIZ / "web" / app
            vite = proyecto / "node_modules" / "vite" / "bin" / "vite.js"
            destino = carpeta / app
            vite_env = dict(os.environ, VITE_API_URL=url_api)
            compilacion = subprocess.run([nodo, str(vite), "build", "--outDir", str(destino), "--emptyOutDir"],
                                         cwd=proyecto, env=vite_env, capture_output=True, text=True, timeout=120)
            if compilacion.returncode:
                pytest.fail(f"No se pudo compilar {app}.\n{compilacion.stdout}\n{compilacion.stderr}")
            puerto = _puerto_libre(range(5150, 5160))
            url = f"http://{HOST}:{puerto}"
            preview = Servicio([nodo, str(vite), "preview", "--host", HOST, "--port", str(puerto), "--strictPort",
                                "--outDir", str(destino)], proyecto, vite_env, url, carpeta / f"{app}.log")
            preview.iniciar()
            servicios.append(preview)
            apps[app] = url
        yield apps
    finally:
        for s in reversed(servicios):
            s.detener()


def test_cliente_crea_su_cuenta_sale_y_vuelve_a_entrar(con_cuentas, explorador, comprobar):
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 430, "height": 900})
    pagina.goto(con_cuentas["cliente"])
    expect(pagina.get_by_role("heading", name="Ingresa a tu cuenta")).to_be_visible()
    expect(pagina.get_by_role("heading", name="Tu crédito, a tu ritmo")).to_be_visible()

    pagina.get_by_role("tab", name="Crear cuenta").click()
    expect(pagina.get_by_label("Código de autorización")).to_have_count(0)  # el cliente se registra solo
    pagina.get_by_label("Nombre completo").fill("Rosa Quispe Vela")
    pagina.get_by_label("Correo").fill("rosa.e2e@ejemplo.pe")
    pagina.get_by_label("Contraseña", exact=True).fill("ArrozChepen2026")
    pagina.get_by_role("button", name="Crear cuenta").click()
    expect(pagina.get_by_role("heading", name="Hola, Rosa")).to_be_visible(timeout=15_000)

    pagina.get_by_role("button", name="Abrir menú").click()
    expect(pagina.get_by_role("menu").get_by_text("Rosa Quispe Vela")).to_be_visible()
    pagina.get_by_role("menuitem", name="Salir").click()
    expect(pagina.get_by_role("heading", name="Ingresa a tu cuenta")).to_be_visible()

    pagina.get_by_label("Correo").fill("ROSA.e2e@ejemplo.pe")
    pagina.get_by_label("Contraseña", exact=True).fill("ArrozChepen2026")
    pagina.get_by_role("button", name="Ingresar", exact=True).click()
    expect(pagina.get_by_role("heading", name="Hola, Rosa")).to_be_visible(timeout=15_000)


def test_asesor_entra_con_pin_y_crea_su_cuenta_con_el_codigo(con_cuentas, explorador, comprobar):
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    pagina.goto(con_cuentas["asesor"])
    pagina.get_by_role("button", name="Entrar con el PIN de asesor").click()
    pagina.get_by_label("PIN de asesor").fill("1111")
    pagina.get_by_role("button", name="Entrar", exact=True).click()
    expect(pagina.get_by_role("heading", name="Bandeja de solicitudes")).to_be_visible(timeout=15_000)
    menu = pagina.get_by_role("complementary", name="Menú principal")
    expect(menu.get_by_text("Sesión con PIN")).to_be_visible()
    menu.get_by_role("button", name="Salir").click()

    expect(pagina.get_by_role("heading", name="Ingresa a tu cuenta")).to_be_visible()
    pagina.get_by_role("tab", name="Crear cuenta").click()
    pagina.get_by_label("Nombre completo").fill("Ana Torres Rojas")
    pagina.get_by_label("Correo").fill("ana.e2e@caja.pe")
    pagina.get_by_label("Contraseña", exact=True).fill("Asesora2026")
    pagina.get_by_label("Código de autorización").fill("1111")
    pagina.get_by_role("button", name="Crear cuenta").click()
    expect(pagina.get_by_role("heading", name="Bandeja de solicitudes")).to_be_visible(timeout=15_000)
    expect(menu.get_by_text("Ana Torres Rojas")).to_be_visible()
    expect(pagina.get_by_role("cell", name="E001", exact=True)).to_be_visible()  # la API acepta el token de la cuenta
