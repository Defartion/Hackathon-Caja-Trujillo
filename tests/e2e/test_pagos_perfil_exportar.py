"""Lote 2 en el navegador: elegir qué cuota pagar, detalle de la cuota, perfil, tema oscuro, exportar,
detalle del préstamo para el asesor, regla del ajuste por visita y meses en varias filas.

Ejecutar: pytest tests/e2e/test_pagos_perfil_exportar.py
"""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
import zipfile

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture
def comprobar(navegador):
    from playwright.sync_api import expect

    return expect


def _api(demo, ruta, cuerpo=None, metodo=None):
    datos = None if cuerpo is None else json.dumps(cuerpo).encode()
    pedido = urllib.request.Request(demo.api.url + ruta, data=datos, method=metodo or ("POST" if datos is not None else "GET"),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=30) as respuesta:
        return json.load(respuesta)


def _prestamo(demo) -> int:
    pedido = urllib.request.Request(demo.api.url + "/cliente/demo-seed", data=b"", method="POST")
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        return json.load(respuesta)["loanId"]


def _cliente(contexto, demo, loan_id, comprobar):
    pagina = contexto.new_page()
    pagina.goto(f"{demo.apps['cliente']}/?loanId={loan_id}")
    comprobar(pagina.get_by_role("region", name="Próxima cuota")).to_be_visible(timeout=20_000)
    return pagina


def _descargar(pagina, boton, formato, tmp_path):
    pagina.get_by_role("button", name=boton).click()
    with pagina.expect_download() as descarga:
        pagina.get_by_role("menuitem", name=re.compile(rf"^{re.escape(formato)}")).click()
    destino = tmp_path / descarga.value.suggested_filename
    descarga.value.save_as(destino)
    return destino


def test_cliente_adelanta_una_cuota_y_ve_su_detalle(demo, explorador, comprobar):
    contexto, _ = explorador
    loan_id = _prestamo(demo)
    pagina = _cliente(contexto, demo, loan_id, comprobar)

    # Detalle de la próxima cuota desde la tarjeta del inicio.
    pagina.get_by_role("button", name="Ver detalle").click()
    hoja = pagina.get_by_role("dialog", name="Cuota 1 de 12")
    comprobar(hoja).to_be_visible()
    comprobar(hoja).to_contain_text("Vence el")
    comprobar(hoja).to_contain_text("Capital")
    comprobar(hoja).to_contain_text("Saldo después de esta cuota")
    hoja.get_by_role("button", name="Cerrar detalle").click()
    comprobar(hoja).to_be_hidden()

    # Elegir la cuota 3 (adelantada) y pagarla.
    pagina.get_by_role("button", name="Pagar una cuota (demo)").click()
    comprobar(pagina.get_by_role("heading", name="Pagar una cuota")).to_be_visible()
    opciones = pagina.get_by_role("group", name="Cuotas por pagar").get_by_role("radio")
    comprobar(opciones).to_have_count(12)
    comprobar(opciones.first).to_be_checked()
    pagina.get_by_role("radio", name=re.compile(r"Cuota 3 ·")).check()
    comprobar(pagina.get_by_role("region", name="Pago elegido")).to_contain_text("Estás adelantando esta cuota")
    pagina.get_by_role("button", name=re.compile(r"^Pagar S. [\d,.]+ \(demo\)$")).click()
    comprobar(pagina.get_by_role("status")).to_contain_text("Pagaste la cuota 3")

    # La próxima sigue siendo la 1 y la 3 figura pagada.
    comprobar(pagina.get_by_role("region", name="Próxima cuota")).to_contain_text("Cuota 1 de 12")
    pagina.get_by_role("button", name="Ver mi cronograma").click()
    filas = pagina.get_by_role("list", name="Cuotas del crédito").get_by_role("listitem")
    comprobar(filas.nth(0)).to_contain_text("Cuota 1 · Próxima")
    comprobar(filas.nth(2)).to_contain_text("Cuota 3 · Pagada")
    filas.nth(2).get_by_role("button").click()
    comprobar(pagina.get_by_role("dialog", name="Cuota 3 de 12")).to_contain_text("Pagada el")

    datos = _api(demo, f"/cliente/prestamos/{loan_id}")
    assert datos["cuotasPagadas"] == 1 and datos["proximaCuota"]["numero"] == 1
    assert [f["estado"] for f in datos["cronograma"][:3]] == ["proxima", "pendiente", "pagada"]


def test_cliente_perfil_en_la_barra_y_tema_oscuro(demo, explorador, comprobar):
    contexto, _ = explorador
    loan_id = _prestamo(demo)
    pagina = _cliente(contexto, demo, loan_id, comprobar)

    barra = pagina.get_by_role("navigation", name="Navegación principal")
    comprobar(barra.get_by_role("button")).to_have_text(["Inicio", "Cronograma", "Ayuda", "Perfil"])
    comprobar(pagina.get_by_role("heading", name="Tu crédito en cifras")).to_be_visible()
    comprobar(pagina.get_by_role("heading", name="Lo que sigue")).to_be_visible()

    barra.get_by_role("button", name="Perfil").click()
    comprobar(pagina.get_by_role("heading", name="Tu crédito")).to_be_visible()
    comprobar(pagina.locator(".kv").filter(has_text="N° de crédito")).to_contain_text(str(loan_id))
    comprobar(pagina.get_by_role("radio", name="Automático")).to_be_checked()

    raiz = pagina.locator("html")
    comprobar(raiz).to_have_attribute("data-tema", "claro")
    pagina.get_by_role("radio", name="Oscuro").check()
    comprobar(raiz).to_have_attribute("data-tema", "oscuro")
    assert pagina.evaluate("localStorage.getItem('cuotaflex.tema')") == "oscuro"
    pagina.reload()
    comprobar(pagina.locator("html")).to_have_attribute("data-tema", "oscuro")
    fondo = pagina.evaluate("getComputedStyle(document.body).backgroundColor")
    assert fondo == "rgb(7, 10, 16)", fondo

    # El interruptor del menú vuelve al tema claro.
    pagina.get_by_role("button", name="Abrir menú").click()
    interruptor = pagina.get_by_role("menuitemcheckbox", name="Tema oscuro")
    comprobar(interruptor).to_have_attribute("aria-checked", "true")
    interruptor.click()
    comprobar(pagina.locator("html")).to_have_attribute("data-tema", "claro")


def test_cliente_descarga_su_cronograma_en_los_cinco_formatos(demo, explorador, comprobar, tmp_path):
    from pypdf import PdfReader

    contexto, _ = explorador
    loan_id = _prestamo(demo)
    pagina = _cliente(contexto, demo, loan_id, comprobar)
    pagina.get_by_role("button", name="Ver mi cronograma").click()
    pagina.get_by_role("button", name="Descargar").click()
    comprobar(pagina.get_by_role("menuitem")).to_have_count(5)
    pagina.keyboard.press("Escape")
    comprobar(pagina.get_by_role("menu")).to_be_hidden()

    pdf = _descargar(pagina, "Descargar", "PDF", tmp_path)
    assert pdf.name.startswith(f"cuotaflex-cronograma-credito-{loan_id}-") and pdf.suffix == ".pdf"
    contenido = pdf.read_bytes()
    assert contenido.startswith(b"%PDF-1.4") and contenido.rstrip().endswith(b"%%EOF")
    texto = "\n".join(p.extract_text() for p in PdfReader(pdf).pages)
    assert f"Mi cronograma, crédito N° {loan_id}" in texto and "Interés" in texto and "S/" in texto

    xlsx = _descargar(pagina, "Descargar", "Excel (.xlsx)", tmp_path)
    with zipfile.ZipFile(xlsx) as libro:
        assert libro.testzip() is None
        hojas = re.findall(r'<sheet name="([^"]+)"', libro.read("xl/workbook.xml").decode())
        assert hojas == ["Resumen", "Cronograma"]
        assert libro.read("xl/worksheets/sheet2.xml").decode().count("<row ") == 13

    filas = list(csv.reader(io.StringIO(_descargar(pagina, "Descargar", "CSV", tmp_path).read_text(encoding="utf-8-sig"))))
    assert filas[0][:4] == ["N°", "Mes", "Vence", "Cuota"] and len(filas) == 13
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", filas[1][2]) and float(filas[1][3]) > 0

    datos = json.loads(_descargar(pagina, "Descargar", "JSON", tmp_path).read_text(encoding="utf-8"))
    cronograma = datos["tablas"][0]
    assert cronograma["titulo"] == "Cronograma" and len(cronograma["filas"]) == 12
    assert isinstance(cronograma["filas"][0]["cuota"], float) and cronograma["filas"][0]["numero"] == 1

    txt = _descargar(pagina, "Descargar", "Texto (.txt)", tmp_path).read_text(encoding="utf-8")
    assert "Cronograma (12 filas)" in txt and "Resumen" in txt


def test_asesor_ve_el_detalle_de_un_prestamo_registrado(demo, explorador, comprobar, tmp_path):
    contexto, _ = explorador
    loan_id = _prestamo(demo)
    _api(demo, f"/cliente/prestamos/{loan_id}/pagar", {"cuota": 2})

    pagina = contexto.new_page()
    pagina.goto(f"{demo.apps['asesor']}/prestamos")
    pagina.get_by_role("link", name=f"Ver detalle del préstamo {loan_id}").click()
    comprobar(pagina.get_by_role("heading", name=f"Préstamo N° {loan_id}")).to_be_visible(timeout=20_000)
    for seccion in ("Cliente", "Condiciones", "Cuotas mes a mes", "Cronograma", "Pagos registrados", "Por qué este plan"):
        comprobar(pagina.get_by_role("heading", name=seccion, exact=True)).to_be_visible()
    tabla = pagina.locator("section").filter(has=pagina.get_by_role("heading", name="Cronograma", exact=True))
    comprobar(tabla.locator("tbody tr")).to_have_count(12)
    comprobar(tabla.locator("tbody tr").nth(1)).to_contain_text("Pagada")
    comprobar(pagina.locator(".pd-kpis")).to_contain_text("1 de 12 cuotas")

    xlsx = _descargar(pagina, "Exportar", "Excel (.xlsx)", tmp_path)
    with zipfile.ZipFile(xlsx) as libro:
        hojas = re.findall(r'<sheet name="([^"]+)"', libro.read("xl/workbook.xml").decode())
    assert hojas == ["Resumen", "Cronograma", "Pagos registrados"]

    pagina.get_by_role("link", name="Préstamos registrados").first.click()
    comprobar(pagina.get_by_role("heading", name="Préstamos registrados")).to_be_visible()
    csv_lista = _descargar(pagina, "Exportar", "CSV", tmp_path).read_text(encoding="utf-8-sig")
    assert csv_lista.startswith("N°,Cliente,Rubro,Producto,Monto")


def test_asesor_regla_del_ajuste_y_meses_en_varias_filas(demo, explorador, comprobar):
    contexto, _ = explorador
    pagina = contexto.new_page()
    pagina.goto(demo.apps["asesor"])
    pagina.get_by_role("cell", name="E001", exact=True).click()
    comprobar(pagina.get_by_role("heading", name="Propuesta del agente")).to_be_visible(timeout=25_000)

    regla = pagina.get_by_role("slider", name="Ventas según tu visita")
    comprobar(regla).to_have_attribute("aria-valuetext", "sin ajuste")
    regla.focus()
    for _ in range(3):
        pagina.keyboard.press("ArrowLeft")
    comprobar(regla).to_have_attribute("aria-valuetext", "-3% (más prudente)")
    comprobar(pagina.locator(".regla__valor")).to_have_text("−3%, más prudente")
    comprobar(pagina.locator(".regla__marcas span")).to_have_count(21)
    comprobar(pagina.locator(".regla__rotulos button")).to_have_text(["−10%", "−5%", "Sin ajuste", "+5%", "+10%"])

    pagina.goto(f"{demo.apps['asesor']}/nueva")
    meses = pagina.get_by_role("group", name="Meses altos y bajos").get_by_role("button")
    comprobar(meses).to_have_count(12)
    filas = {round(meses.nth(i).bounding_box()["y"]) for i in range(12)}
    assert len(filas) == 2, filas  # 6 meses por fila en escritorio
    comprobar(meses.first).to_contain_text("Enero")


def test_tablero_exporta_los_resultados_de_la_corrida(demo, explorador, comprobar, tmp_path):
    contexto, _ = explorador
    pagina = contexto.new_page()
    pagina.goto(demo.apps["tablero"])
    comprobar(pagina.locator(".cab-corrida")).to_be_visible(timeout=120_000)
    datos = json.loads(_descargar(pagina, "Exportar resultados", "JSON", tmp_path).read_text(encoding="utf-8"))
    titulos = [t["titulo"] for t in datos["tablas"]]
    assert titulos == ["Por estrategia", "Por rubro", "Productos asignados", "VPN por crédito", "Créditos simulados"]
    estrategias = {f["estrategia"]: f for f in datos["tablas"][0]["filas"]}
    assert set(estrategias) == {"Cuota fija", "CuotaFlex"}
    assert 0 <= estrategias["CuotaFlex"]["mora"] <= 1
