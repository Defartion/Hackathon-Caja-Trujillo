"""Genera el resumen impreso de Thinku a partir del resultado calibrado.

Desde la raíz del repositorio: python docs/pitch/generar_one_pager.py
Requiere ReportLab (python -m pip install reportlab).
"""

import json
from pathlib import Path

from reportlab import rl_config
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

RAIZ = Path(__file__).resolve().parents[2]
REPO = "https://github.com/Defartion/Hackathon-Caja-Trujillo"
PAPEL = HexColor("#F7F4ED")
TINTA = HexColor("#142728")
SECUNDARIO = HexColor("#435657")
ROJO = HexColor("#BD2337")
VERDE = HexColor("#136C63")
VERDE_CLARO = HexColor("#E6F0EA")
LINEA = HexColor("#D1D7CB")

ANCHO, ALTO = A4
MARGEN = 43
DERECHA = ANCHO - MARGEN
CONTENIDO = ANCHO - 2 * MARGEN


def texto(pdf, x, y, contenido, tamano=11, *, negrita=False, color=TINTA, alinear="izquierda"):
    fuente = "Helvetica-Bold" if negrita else "Helvetica"
    pdf.setFont(fuente, tamano)
    pdf.setFillColor(color)
    if alinear == "derecha":
        pdf.drawRightString(x, ALTO - y, contenido)
    else:
        pdf.drawString(x, ALTO - y, contenido)


def parrafo(pdf, x, y, contenido, ancho, *, tamano=11, interlinea=15, color=SECUNDARIO):
    lineas = simpleSplit(contenido, "Helvetica", tamano, ancho)
    for indice, linea in enumerate(lineas):
        texto(pdf, x, y + interlinea * indice, linea, tamano, color=color)
    return len(lineas)


def rectangulo(pdf, x, y, ancho, alto, color):
    pdf.setFillColor(color)
    pdf.rect(x, ALTO - y - alto, ancho, alto, stroke=0, fill=1)


def regla(pdf, y):
    pdf.setStrokeColor(LINEA)
    pdf.setLineWidth(0.65)
    pdf.line(MARGEN, ALTO - y, DERECHA, ALTO - y)


def porcentaje(valor):
    return f"{valor:.2f}".replace(".", ",") + " %"


def millones(valor):
    return ("S/ " + f"{valor / 1_000_000:.2f}" + " M").replace(".", ",")


def tabla_impacto(pdf, completo):
    filas = (
        ("Créditos con atraso > 30 días", "mora30_pct", porcentaje),
        ("Default (3 cuotas impagas seguidas)", "default_pct", porcentaje),
        ("Margen neto / cartera", "margen_sobre_cartera_pct", porcentaje),
        ("Cartera colocada", "cartera", millones),
    )
    x_fija = MARGEN + CONTENIDO * 0.72
    x_flex = DERECHA - 14
    rectangulo(pdf, x_fija + 17, 257, DERECHA - x_fija - 17, 178, VERDE_CLARO)
    texto(pdf, MARGEN + 4, 276, "Indicador", 10, negrita=True, color=SECUNDARIO)
    texto(pdf, x_fija, 276, "Cuota fija", 10, negrita=True, color=SECUNDARIO, alinear="derecha")
    texto(pdf, x_flex, 276, "Thinku", 10, negrita=True, color=VERDE, alinear="derecha")
    for indice, (etiqueta, clave, formato) in enumerate(filas):
        y = 310 + indice * 37
        regla(pdf, y - 21)
        texto(pdf, MARGEN + 4, y, etiqueta, 11, negrita=clave == "default_pct")
        texto(pdf, x_fija, y, formato(completo["fija"][clave]), 15, alinear="derecha")
        texto(pdf, x_flex, y, formato(completo["cuotaflex"][clave]), 16, negrita=True,
              color=VERDE, alinear="derecha")
    regla(pdf, 435)


def codigo_qr(pdf, x, y, tamano):
    qr = QrCodeWidget(REPO, barLevel="M", barBorder=4)
    x1, y1, x2, y2 = qr.getBounds()
    ancho, alto = tamano / (x2 - x1), tamano / (y2 - y1)
    dibujo = Drawing(tamano, tamano, transform=[ancho, 0, 0, alto, -x1 * ancho, -y1 * alto])
    dibujo.add(qr)
    rectangulo(pdf, x, y, tamano, tamano, white)
    renderPDF.draw(dibujo, pdf, x, ALTO - y - tamano)
    pdf.linkURL(REPO, (x, ALTO - y - tamano, x + tamano, ALTO - y), relative=0)


def generar():
    resumen = json.loads((RAIZ / "resultados/resumen.json").read_text(encoding="utf-8"))
    destino = Path(__file__).with_name("one-pager-final.pdf")
    pdf = canvas.Canvas(str(destino), pagesize=A4, pageCompression=1, invariant=1)
    pdf.setTitle("Thinku | Resumen para el jurado")
    pdf.setAuthor("Equipo Thinku")
    pdf.setSubject("Cajathón 2026 | Impacto en una cartera sintética calibrada")
    rectangulo(pdf, 0, 0, ANCHO, ALTO, PAPEL)

    rectangulo(pdf, MARGEN, 33, 29, 3.5, ROJO)
    texto(pdf, MARGEN, 54, "CAJATHÓN 2026  /  DESAFÍO NEG-01", 9, negrita=True, color=SECUNDARIO)
    texto(pdf, DERECHA, 54, "RESUMEN PARA EL JURADO", 9, negrita=True, color=SECUNDARIO, alinear="derecha")
    texto(pdf, MARGEN - 3, 112, "Thinku", 51, negrita=True)
    texto(pdf, MARGEN, 144, "Cuotas que se adaptan al flujo del negocio", 20, negrita=True)
    parrafo(pdf, MARGEN, 174,
            "En la demo, Rosa cultiva arroz en Chepén y tiene más liquidez en cosecha. Thinku ayuda al asesor "
            "a programar cuotas más bajas en siembra y más altas cuando el negocio vende más.",
            CONTENIDO, tamano=11.5, interlinea=15.5)

    texto(pdf, MARGEN, 225, "Resultados en simulación", 23, negrita=True)
    texto(pdf, MARGEN, 245, "600 créditos sintéticos × 200 escenarios por crédito", 10.5, color=SECUNDARIO)
    tabla_impacto(pdf, resumen["completo"])

    solo = resumen["solo_cronograma"]
    fija = porcentaje(solo["fija"]["default_pct"])
    flex = porcentaje(solo["cuotaflex"]["default_pct"])
    parrafo(pdf, MARGEN, 460,
            f"Con el mismo monto y plazo, el default pasa de {fija} a {flex}. "
            "La simulación completa incorpora el ajuste de monto y plazo y coloca menos cartera.",
            CONTENIDO, tamano=10.5, interlinea=14)
    texto(pdf, MARGEN, 501, "Cartera sintética calibrada con referencias de mora de la SBS.", 9, color=SECUNDARIO)

    texto(pdf, MARGEN, 542, "Decisión de crédito", 23, negrita=True)
    pasos = (
        ("Pronóstico", "Estima las ventas y usa el escenario conservador p25 para evaluar la capacidad de pago."),
        ("Elección", "Simula cuota fija, cuota con aplazamientos y cuota estacional. Optimiza el cronograma."),
        ("Explicación", "El agente verifica las cifras y muestra el costo de aplazar y la TEA."),
    )
    for indice, (titulo, detalle) in enumerate(pasos):
        y = 574 + indice * 33
        regla(pdf, y - 14)
        texto(pdf, MARGEN + 4, y, titulo, 11.5, negrita=True, color=VERDE)
        parrafo(pdf, MARGEN + 116, y, detalle, CONTENIDO - 118, tamano=10.5, interlinea=12.5)
    regla(pdf, 662)
    parrafo(pdf, MARGEN, 682,
            "ENFEN aporta la alerta oficial que habilita el alivio pactado. La API replica préstamos en Apache Fineract.",
            CONTENIDO, tamano=10, interlinea=13)

    regla(pdf, 717)
    texto(pdf, MARGEN, 743, "Repositorio de Thinku", 16, negrita=True)
    texto(pdf, MARGEN, 763, "Código, metodología, demo y evidencias de la final.", 10, color=SECUNDARIO)
    enlace = "github.com/Defartion/Hackathon-Caja-Trujillo"
    texto(pdf, MARGEN, 784, enlace, 9.5, color=VERDE)
    pdf.linkURL(REPO, (MARGEN, ALTO - 789, MARGEN + stringWidth(enlace, "Helvetica", 9.5), ALTO - 771),
                relative=0)
    codigo_qr(pdf, DERECHA - 74, 724, 74)
    texto(pdf, MARGEN, 818, "Fuentes  resultados/resumen.json · resultados/CAMBIOS_FASE2.md", 8, color=SECUNDARIO)
    pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    rl_config.useA85 = False
    generar()
