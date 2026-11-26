"""Exporta la vista del comité de los 3 casos estrella a PDF (A4 vertical) y, si se pide, las
capturas de la app del asesor para web/asesor/README.md.

Recorre el asistente igual que el Asesor de Negocios: carga el caso, estima el ciclo, propone el
plan y, si el motor no encuentra un plan factible, aplica el primer ajuste sugerido. Después guarda
el expediente y exporta /comite/<id>.

Requisitos: la API con los lotes A y B de la fase 4 (POST /ciclo/estimar y POST /plan/proponer) y
la app del asesor sirviéndose contra ella, por ejemplo:
    PYTHONPATH=src uvicorn cuotaflex.api.main:app --port 8000
    cd web/asesor && npm run dev
    python docs/demo/comite/exportar.py --capturas
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[3]
DESTINO_PDF = Path(__file__).resolve().parent
DESTINO_CAPTURAS = RAIZ / "web" / "asesor" / "docs"
CASOS = ("E001", "E002", "E003")


def capturar(pagina: Page, nombre: str, arriba=None):
    """Captura la ventana (1366 × 768) sin el puntero encima de un botón; `arriba` queda bajo la barra."""
    if arriba is not None:
        arriba.evaluate("e => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 72)")
    pagina.mouse.move(2, 2)
    pagina.wait_for_timeout(150)
    pagina.screenshot(path=DESTINO_CAPTURAS / nombre)


def preparar_expediente(pagina: Page, app: str, caso: str, capturas: bool) -> str:
    """Recorre los 3 pasos del asistente y devuelve el texto del estado del plan."""
    pagina.goto(f"{app}/nueva?caso={caso}")
    expect(pagina.get_by_label("Código de la solicitud")).to_have_value(caso)
    if capturas and caso == "E001":
        capturar(pagina, "nueva-1-negocio.png")
    pagina.get_by_role("button", name="Estimar ciclo →").click()
    expect(pagina.get_by_role("figure", name=re.compile("^Ciclo estimado"))).to_be_visible(timeout=30_000)
    if capturas and caso == "E001":
        capturar(pagina, "nueva-2-ciclo.png")
    pagina.get_by_role("button", name="Continuar: crédito y plan →").click()
    estado = pagina.get_by_test_id("estado-plan")
    expect(estado).to_be_visible(timeout=60_000)
    expect(pagina.get_by_text("Plan actualizado con estos datos.")).to_be_visible(timeout=60_000)
    if "Sin plan factible" in estado.inner_text():
        ajuste = pagina.get_by_role("button", name=re.compile("^Aplicar: "))
        if ajuste.count():
            if capturas:
                capturar(pagina, "nueva-3-ajustes.png", pagina.get_by_role("heading", name="Datos del crédito"))
            ajuste.first.click()
            expect(estado).to_contain_text("Plan factible", timeout=60_000)
    if capturas and caso == "E001":
        capturar(pagina, "nueva-3-plan.png", estado)
    boton = pagina.get_by_role("button", name=re.compile("(Guardar y abrir la vista del comité|Informar al comité) →"))
    expect(boton).to_be_enabled(timeout=60_000)
    texto = estado.inner_text()
    boton.click()
    expect(pagina).to_have_url(re.compile(rf"/comite/{caso}$"))
    expect(pagina.get_by_role("heading", name="1. Ciclo económico estimado")).to_be_visible()
    return texto


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", default="http://127.0.0.1:5173", help="URL de la app del asesor")
    parser.add_argument("--capturas", action="store_true", help="también guarda las capturas de web/asesor/docs/")
    args = parser.parse_args()
    DESTINO_CAPTURAS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        contexto = navegador.new_context(viewport={"width": 1366, "height": 768}, locale="es-PE")
        pagina = contexto.new_page()
        errores: list[str] = []
        pagina.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pagina.on("pageerror", lambda e: errores.append(str(e)))
        for caso in CASOS:
            estado = preparar_expediente(pagina, args.app, caso, args.capturas)
            pagina.evaluate("document.fonts.ready")
            if args.capturas and caso == "E001":
                capturar(pagina, "comite.png")
            destino = DESTINO_PDF / f"comite-{caso}.pdf"
            pagina.emulate_media(media="print")
            pagina.pdf(path=str(destino), format="A4", print_background=True, prefer_css_page_size=True)
            pagina.emulate_media(media="screen")
            paginas = len(PdfReader(str(destino)).pages)
            resumen = " ".join(estado.split())
            print(f"{caso}: {destino.relative_to(RAIZ)} · {paginas} páginas · {resumen}")
        navegador.close()
    if errores:
        raise SystemExit(f"Errores en la consola: {errores}")


if __name__ == "__main__":
    main()
