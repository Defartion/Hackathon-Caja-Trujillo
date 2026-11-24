"""Contratos del material de la final y las cifras de la fase 2."""
import hashlib
import json
import re
import zipfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
PITCH = RAIZ / "docs/pitch"
CONCEPTO = RAIZ / "docs/concepto"
RESULTADOS = RAIZ / "resultados"
PORCENTAJE = re.compile(r"(?<![\d.,])([+−-]?\d+(?:[.,]\d+)?)\s*%")
REPO = "https://github.com/Defartion/Hackathon-Caja-Trujillo"

# Huellas del concepto entregado en la fase 1, antes de añadir v2.
CONCEPTO_V1 = {
    "CONCEPT_SOLUTION.md": "57fa69bbe21548d4db0272fdc59e6df6ef79fe00aaa21829a306c07f654f95d9",
    "one-pager.md": "4dcb14e76f6e851ae20c9236a1bd2b4d7abb263e731a86affd511a12d5bf8168",
    "img/cronograma-ejemplo.png": "3904a69e5ae547511f9be1a15d6efe2d3fc657cccbadf17a23abc942b1e13be7",
    "export/CuotaFlex-Solution-Concept.pdf": "945bb96361995d09e09f5552ca5561550e7d14338d786db5b6683c4b07d378f1",
}


def _leer(archivo):
    return archivo.read_text(encoding="utf-8")


def _porcentajes(texto):
    return [Decimal(valor.replace("−", "-").replace(",", ".")) for valor in PORCENTAJE.findall(texto)]


def _porcentajes_resumen(dato):
    for clave, valor in dato.items():
        if isinstance(valor, dict):
            yield from _porcentajes_resumen(valor)
        elif clave.endswith("_pct") or clave in {"mora30_fija", "mora30_cuotaflex"}:
            yield Decimal(str(valor))


@pytest.mark.parametrize("nombre", ["GUION.md", "PREGUNTAS.md"])
def test_porcentajes_del_pitch_se_respaldan_en_resultados(nombre):
    resumen = json.loads(_leer(RESULTADOS / "resumen.json"))
    permitidos = set(_porcentajes_resumen(resumen))
    permitidos.update(_porcentajes(_leer(RESULTADOS / "CAMBIOS_FASE2.md")))
    citados = _porcentajes(_leer(PITCH / nombre))
    assert citados
    for valor in citados:
        unidad = Decimal(1).scaleb(valor.as_tuple().exponent)
        assert any(valor == base.quantize(unidad, rounding=ROUND_HALF_UP) for base in permitidos), (nombre, valor)


def test_pdf_del_pitch_contiene_las_laminas_y_el_editable():
    pdf = PdfReader(PITCH / "CuotaFlex-pitch.pdf")
    assert 10 <= len(pdf.pages) <= 12
    assert all(pagina.extract_text().strip() for pagina in pdf.pages)
    assert "Impacto estimado" in pdf.pages[5].extract_text()
    with zipfile.ZipFile(PITCH / "CuotaFlex-pitch.pptx") as editable:
        laminas = [n for n in editable.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        assert len(laminas) == len(pdf.pages)
        assert b"<a:tbl>" in editable.read("ppt/slides/slide6.xml")


def test_concepto_calibrado_por_separado_del_original():
    for ruta, huella in CONCEPTO_V1.items():
        archivo = CONCEPTO / ruta
        contenido = _leer(archivo).encode("utf-8") if archivo.suffix == ".md" else archivo.read_bytes()
        assert hashlib.sha256(contenido).hexdigest() == huella, ruta
    resumen = json.loads(_leer(RESULTADOS / "resumen.json"))
    concepto_v2 = _leer(CONCEPTO / "v2/CONCEPT_SOLUTION.md")
    for modalidad in ("fija", "cuotaflex"):
        default = Decimal(str(resumen["completo"][modalidad]["default_pct"]))
        publicado = default.quantize(Decimal(".1"), rounding=ROUND_HALF_UP)
        assert publicado in _porcentajes(concepto_v2)


def test_resumen_impreso_en_una_pagina_con_destino_del_qr():
    pdf = PdfReader(PITCH / "one-pager-final.pdf")
    assert len(pdf.pages) == 1
    anotaciones = [ref.get_object() for ref in pdf.pages[0].get("/Annots", [])]
    assert any(anotacion.get("/A", {}).get("/URI") == REPO for anotacion in anotaciones)


def test_banco_y_guion_contienen_preguntas_y_ambas_duraciones():
    preguntas = _leer(PITCH / "PREGUNTAS.md")
    assert len(re.findall(r"^### \d+ · ¿", preguntas, flags=re.MULTILINE)) >= 20
    guion = _leer(PITCH / "GUION.md")
    assert "6:20" in guion and "3:00" in guion
    assert all(caso in guion for caso in ("E001", "E002", "E003"))
