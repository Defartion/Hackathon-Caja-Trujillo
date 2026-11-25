"""Fase 4 · Lote C: asistente de nueva solicitud y vista del comité en Chromium.

En modo mock (VITE_MOCK=1) la app del asesor usa los JSON de web/asesor/src/mocks/, copia de
tests/fixtures/contratos/ (caso Rosa), así que no depende de los lotes A y B. La prueba contra la
API real se ejecuta sola cuando la API ya expone POST /ciclo/estimar y POST /plan/proponer.
Ejecutar: pytest tests/e2e/test_fase4_c.py
"""
from __future__ import annotations

import io
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

RAIZ = Path(__file__).resolve().parents[2]
ASESOR = RAIZ / "web" / "asesor"
HOST = "127.0.0.1"
SECCIONES_COMITE = (
    "1. Ciclo económico estimado",
    "2. Plan propuesto frente a la cuota fija",
    "3. Cuota/UN por etapa",
    "4. Escenarios adversos",
    "5. Cronograma del plan adaptado",
    "7. Supuestos y fuentes",
    "9. Validación del Asesor de Riesgos y decisión del comité",
)


@pytest.fixture
def comprobar(navegador):
    from playwright.sync_api import expect

    return expect


def _puerto_libre() -> int:
    # El CORS de la API acepta 51xx; conftest.py usa 5180-5199 para las apps de la demo.
    for puerto in range(5160, 5180):
        with socket.socket() as reservado:
            try:
                reservado.bind((HOST, puerto))
            except OSError:
                continue
            return puerto
    pytest.fail("No hay puertos libres entre 5160 y 5179.")


@pytest.fixture(scope="module")
def asesor_mock(demo, tmp_path_factory):
    """App del asesor compilada con VITE_MOCK=1 (la API de la demo solo atiende /auth/config)."""
    nodo = shutil.which("node")
    vite = ASESOR / "node_modules" / "vite" / "bin" / "vite.js"
    destino = tmp_path_factory.mktemp("asesor-mock")
    entorno = dict(os.environ, VITE_API_URL=demo.api.url, VITE_MOCK="1")
    compilacion = subprocess.run(
        [nodo, str(vite), "build", "--outDir", str(destino), "--emptyOutDir"],
        cwd=ASESOR, env=entorno, capture_output=True, text=True, timeout=120,
    )
    if compilacion.returncode:
        pytest.fail(f"No se pudo compilar el asesor en modo mock.\n{compilacion.stdout}\n{compilacion.stderr}")
    puerto = _puerto_libre()
    url = f"http://{HOST}:{puerto}"
    servicio = type(demo.api)(  # la misma clase Servicio de conftest.py
        [nodo, str(vite), "preview", "--host", HOST, "--port", str(puerto), "--strictPort", "--outDir", str(destino)],
        ASESOR, entorno, url, destino.parent / "asesor-mock.log",
    )
    servicio.iniciar()
    try:
        yield url
    finally:
        servicio.detener()


def _entero(localizador) -> int:
    return int(localizador.inner_text().strip())


def _hasta_el_plan(pagina, base, expect):
    """Recorre los pasos 1 y 2 con el caso Rosa y deja la página en el paso 3."""
    pagina.goto(f"{base}/nueva")
    expect(pagina.get_by_role("heading", name="Nueva solicitud")).to_be_visible()
    pagina.get_by_role("button", name="Cargar caso Rosa (E001)").click()
    expect(pagina.get_by_label("Código de la solicitud")).to_have_value("E001")
    pagina.get_by_role("button", name="Estimar ciclo →").click()
    expect(pagina.get_by_role("figure", name=re.compile("^Ciclo estimado"))).to_be_visible(timeout=20_000)
    pagina.get_by_role("button", name="Continuar: crédito y plan →").click()
    expect(pagina.get_by_test_id("estado-plan")).to_be_visible(timeout=25_000)


def test_nueva_solicitud_rosa_completa_los_tres_pasos(asesor_mock, explorador, comprobar):
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1366, "height": 768})
    pagina.goto(f"{asesor_mock}/nueva")
    expect(pagina.get_by_role("status")).to_contain_text("Modo de prueba")

    # Paso 1: las validaciones hablan en lenguaje de campo.
    pagina.get_by_role("button", name="Estimar ciclo →").click()
    expect(pagina.get_by_text("Anota cuánto vende en un buen mes (S/).")).to_be_visible()
    pagina.get_by_role("button", name="Cargar caso Rosa (E001)").click()
    expect(pagina.get_by_role("button", name="junio: mes alto")).to_be_visible()
    expect(pagina.get_by_role("button", name="enero: mes bajo")).to_be_visible()
    expect(pagina.get_by_text("Utilidad neta en un mes bajo")).to_be_visible()
    pagina.get_by_role("button", name="Estimar ciclo →").click()

    # Paso 2: ciclo con banda, etapas, supuestos y fuentes desplegables; "Ajustar meses" vuelve al paso 1.
    expect(pagina.get_by_role("figure", name=re.compile("^Ciclo estimado"))).to_be_visible()
    expect(pagina.get_by_text("Rango p10–p90")).to_be_visible()
    pagina.locator("summary", has_text="Supuestos del ciclo").click()
    expect(pagina.get_by_text(re.compile("Patrón de campaña de arroz en Chepén"))).to_be_visible()
    pagina.locator("summary", has_text="Fuentes").click()
    expect(pagina.locator(".pl-fuentes li").first).to_contain_text("MIDAGRI")
    pagina.get_by_role("button", name="← Ajustar meses").click()
    expect(pagina.get_by_role("group", name="Meses altos y bajos")).to_be_visible()
    pagina.get_by_role("button", name="Estimar ciclo →").click()
    pagina.get_by_role("button", name="Continuar: crédito y plan →").click()

    # Paso 3: plan adaptado sin etapas sobre el factor; la cuota fija sí las tiene.
    expect(pagina.get_by_test_id("estado-plan")).to_contain_text("Plan factible")
    assert _entero(pagina.get_by_test_id("etapas-sobre-factor-adaptado")) == 0
    assert _entero(pagina.get_by_test_id("etapas-sobre-factor-fija")) > 0
    expect(pagina.get_by_role("figure", name=re.compile("^Cuotas del plan adaptado"))).to_be_visible()
    tabla = pagina.get_by_role("table", name="Cronograma del plan adaptado")
    expect(tabla).to_contain_text("Gracia")
    expect(tabla.locator(".pl-semaforo").first).to_be_visible()
    expect(pagina.get_by_role("table", name="Resumen comparado")).to_contain_text("TCEA")
    expect(pagina.get_by_role("table", name="Escenarios adversos")).to_contain_text("El Niño costero")

    # La TEA sobre el tope del producto se avisa y no se propone el plan.
    pagina.get_by_label("TEA", exact=True).fill("90")
    expect(pagina.get_by_text(re.compile("Supera el tope de 83.00% del producto"))).to_be_visible()
    expect(pagina.get_by_role("button", name="Guardar y abrir la vista del comité →")).to_be_disabled()
    pagina.get_by_label("TEA", exact=True).fill("45")
    expect(pagina.get_by_role("button", name="Guardar y abrir la vista del comité →")).to_be_enabled()

    # Sin desbordes horizontales en 1366 × 768.
    assert pagina.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_caso_no_factible_muestra_ajustes_y_al_aplicar_uno_es_factible(asesor_mock, explorador, comprobar):
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    _hasta_el_plan(pagina, asesor_mock, expect)

    monto = pagina.get_by_label("Monto", exact=True)
    monto.fill("12000")  # el mock responde "no factible" por encima de S/ 7,000
    expect(pagina.get_by_test_id("estado-plan")).to_contain_text("Sin plan factible")
    expect(pagina.get_by_role("button", name="Aplicar: Ampliar el plazo a 30 meses")).to_be_visible()
    expect(pagina.get_by_role("button", name="Informar al comité →")).to_be_enabled()

    pagina.get_by_role("button", name="Aplicar: Reducir el monto a S/ 7,000").click()
    expect(monto).to_have_value("7000")
    expect(pagina.get_by_test_id("estado-plan")).to_contain_text("Plan factible")
    assert _entero(pagina.get_by_test_id("etapas-sobre-factor-adaptado")) == 0
    expect(pagina.get_by_text("Ajustes aplicados: Monto de S/ 12,000 a S/ 7,000 (sugerencia del motor)")).to_be_visible()


def test_vista_del_comite_es_imprimible_y_registra_la_validacion(asesor_mock, explorador, comprobar):
    from pypdf import PdfReader

    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1366, "height": 768})
    _hasta_el_plan(pagina, asesor_mock, expect)
    pagina.get_by_role("button", name="Guardar y abrir la vista del comité →").click()
    expect(pagina).to_have_url(re.compile(r"/comite/E001$"))

    for titulo in SECCIONES_COMITE:
        expect(pagina.get_by_role("heading", name=titulo)).to_be_visible()
    expect(pagina.get_by_role("figure", name=re.compile("^Ciclo estimado"))).to_be_visible()
    expect(pagina.get_by_role("figure", name=re.compile("^Cuotas del plan adaptado"))).to_be_visible()
    expect(pagina.get_by_role("table", name="Cronograma para el comité")).to_contain_text("Gracia")
    expect(pagina.get_by_role("table", name="Escenarios adversos")).to_contain_text("El Niño costero")
    expect(pagina.get_by_role("table", name="Cuota/UN por etapa")).to_contain_text("Valle")
    expect(pagina.get_by_text(re.compile("Patrón de campaña de arroz en Chepén"))).to_be_visible()
    expect(pagina.get_by_test_id("explicacion-reservada")).to_be_visible()

    # Validación del Asesor de Riesgos: observar exige comentario; queda guardada con la fecha.
    pagina.get_by_role("button", name="Observar").click()
    pagina.get_by_role("button", name="Registrar validación").click()
    expect(pagina.get_by_text("Escribe la observación para el Asesor de Negocios.")).to_be_visible()
    pagina.get_by_label("Comentario").fill("Confirmar con boletas las ventas de la cosecha.")
    pagina.get_by_role("button", name="Registrar validación").click()
    sello = pagina.get_by_test_id("validacion-registrada")
    expect(sello).to_contain_text("Observado por el Asesor de Riesgos")
    expect(sello).to_contain_text(re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}"))
    pagina.reload()
    expect(pagina.get_by_test_id("validacion-registrada")).to_contain_text("Observado")
    expect(pagina.get_by_text("Confirmar con boletas las ventas de la cosecha.")).to_be_visible()

    # window.print no rompe la página.
    pagina.get_by_role("button", name="Imprimir o guardar en PDF").click()
    expect(pagina.get_by_role("heading", name=SECCIONES_COMITE[0])).to_be_visible()
    pagina.get_by_role("button", name="Corregir").click()
    expect(pagina.get_by_role("button", name="Registrar validación")).to_be_visible()
    pagina.get_by_role("button", name="Cancelar").click()

    # Con CSS de impresión: sin barra de herramientas y en A4 vertical de 2 o 3 páginas.
    pagina.emulate_media(media="print")
    expect(pagina.get_by_role("button", name="Imprimir o guardar en PDF")).to_be_hidden()
    expect(pagina.get_by_role("heading", name=SECCIONES_COMITE[-1])).to_be_visible()
    pdf = pagina.pdf(format="A4", print_background=True, prefer_css_page_size=True)
    paginas = PdfReader(io.BytesIO(pdf)).pages
    assert 2 <= len(paginas) <= 3, len(paginas)
    assert "Observado" in "".join(p.extract_text() for p in paginas)


def test_la_ficha_oculta_aplazamientos_y_alivio_en_vivo(demo, explorador, comprobar):
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    pagina.goto(demo.apps["asesor"])
    expect(pagina.get_by_role("button", name="Nueva solicitud")).to_be_visible()
    pagina.get_by_role("cell", name="E001", exact=True).click()
    aviso = pagina.get_by_test_id("fuera-de-alcance")
    expect(aviso).to_be_visible(timeout=25_000)
    expect(aviso).to_contain_text("fuera del alcance del reto (créditos vigentes = reprogramación)")
    expect(pagina.get_by_text("Cláusula El Niño", exact=True)).to_have_count(0)


def test_flujo_contra_la_api_real(demo, explorador, comprobar):
    rutas = httpx.get(f"{demo.api.url}/openapi.json", timeout=10, trust_env=False).json().get("paths", {})
    if "/ciclo/estimar" not in rutas or "/plan/proponer" not in rutas:
        pytest.skip("La API todavía no integra los lotes A y B de la fase 4.")
    contexto, _ = explorador
    expect = comprobar
    pagina = contexto.new_page()
    _hasta_el_plan(pagina, demo.apps["asesor"], expect)
    expect(pagina.get_by_test_id("estado-plan")).to_contain_text("Plan factible")
    assert _entero(pagina.get_by_test_id("etapas-sobre-factor-adaptado")) == 0
    assert _entero(pagina.get_by_test_id("etapas-sobre-factor-fija")) > 0
    pagina.get_by_role("button", name="Guardar y abrir la vista del comité →").click()
    for titulo in SECCIONES_COMITE:
        expect(pagina.get_by_role("heading", name=titulo)).to_be_visible()
