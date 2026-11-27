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
        for app in ("cliente", "asesor", "tablero"):
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
        apps["api"] = url_api
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
    expect(pagina.get_by_role("heading", name="Entra con tu código")).to_be_visible()  # fase 4: llave por defecto
    expect(pagina.get_by_role("heading", name="Tu crédito, a tu ritmo")).to_be_visible()
    pagina.get_by_role("button", name="Ingresar con correo y contraseña").click()
    expect(pagina.get_by_role("heading", name="Ingresa a tu cuenta")).to_be_visible()

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
    expect(pagina.get_by_role("heading", name="Entra con tu código")).to_be_visible()
    pagina.get_by_role("button", name="Ingresar con correo y contraseña").click()

    pagina.get_by_label("Correo").fill("ROSA.e2e@ejemplo.pe")
    pagina.get_by_label("Contraseña", exact=True).fill("ArrozChepen2026")
    pagina.get_by_role("button", name="Ingresar", exact=True).click()
    expect(pagina.get_by_role("heading", name="Hola, Rosa")).to_be_visible(timeout=15_000)


def test_asesor_entra_con_pin_y_crea_su_cuenta_con_el_codigo(con_cuentas, explorador, comprobar):
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    pagina.goto(con_cuentas["asesor"])
    pagina.get_by_role("button", name="Entrar con el PIN general de asesor (demo)").click()
    pagina.get_by_label("PIN general de asesor").fill("1111")
    pagina.get_by_role("button", name="Entrar", exact=True).click()
    expect(pagina.get_by_role("heading", name="Bandeja de solicitudes")).to_be_visible(timeout=15_000)
    menu = pagina.get_by_role("complementary", name="Menú principal")
    expect(menu.get_by_text("Sesión con PIN")).to_be_visible()
    menu.get_by_role("button", name="Salir").click()

    expect(pagina.get_by_role("heading", name="Ingresa con tu usuario")).to_be_visible()
    pagina.get_by_role("button", name="Ingresar con correo y contraseña").click()
    pagina.get_by_role("tab", name="Crear cuenta").click()
    pagina.get_by_label("Nombre completo").fill("Ana Torres Rojas")
    pagina.get_by_label("Correo").fill("ana.e2e@caja.pe")
    pagina.get_by_label("Contraseña", exact=True).fill("Asesora2026")
    pagina.get_by_label("Código de autorización").fill("1111")
    pagina.get_by_role("button", name="Crear cuenta").click()
    expect(pagina.get_by_role("heading", name="Bandeja de solicitudes")).to_be_visible(timeout=15_000)
    expect(menu.get_by_text("Ana Torres Rojas")).to_be_visible()
    expect(pagina.get_by_role("cell", name="E001", exact=True)).to_be_visible()  # la API acepta el token de la cuenta


def test_cliente_ve_su_cuenta_en_el_perfil(con_cuentas, explorador, comprobar):
    contexto, _ = explorador
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 430, "height": 900})
    pagina.goto(con_cuentas["cliente"])
    pagina.get_by_role("button", name="Ingresar con correo y contraseña").click()
    pagina.get_by_role("tab", name="Crear cuenta").click()
    pagina.get_by_label("Nombre completo").fill("Teresa Vargas Ruiz")
    pagina.get_by_label("Correo").fill("teresa.e2e@ejemplo.pe")
    pagina.get_by_label("Contraseña", exact=True).fill("Limones2026")
    pagina.get_by_role("button", name="Crear cuenta").click()
    comprobar(pagina.get_by_role("heading", name="Hola, Teresa")).to_be_visible(timeout=15_000)

    pagina.get_by_role("button", name="Abrir menú").click()
    pagina.get_by_role("menuitem", name="Mi perfil").click()
    comprobar(pagina.get_by_role("heading", name="Teresa Vargas Ruiz")).to_be_visible()
    datos = pagina.locator(".kv").first
    comprobar(datos).to_contain_text("teresa.e2e@ejemplo.pe")
    comprobar(datos).to_contain_text("Correo y contraseña")
    pagina.get_by_role("button", name="Volver al inicio").click()
    comprobar(pagina.get_by_role("heading", name="Hola, Teresa")).to_be_visible()


def _api(url: str, metodo: str, ruta: str, token: str | None = None, cuerpo: dict | None = None) -> dict:
    import json
    import urllib.request

    pedido = urllib.request.Request(
        url + ruta, method=metodo, data=None if cuerpo is None else json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # localhost, sin proxy
    with abridor.open(pedido, timeout=120) as r:
        return json.loads(r.read())


def test_llaves_personales_de_punta_a_punta(con_cuentas, explorador, comprobar):
    """Fase 4: el supervisor crea la llave de una asesora, ella ve el código del cliente y el cliente entra con él
    a SU préstamo. Al desactivarla, su sesión se corta."""
    contexto, _ = explorador
    expect = comprobar
    api = con_cuentas["api"]
    general = _api(api, "POST", "/auth/login", cuerpo={"rol": "cliente", "pin": "2222"})["token"]
    prestamo = _api(api, "POST", "/cliente/demo-seed", token=general)["loanId"]  # Rosa Salazar, desembolsado

    # 1. El supervisor entra con el PIN general (demo) y crea la llave de Ana en Equipo
    sup = contexto.new_page()
    sup.goto(con_cuentas["tablero"])
    expect(sup.get_by_role("heading", name="Ingresa con tu usuario")).to_be_visible()
    sup.get_by_role("button", name="Entrar con el PIN general de supervisor (demo)").click()
    sup.get_by_label("PIN general de supervisor").fill("3333")
    sup.get_by_role("button", name="Entrar", exact=True).click()
    sup.get_by_role("button", name="Equipo").click()
    expect(sup.get_by_role("heading", name="Equipo", exact=True)).to_be_visible(timeout=15_000)
    sup.get_by_label("Nombre completo").fill("Ana Torres Rojas")
    sup.get_by_role("button", name="Crear su llave").click()
    tarjeta = sup.locator(".llave-nueva")
    expect(tarjeta).to_contain_text("ana.torres")
    pin = tarjeta.locator(".llave-nueva__pin").inner_text().replace(" ", "")
    assert len(pin) == 6 and pin.isdigit()
    expect(sup.get_by_role("cell", name="Ana Torres Rojas")).to_be_visible()

    # 2. Ana entra al asesor con su usuario y PIN y ve el código del cliente en el detalle del préstamo
    ana = contexto.new_page()
    ana.goto(con_cuentas["asesor"])
    ana.get_by_label("Usuario").fill("ana.torres")
    ana.get_by_label("PIN personal").fill(pin)
    ana.get_by_role("button", name="Entrar", exact=True).click()
    expect(ana.get_by_role("heading", name="Bandeja de solicitudes")).to_be_visible(timeout=15_000)
    expect(ana.get_by_role("complementary", name="Menú principal").get_by_text("Ana Torres Rojas")).to_be_visible()
    ana.goto(f"{con_cuentas['asesor']}/prestamos/{prestamo}")
    acceso = ana.get_by_label("Código de acceso del cliente")
    acceso.get_by_role("button", name="Mostrar código").click()
    codigo = acceso.locator(".codigo-cliente__digitos").inner_text().replace(" ", "")
    assert len(codigo) == 6 and codigo.isdigit()

    # 3. El cliente entra con su número de préstamo y su código, y solo ve su préstamo
    cli = contexto.new_page()
    cli.set_viewport_size({"width": 430, "height": 900})
    cli.goto(f"{con_cuentas['cliente']}/?loanId=999")
    expect(cli.get_by_role("heading", name="Entra con tu código")).to_be_visible()
    cli.get_by_label("Número de préstamo").fill(str(prestamo))
    cli.get_by_label("Código de acceso").fill(codigo)  # el código equivocado se prueba en test_fase4_llaves.py
    cli.get_by_role("button", name="Entrar", exact=True).click()
    expect(cli.get_by_role("heading", name="Hola, Rosa")).to_be_visible(timeout=15_000)
    assert f"loanId={prestamo}" in cli.url  # el número del enlace se corrige a su préstamo

    # 4. El supervisor desactiva a Ana: su sesión se corta al siguiente pedido. Se comprueba contra la API con
    #    el token de su pestaña, para no dejar un 401 en la consola del navegador (la prueba los vigila).
    token_ana = ana.evaluate("sessionStorage.getItem('cuotaflex_token.asesor')")
    assert _api(api, "GET", "/motor/prestamos", token=token_ana) is not None
    fila = sup.get_by_role("row", name="Ana Torres Rojas")
    fila.get_by_role("button", name="Desactivar").click()
    fila.get_by_role("button", name="Sí, desactivar").click()
    expect(fila.get_by_text("Desactivado")).to_be_visible()
    import urllib.error

    with pytest.raises(urllib.error.HTTPError) as cortado:
        _api(api, "GET", "/motor/prestamos", token=token_ana)
    assert cortado.value.code == 401
    ana.close()

