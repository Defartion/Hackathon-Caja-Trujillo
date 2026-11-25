"""Exporta el concepto v2 a PDF con Markdown y Chromium local."""

from pathlib import Path
from tempfile import TemporaryDirectory

from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

CONCEPTO = Path(__file__).resolve().parent
RAIZ = CONCEPTO.parents[2]
REPO = "https://github.com/Defartion/Hackathon-Caja-Trujillo/blob/main/"
SALIDA = CONCEPTO / "export" / "CuotaFlex-Solution-Concept-v2.pdf"

ESTILO_V2 = """
@page {
  margin: 11mm 14mm 13mm;
  @bottom-left { content: "CuotaFlex · Solution Concept v2 · Cajathón 2026 · NEG-01"; }
}

html { font-size: 10.5pt; }
body { line-height: 1.40; }
a { overflow-wrap: anywhere; word-break: normal; }
h2, h3 { break-after: avoid; }
h2 { margin-top: 10pt; }
li { break-inside: avoid; }
p { orphans: 3; widows: 3; }
thead { display: table-header-group; }
table { break-inside: auto; }
tr { break-inside: avoid; }
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
                if destino.startswith("../"):
                    ruta = (CONCEPTO / destino).resolve().relative_to(RAIZ)
                    token.attrSet("href", REPO + ruta.as_posix())

    return md.renderer.render(bloques, md.options, entorno)


def main() -> None:
    css = (CONCEPTO.parent / "export" / "estilo-pdf.css").read_text(encoding="utf-8")
    html = (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<title>CuotaFlex · Solution Concept v2</title>'
        f"<style>{css}{ESTILO_V2}</style><body>{renderizar_markdown()}</body></html>"
    )
    # Chromium carga las imágenes del repositorio desde este archivo local.
    with TemporaryDirectory() as temporal:
        entrada = Path(temporal) / "concepto.html"
        entrada.write_text(html, encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--allow-file-access-from-files"])
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
