"""Recorridos de CuotaFlex con entorno local, datos sintéticos y Chromium."""
from __future__ import annotations

import re
from decimal import Decimal

import pytest

# Importar Playwright en la fixture permite que la suite de Python se ejecute sin él.
pytestmark = pytest.mark.e2e
RUTA_CORE = "/fineract-provider/api/v1/loans"


@pytest.fixture
def comprobar(navegador):
    from playwright.sync_api import expect

    return expect


def _asesor(contexto, demo, caso, expect):
    pagina = contexto.new_page()
    pagina.goto(demo.apps["asesor"])
    pagina.get_by_role("cell", name=caso, exact=True).click()
    expect(pagina.get_by_role("heading", name=f"Solicitud {caso}")).to_be_visible()
    expect(pagina.get_by_role("heading", name="Propuesta del agente")).to_be_visible(timeout=25_000)
    return pagina


def _tarjeta(pagina, cabecera):
    return pagina.locator(".tarjeta").filter(has=pagina.get_by_role("heading", name=cabecera))


def _registrar_y_desembolsar(pagina, expect, captura=None):
    with pagina.expect_response(
        lambda respuesta: respuesta.request.method == "POST" and respuesta.url.endswith(RUTA_CORE),
        timeout=25_000,
    ) as registro:
        pagina.get_by_role("button", name="Registrar solicitud en el core", exact=True).click()
    assert registro.value.ok, registro.value.text()
    credito = registro.value.json()["loanId"]
    expect(pagina.get_by_text("Registrada, falta aprobar", exact=True)).to_be_visible()
    pagina.get_by_role("button", name="Aprobar", exact=True).click()
    expect(pagina.get_by_text("Aprobada, falta desembolsar", exact=True)).to_be_visible()
    if captura is not None:
        captura(_tarjeta(pagina, "Registrar en el core"), "03-asesor-e001-aprobacion")
    pagina.get_by_role("button", name="Desembolsar", exact=True).click()
    expect(pagina.get_by_text("Desembolsada (activa)", exact=True)).to_be_visible()
    if captura is not None:
        captura(_tarjeta(pagina, "Registrar en el core"), "04-asesor-e001-desembolso")
    return credito


def _cliente(contexto, demo, credito, *, panel_demo=False):
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 470, "height": 860})
    modo = "&demo=1" if panel_demo else ""
    pagina.goto(f"{demo.apps['cliente']}/?loanId={credito}{modo}")
    return pagina


def _cuota_visible(pagina):
    return pagina.get_by_role("region", name="Próxima cuota").locator(".due-card__amount")


def _soles(texto):
    return Decimal(texto.removeprefix("S/").replace(",", "").strip())


def test_asesor_y_cliente_prestamo_de_rosa(demo, explorador, captura, comprobar):
    contexto, _ = explorador
    expect = comprobar
    asesor = _asesor(contexto, demo, "E001", expect)
    asesor.get_by_role("tab", name="Cómo decidió el agente").click()
    bitacora = _tarjeta(asesor, "Cómo decidió el agente")
    expect(bitacora.get_by_text("Selección por simulación: cuotas estacionales", exact=True)).to_be_visible()
    captura(bitacora, "01-asesor-e001-seleccion")

    asesor.evaluate("window.scrollTo(0, 0)")
    asesor.get_by_text("Pregúntale al agente", exact=True).click()
    chat = asesor.get_by_role("complementary", name="Agente de CuotaFlex")
    chat.get_by_role("button", name="¿Y a 24 meses?", exact=True).click()
    expect(chat.get_by_text("✓ Cifras verificadas")).to_be_visible(timeout=20_000)
    expect(chat.get_by_text("Recalculó a 24 meses")).to_be_visible()
    chat.get_by_role("button", name="Aplicar a la ficha").click()
    expect(chat.get_by_text("Vista previa de la propuesta")).to_be_visible()
    captura(asesor, "02-asesor-e001-chat")
    asesor.get_by_text("Pregúntale al agente", exact=True).click()

    credito = _registrar_y_desembolsar(asesor, expect, captura)
    cliente = _cliente(contexto, demo, credito)
    expect(_cuota_visible(cliente)).to_have_text(re.compile(r"^S/\s[\d,.]+$"))
    captura(cliente, "05-cliente-e001-proxima-cuota")
    aplazar = cliente.get_by_role("button", name="Necesito aplazar una cuota")
    if aplazar.is_visible():
        aplazar.click()
        cliente.get_by_role("combobox", name="Cuota que quieres aplazar").select_option(index=1)
        cliente.get_by_role("button", name="Ver costo del aplazamiento").click()
        expect(cliente.get_by_role("region", name="Detalle del aplazamiento")).to_be_visible()
    else:
        cliente.get_by_role("button", name="Ver mi cronograma").click()
        expect(cliente.get_by_role("heading", name="Mi cronograma")).to_be_visible()
        filas = cliente.get_by_role("list", name="Cuotas del crédito").get_by_role("listitem")
        expect(filas.first).to_contain_text("Cuota 1 · Próxima")
        assert filas.count() > 1
    captura(cliente, "06-cliente-e001-cronograma")


def test_alerta_demo_y_alivio_de_martin(demo, explorador, captura, comprobar):
    contexto, _ = explorador
    expect = comprobar
    asesor = _asesor(contexto, demo, "E002", expect)
    credito = _registrar_y_desembolsar(asesor, expect)
    cliente = _cliente(contexto, demo, credito, panel_demo=True)
    alerta_demo = cliente.get_by_role("switch", name="Alerta El Niño")
    expect(alerta_demo).to_be_enabled()
    expect(alerta_demo).to_have_attribute("aria-checked", "false")

    cuota = _cuota_visible(cliente)
    expect(cuota).to_be_visible()
    cuota_antes = cuota.inner_text()
    cuota_ini = _soles(cuota_antes)
    alerta_demo.click()
    expect(cliente.get_by_role("heading", name="Alerta El Niño activa")).to_be_visible()
    captura(cliente, "07-cliente-e002-alerta")

    tablero = contexto.new_page()
    tablero.goto(demo.apps["tablero"])
    distintivo = tablero.get_by_role("button", name=re.compile("Alerta de El Niño Costero"))
    expect(distintivo).to_be_enabled()
    distintivo.click()
    impacto = tablero.get_by_role("region", name="Impacto de la alerta en la cartera")
    expect(impacto.get_by_text("Saldo cubierto", exact=True)).to_be_visible()
    expect(impacto.get_by_role("cell", name="Pesca", exact=True)).to_be_visible()
    captura(tablero, "08-tablero-e002-cartera")

    usar_alivio = cliente.get_by_role("button", name="Usar alivio")
    usar_alivio.click()
    expect(cliente.get_by_role("status")).to_contain_text("Alivio aplicado")
    expect(cuota).not_to_have_text(cuota_antes)
    assert Decimal("0") < _soles(cuota.inner_text()) < cuota_ini
    expect(usar_alivio).to_have_count(0)
    captura(cliente, "09-cliente-e002-alivio")


def test_tablero_compara_escenario_base_con_ano_el_nino(demo, explorador, captura, comprobar):
    contexto, _ = explorador
    expect = comprobar
    tablero = contexto.new_page()
    tablero.goto(demo.apps["tablero"])
    # "Rápido" es el tamaño por defecto y el escenario base corre solo al abrir.
    base = tablero.get_by_role("button", name="Base", exact=True)
    base.click()
    expect(tablero.locator(".cab-corrida")).to_contain_text(
        "Base · 150 créditos × 80 escenarios", timeout=75_000,
    )
    indicadores = tablero.locator(".kpi")
    expect(indicadores).to_have_count(4)
    for etiqueta in (
        "Créditos con atraso > 30 días", "Incumplimiento (3 cuotas impagas)",
        "Margen neto / cartera", "Cartera colocada",
    ):
        expect(indicadores.get_by_text(etiqueta, exact=True)).to_be_visible()
    valores = tablero.locator(".kpi-valores")
    antes = valores.all_inner_texts()
    captura(tablero, "10-tablero-base")

    tablero.get_by_role("button", name="Año El Niño", exact=True).click()
    expect(tablero.locator(".cab-corrida")).to_contain_text(
        "Año El Niño · 150 créditos × 80 escenarios", timeout=75_000,
    )
    expect(indicadores).to_have_count(4)
    assert valores.all_inner_texts() != antes
    captura(tablero, "11-tablero-ano-el-nino")


def test_asesor_explica_la_reduccion_del_monto_de_luis(demo, explorador, captura, comprobar):
    contexto, _ = explorador
    expect = comprobar
    asesor = _asesor(contexto, demo, "E003", expect)
    asesor.get_by_role("tab", name="Cómo decidió el agente").click()
    bitacora = _tarjeta(asesor, "Cómo decidió el agente")
    expect(bitacora.get_by_text(re.compile(r"^Ajuste del monto: "))).to_be_visible()
    bitacora.get_by_role("button", name="Ver intentos").click()
    expect(bitacora.get_by_text("Replanificación: reducir monto", exact=True).first).to_be_visible()
    captura(bitacora, "12-asesor-e003-reduccion")

    asesor.evaluate("window.scrollTo(0, 0)")
    asesor.get_by_text("Pregúntale al agente", exact=True).click()
    chat = asesor.get_by_role("complementary", name="Agente de CuotaFlex")
    chat.get_by_role("button", name="¿Por qué bajó el monto?", exact=True).click()
    expect(chat.get_by_text("✓ Cifras verificadas")).to_be_visible(timeout=20_000)
    respuesta = chat.get_by_text(re.compile(r"redujo el monto solicitado", re.IGNORECASE))
    expect(respuesta).to_be_visible()
    cifras = re.findall(r"S/ [\d,]+\.\d{2}", respuesta.inner_text())
    assert len(cifras) == 2 and _soles(cifras[1]) < _soles(cifras[0])
    captura(asesor, "13-asesor-e003-chat")


def test_las_tres_apps_informan_de_la_api_apagada(demo, explorador, captura, comprobar):
    contexto, desconectar_api = explorador
    expect = comprobar
    desconectar_api()

    asesor = contexto.new_page()
    asesor.goto(demo.apps["asesor"])
    expect(asesor.get_by_text(re.compile(r"No se pudo conectar con la API"))).to_be_visible()
    captura(asesor, "14-sin-api-asesor")

    cliente = _cliente(contexto, demo, credito=1)
    expect(cliente.get_by_role("alert")).to_contain_text("No pudimos conectar con la app de pagos")
    expect(cliente.get_by_role("button", name="Volver a cargar", exact=True)).to_be_visible()
    captura(cliente, "15-sin-api-cliente")

    tablero = contexto.new_page()
    tablero.goto(demo.apps["tablero"])
    expect(tablero.get_by_role("heading", name="No se pudo cargar el tablero")).to_be_visible()
    expect(tablero.get_by_role("button", name="Reintentar", exact=True)).to_be_visible()
    captura(tablero, "16-sin-api-tablero")
