"""Comprueba el concepto original y la versión calibrada de la fase 3."""
import importlib.util
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
CONCEPTO = RAIZ / "docs" / "concepto"
# El concepto se entregó con las cifras de la fase 1: se compara contra esa foto, no contra la corrida vigente.
# Las cifras calibradas de la fase 2 están en resultados/resumen.json y resultados/CAMBIOS_FASE2.md.
RESUMEN = json.loads((RAIZ / "resultados" / "fase1" / "resumen.json").read_text(encoding="utf-8"))
COMPLETO, SOLO = RESUMEN["completo"], RESUMEN["solo_cronograma"]
ACTUAL = json.loads((RAIZ / "resultados" / "resumen.json").read_text(encoding="utf-8"))
PNG = b"\x89PNG\r\n\x1a\n"


def _redondeo(valor, decimales=1) -> Decimal:
    """Redondeo comercial (mitad hacia arriba), como se publican las cifras."""
    return Decimal(str(valor)).quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


def _pct(valor, decimales=1) -> str:
    return f"{_redondeo(valor, decimales)}%"


def _delta(valor) -> str:
    """Variación relativa entera con signo menos tipográfico: -55.2 -> '−55%'."""
    v = _redondeo(valor, 0)
    return f"−{abs(v)}%" if v < 0 else f"+{v}%"


def _miles(valor) -> str:
    return f"S/ {_redondeo(Decimal(str(valor)) / 1000, 0)} mil"


def _texto(nombre: str) -> str:
    return (CONCEPTO / nombre).read_text(encoding="utf-8")


def _fila(doc: str, inicio: str) -> str:
    return next(linea for linea in doc.splitlines() if linea.startswith(inicio))


@pytest.fixture(scope="module")
def figuras():
    spec = importlib.util.spec_from_file_location("generar_figuras", CONCEPTO / "generar_figuras.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def ejemplo(figuras):
    cliente, propuesta = figuras.elegir_ejemplo()
    return figuras.datos_cronograma(cliente, propuesta)


def test_tabla_de_impacto_coincide_con_resumen():
    doc = _texto("CONCEPT_SOLUTION.md")
    atraso = _fila(doc, "| Créditos con atraso > 30 días")
    default = _fila(doc, "| Default")
    margen = _fila(doc, "| Margen neto / cartera")
    total = _fila(doc, "| Margen neto total")
    cartera = _fila(doc, "| Cartera colocada")
    for clave, fila in (("mora30_pct", atraso), ("default_pct", default), ("margen_sobre_cartera_pct", margen)):
        esperado = [_pct(COMPLETO["fija"][clave]), _pct(COMPLETO["cuotaflex"][clave]), _pct(SOLO["cuotaflex"][clave])]
        celdas = [c.strip().strip("*").split(" ")[0] for c in fila.strip("|").split("|")[1:]]
        assert [c.replace("**", "") for c in celdas] == esperado, fila
    assert COMPLETO["fija"] == SOLO["fija"]  # la línea base es la misma en las dos variantes
    for clave, fila in (("mora30_relativa_pct", atraso), ("default_relativo_pct", default)):
        assert _delta(COMPLETO["delta"][clave]) in fila and _delta(SOLO["delta"][clave]) in fila
    for valor in (COMPLETO["fija"]["margen_neto_total"], COMPLETO["cuotaflex"]["margen_neto_total"],
                  SOLO["cuotaflex"]["margen_neto_total"]):
        assert _miles(valor) in total
    assert f"+{_miles(COMPLETO['delta']['margen_neto_dif'])}" in total
    assert f"+{_miles(SOLO['delta']['margen_neto_dif'])}" in total
    cartera_m = lambda v: f"S/ {_redondeo(Decimal(str(v)) / 1_000_000, 2)} M"  # noqa: E731
    assert cartera_m(COMPLETO["fija"]["cartera"]) in cartera and cartera_m(COMPLETO["cuotaflex"]["cartera"]) in cartera
    variacion = 100 * (COMPLETO["cuotaflex"]["cartera"] / COMPLETO["fija"]["cartera"] - 1)
    assert _delta(variacion) in cartera


def test_cifras_del_texto_coinciden_con_resumen():
    doc = _texto("CONCEPT_SOLUTION.md")
    fija, cf = COMPLETO["fija"], COMPLETO["cuotaflex"]
    resumen = doc.split("## Resumen ejecutivo")[1].split("## 1.")[0]
    for cifra in (_pct(fija["mora30_pct"]), _pct(cf["mora30_pct"]), _pct(fija["margen_sobre_cartera_pct"]),
                  _pct(cf["margen_sobre_cartera_pct"])):
        assert cifra in resumen
    caida_cartera = abs(_redondeo(100 * (cf["cartera"] / fija["cartera"] - 1), 0))
    assert f"{caida_cartera}% menos colocación" in resumen
    # Parte del efecto que se logra solo con el cronograma frente al efecto completo
    solo = _redondeo(fija["mora30_pct"] - SOLO["cuotaflex"]["mora30_pct"])
    completo = _redondeo(fija["mora30_pct"] - cf["mora30_pct"])
    assert f"el atraso baja {solo} puntos; con el dimensionamiento, baja {completo}" in doc
    rubros = COMPLETO["por_rubro"]
    for rubro in ("agricultura", "pesca"):
        assert f"{_pct(rubros[rubro]['mora30_fija'])} a {_pct(rubros[rubro]['mora30_cuotaflex'])}" in doc
    for rubro in ("calzado", "comercio_campana"):
        r = SOLO["por_rubro"][rubro]
        assert f"{_pct(r['mora30_fija'])} a {_pct(r['mora30_cuotaflex'])}" in doc


def test_one_pager_coincide_con_resumen():
    doc = _texto("one-pager.md")
    fija, cf = COMPLETO["fija"], COMPLETO["cuotaflex"]
    for clave in ("mora30_pct", "default_pct", "margen_sobre_cartera_pct"):
        assert _pct(fija[clave]) in doc and _pct(cf[clave]) in doc
    assert f"{abs(_redondeo(100 * (cf['cartera'] / fija['cartera'] - 1), 0))}% menor" in doc


def test_documento_sigue_los_componentes_oficiales():
    doc = _texto("CONCEPT_SOLUTION.md")
    componentes = ["Problema abordado", "Concepto de solución", "Impacto esperado", "Enfoque tecnológico",
                   "Tecnología preexistente", "Funcionalidad crítica", "Nivel de desarrollo esperado",
                   "Factibilidad y dependencias"]
    posiciones = [doc.index(f"## {i}. {nombre}") for i, nombre in enumerate(componentes, start=1)]
    assert posiciones == sorted(posiciones)
    resumen = doc.split("## Resumen ejecutivo")[1].split("## 1.")[0]
    assert len(resumen.split()) <= 150


def test_diagramas_con_png_y_fuente():
    img = CONCEPTO / "img"
    for nombre in ("arquitectura", "flujo-agente"):
        assert (img / f"{nombre}.mmd").read_text(encoding="utf-8").strip()
        assert (img / f"{nombre}.png").read_bytes()[:8] == PNG
    assert (img / "cronograma-ejemplo.png").read_bytes()[:8] == PNG


def test_ejemplo_de_la_figura_1_coincide_con_el_texto_v2(ejemplo):
    assert ejemplo["exceso_estacional"] < ejemplo["exceso_fija"]
    leyenda = _texto("v2/CONCEPT_SOLUTION.md").split("*Figura 1.")[1].split("*")[0]
    assert ejemplo["cliente_id"] in leyenda
    assert f"S/ {ejemplo['principal_aprobado']:,.0f} a {ejemplo['plazo']} meses" in leyenda
    assert f"en {ejemplo['meses_exceso_fija']} meses (S/ {ejemplo['exceso_fija']:,.0f} en total)" in leyenda
    assert f"en {ejemplo['meses_exceso_estacional']} (S/ {ejemplo['exceso_estacional']:,.0f})" in leyenda

    original = (CONCEPTO / "img" / "cronograma-ejemplo.png").read_bytes()
    regenerada = (CONCEPTO / "v2" / "img" / "cronograma-ejemplo.png").read_bytes()
    assert regenerada.startswith(PNG)
    assert regenerada != original


@pytest.mark.parametrize("nombre", ["CONCEPT_SOLUTION.md", "one-pager.md"])
def test_cifras_v2_coinciden_con_resumen_vigente(nombre):
    doc = _texto(f"v2/{nombre}")
    completo, solo = ACTUAL["completo"], ACTUAL["solo_cronograma"]
    indicadores = {
        "mora30_pct": "| Créditos con atraso > 30 días",
        "default_pct": "| Default",
        "margen_sobre_cartera_pct": "| Margen neto / cartera",
    }
    for clave, indicador in indicadores.items():
        fila = _fila(doc, indicador)
        valores = [completo["fija"][clave], completo["cuotaflex"][clave], solo["cuotaflex"][clave]]
        celdas = [celda.strip().replace("**", "").split(" ")[0] for celda in fila.strip("|").split("|")[1:]]
        assert celdas == [_pct(valor) for valor in valores], fila

    fila = _fila(doc, "| Cartera colocada")
    carteras = [completo["fija"]["cartera"], completo["cuotaflex"]["cartera"], solo["cuotaflex"]["cartera"]]
    for celda, valor in zip(fila.strip("|").split("|")[1:], carteras, strict=True):
        millones = _redondeo(Decimal(str(valor)) / 1_000_000, 2)
        assert f"S/ {millones} M" in celda

    caida = abs(_redondeo(100 * (completo["cuotaflex"]["cartera"] / completo["fija"]["cartera"] - 1), 0))
    assert f"{caida}%" in doc
    assert "SBS" in doc and "simulación" in doc


def test_impacto_absoluto_y_relativo_v2():
    doc = _texto("v2/CONCEPT_SOLUTION.md")
    completo, solo = ACTUAL["completo"], ACTUAL["solo_cronograma"]
    for clave, etiqueta in (
        ("mora30_relativa_pct", "| Créditos con atraso > 30 días"),
        ("default_relativo_pct", "| Default"),
    ):
        fila = _fila(doc, etiqueta)
        assert _delta(completo["delta"][clave]) in fila
        assert _delta(solo["delta"][clave]) in fila
    total = _fila(doc, "| Margen neto total")
    assert _miles(completo["fija"]["margen_neto_total"]) in total
    for modo in (completo, solo):
        assert _miles(modo["cuotaflex"]["margen_neto_total"]) in total
        assert f"+{_miles(modo['delta']['margen_neto_dif'])}" in total


def test_exportacion_pdf_del_concepto_v2():
    ruta = CONCEPTO / "v2" / "export" / "CuotaFlex-Solution-Concept-v2.pdf"
    pdf = PdfReader(ruta)
    texto = " ".join(pagina.extract_text() for pagina in pdf.pages)
    assert "Versión 2" in texto
    assert "Figura 1." in texto
    for modo in ("fija", "cuotaflex"):
        assert _pct(ACTUAL["completo"][modo]["default_pct"]) in texto


def test_script_de_figuras_genera_el_png(figuras, tmp_path):
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        pytest.skip("matplotlib no está instalado: pip install -r requirements-lote-d-concepto.txt")
    ruta = figuras.main(["--salida", str(tmp_path / "cronograma.png")])
    assert ruta.read_bytes()[:8] == PNG


def test_concepto_md_queda_como_puntero():
    texto = (RAIZ / "docs" / "CONCEPTO.md").read_text(encoding="utf-8")
    assert "concepto/CONCEPT_SOLUTION.md" in texto
    assert "## " not in texto  # sin secciones propias: solo apunta a docs/concepto/
