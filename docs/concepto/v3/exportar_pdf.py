"""Exporta el concepto v3 a PDF con Markdown y Chromium local."""

from pathlib import Path
from tempfile import TemporaryDirectory

from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

CONCEPTO = Path(__file__).resolve().parent
RAIZ = CONCEPTO.parents[2]
REPO = "https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/main/"
SALIDA = CONCEPTO / "export" / "CuotaFlex-Solution-Concept-v3.pdf"

ESTILO_V3 = """
@page {
  margin: 11mm 14mm 13mm;
  @bottom-left { content: "CuotaFlex · Solution Concept v3 · Cajathón 2026 · NEG-01"; }
}

html { font-size: 10.5pt; }
body { line-height: 1.40; }
a { overflow-wrap: anywhere; word-break: normal; }
h2, h3 { break-after: avoid; }
h2 { margin-top: 10pt; }
li { break-inside: avoid; }
p { orphans: 3; widows: 3; }
thead { display: table-header-group; }
table { break-inside: avoid; }
tr { break-inside: avoid; }
img[alt^="Arquitectura"] { width: 80%; }
"""


def renderizar_markdown() -> str:
    md = MarkdownIt().enable("table")
    texto = (CONCEPTO / "CONCEPT_SOLUTION.md").read_text(encoding="utf-8")
    entorno = {}
    bloques = md.parse(texto, entorno)

    for bloque in bloques:
        for token in bloque.children or []:
            if token.type == "image":
                imagen = (CONCEPTO / token.attrGet("src")).resolve()
                token.attrSet("src", imagen.as_uri())
            elif token.type == "link_open":
                destino = token.attrGet("href")
                if not destino.startswith(("http://", "https://", "#", "mailto:")):
                    # Los enlaces relativos del repositorio apuntan a GitHub en el PDF
                    ruta = (CONCEPTO / destino).resolve().relative_to(RAIZ)
                    token.attrSet("href", REPO + ruta.as_posix())

    return md.renderer.render(bloques, md.options, entorno)


def _lanzar_navegador(playwright):
    argumentos = ["--allow-file-access-from-files"]
    try:
        return playwright.chromium.launch(args=argumentos)
    except Exception:
        # Sin el Chromium de Playwright (python -m playwright install chromium), usa Google Chrome del sistema
        return playwright.chromium.launch(channel="chrome", args=argumentos)


def main() -> None:
    css = (CONCEPTO.parent / "export" / "estilo-pdf.css").read_text(encoding="utf-8")
    html = (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<title>CuotaFlex · Solution Concept v3</title>'
        f"<style>{css}{ESTILO_V3}</style><body>{renderizar_markdown()}</body></html>"
    )
    # Chromium carga las imágenes del repositorio desde este archivo local.
    with TemporaryDirectory() as temporal:
        entrada = Path(temporal) / "concepto.html"
        entrada.write_text(html, encoding="utf-8")
        with sync_playwright() as playwright:
            browser = _lanzar_navegador(playwright)
            try:
                pagina = browser.new_page()
                pagina.goto(entrada.as_uri(), wait_until="load")
                imagenes = pagina.locator("img")
                assert imagenes.count() == 3
                assert imagenes.evaluate_all("(imgs) => imgs.every(img => img.naturalWidth > 0)")
                SALIDA.parent.mkdir(parents=True, exist_ok=True)
                pagina.pdf(path=SALIDA, print_background=True, prefer_css_page_size=True)
            finally:
                browser.close()
    print(f"PDF guardado en {SALIDA}")


if __name__ == "__main__":
    main()
