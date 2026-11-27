"""Lote 3 en el navegador: columnas de la bandeja y menús plegables.

Ejecutar: pytest tests/e2e/test_columnas_y_paneles.py
"""
from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.e2e

POR_DEFECTO = ["Código", "Rubro", "Región", "Monto", "Plazo", "Atraso máx.", "Estacionalidad", ""]
RIESGO = ["Código", "Rubro", "Monto", "Ventas medias", "Margen", "Gasto familiar", "Otras cuotas", "Atraso máx.",
          "Estacionalidad", ""]
COMPACTA = re.compile(r"\bcompacta\b")


@pytest.fixture
def comprobar(navegador):
    from playwright.sync_api import expect

    return expect


def test_asesor_elige_las_columnas_de_la_bandeja(demo, explorador, comprobar):
    contexto, _ = explorador
    pagina = contexto.new_page()
    pagina.goto(demo.apps["asesor"])
    comprobar(pagina.get_by_role("cell", name="E001", exact=True)).to_be_visible(timeout=25_000)
    cabecera = pagina.locator(".tabla-bandeja thead th")
    tabla = pagina.locator(".tabla-bandeja")
    comprobar(cabecera).to_have_text(POR_DEFECTO)

    boton = pagina.get_by_role("button", name="Columnas")
    boton.click()
    panel = pagina.get_by_role("dialog", name="Columnas de la tabla")
    comprobar(panel.get_by_role("button", name="Recomendadas")).to_have_attribute("aria-pressed", "true")
    comprobar(panel.get_by_role("checkbox", name="Código")).to_be_disabled()
    panel.get_by_role("button", name="Capacidad y riesgo").click()
    comprobar(cabecera).to_have_text(RIESGO)

    panel.get_by_role("checkbox", name="Región").check()
    comprobar(cabecera.nth(2)).to_have_text("Región")
    comprobar(panel.get_by_role("button", name="Capacidad y riesgo")).to_have_attribute("aria-pressed", "false")
    panel.get_by_role("radio", name="Compactas").click()
    comprobar(tabla).to_have_class(COMPACTA)
    pagina.keyboard.press("Escape")
    comprobar(panel).to_be_hidden()
    comprobar(boton).to_contain_text("9/13")

    # La elección se guarda en el navegador del asesor.
    pagina.reload()
    comprobar(cabecera.nth(2)).to_have_text("Región", timeout=25_000)
    comprobar(cabecera).to_have_count(len(RIESGO) + 1)
    comprobar(tabla).to_have_class(COMPACTA)

    boton.click()
    panel.get_by_role("button", name="Restablecer").click()
    comprobar(cabecera).to_have_text(POR_DEFECTO)
    comprobar(tabla).not_to_have_class(COMPACTA)
    panel.get_by_role("button", name="Listo").click()
    comprobar(panel).to_be_hidden()


def test_asesor_pliega_el_menu_lateral(demo, explorador, comprobar):
    contexto, _ = explorador
    pagina = contexto.new_page()
    pagina.goto(demo.apps["asesor"])
    comprobar(pagina.get_by_role("cell", name="E001", exact=True)).to_be_visible(timeout=25_000)

    pagina.get_by_role("button", name="Plegar el menú").click()
    comprobar(pagina.get_by_role("button", name="Mostrar el menú completo")).to_have_attribute("aria-expanded", "false")
    pagina.wait_for_function("document.querySelector('.lateral').getBoundingClientRect().width < 90")
    assert pagina.evaluate("document.documentElement.scrollWidth <= innerWidth")

    # Los iconos conservan su nombre para lectores de pantalla y siguen navegando.
    pagina.get_by_role("link", name="Nueva solicitud").click()
    comprobar(pagina).to_have_url(re.compile(r"/nueva$"))
    pagina.reload()
    comprobar(pagina.get_by_role("button", name="Mostrar el menú completo")).to_be_visible(timeout=25_000)

    pagina.get_by_role("button", name="Mostrar el menú completo").click()
    pagina.wait_for_function("document.querySelector('.lateral').getBoundingClientRect().width > 200")
    comprobar(pagina.get_by_role("button", name="Plegar el menú")).to_have_attribute("aria-expanded", "true")


def test_supervisor_pliega_el_menu_y_los_controles(demo, explorador, comprobar):
    contexto, _ = explorador
    pagina = contexto.new_page()
    pagina.goto(demo.apps["tablero"])
    comprobar(pagina.locator(".cab-corrida")).to_be_visible(timeout=120_000)
    base = pagina.get_by_role("button", name="Base", exact=True)
    comprobar(base).to_be_visible()

    # Paso 1 como acordeón: cerrado, muestra el escenario activo.
    paso = pagina.get_by_role("button", name="1. Elige un escenario")
    comprobar(paso).to_have_attribute("aria-expanded", "true")
    paso.click()
    comprobar(paso).to_have_attribute("aria-expanded", "false")
    comprobar(paso).to_contain_text("Base")
    comprobar(base).to_be_hidden()
    paso.click()
    comprobar(base).to_be_visible()

    # Panel de controles reducido a una columna con el botón de simular.
    pagina.get_by_role("button", name="Plegar los controles").click()
    comprobar(base).to_be_hidden()
    comprobar(pagina.get_by_role("button", name="Volver a simular")).to_be_visible()
    pagina.wait_for_function("document.querySelector('.panel').getBoundingClientRect().width < 80")

    # Menú del supervisor solo con iconos.
    pagina.get_by_role("button", name="Plegar el menú").click()
    comprobar(pagina.get_by_role("button", name="Avisos a clientes")).to_be_visible()
    pagina.wait_for_function("document.querySelector('.nav-sup').getBoundingClientRect().width < 90")
    assert pagina.evaluate("document.documentElement.scrollWidth <= innerWidth")
    guardado = pagina.evaluate("[localStorage.getItem('cuotaflex.menu'), localStorage.getItem('cuotaflex.tablero.controles')]")
    assert guardado == ["plegado", "plegado"]

    pagina.get_by_role("button", name="Mostrar los controles").click()
    pagina.get_by_role("button", name="Mostrar el menú completo").click()
    comprobar(base).to_be_visible()
    comprobar(pagina.get_by_role("button", name="Plegar los controles")).to_be_visible()
