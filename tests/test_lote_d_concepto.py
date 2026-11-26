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


# --- Concepto v3 (fase 4): ajustado a las preguntas frecuentes del NEG-01 del 24 de noviembre ---
V3 = CONCEPTO / "v3"
CIFRAS_V3 = json.loads((V3 / "cifras_cuota_un.json").read_text(encoding="utf-8"))
RUBROS_V3 = {"agricultura": "Agricultura", "pesca": "Pesca", "calzado": "Calzado",
             "comercio_campana": "Comercio de campaña"}


def _texto_v3(nombre: str) -> str:
    return (V3 / nombre).read_text(encoding="utf-8")


def _celdas(fila: str) -> list[str]:
    return [celda.strip().replace("**", "") for celda in fila.strip("|").split("|")[1:]]


def _soles(valor) -> str:
    return f"S/ {int(_redondeo(valor, 0)):,}"


@pytest.fixture(scope="module")
def figura_v3():
    spec = importlib.util.spec_from_file_location("generar_figura_v3", V3 / "generar_figura.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_v3_tabla_cuota_un_coincide_con_las_cifras():
    doc = _texto_v3("CONCEPT_SOLUTION.md")
    c85, c65 = CIFRAS_V3["factor_0.85"], CIFRAS_V3["factor_0.65"]
    nino, interes = CIFRAS_V3["el_nino_factor_0.85"], CIFRAS_V3["interes_medio"]
    filas = {
        "| Clientes con alguna etapa donde Cuota/UN > 0.85": [_pct(c85[p]["clientes_pct"]) for p in ("fija", "adaptado")],
        "| Etapas por crédito con Cuota/UN > 0.85": [str(_redondeo(c85[p]["etapas_promedio"], 2)) for p in ("fija", "adaptado")],
        "| Clientes con alguna etapa donde Cuota/UN > 0.65": [_pct(c65[p]["clientes_pct"]) for p in ("fija", "adaptado")],
        "| Escenario El Niño": [_pct(nino[p]["clientes_pct"]) for p in ("fija", "adaptado")],
        "| Interés total medio por crédito": [_soles(interes[p]) for p in ("fija", "adaptado")],
    }
    for inicio, esperado in filas.items():
        assert _celdas(_fila(doc, inicio)) == esperado, inicio
    for rubro, etiqueta in RUBROS_V3.items():
        r = CIFRAS_V3["por_rubro_factor_0.85"][rubro]
        esperado = [f"{_redondeo(r['fija_pct'], 0)}%", f"{_redondeo(r['adaptado_pct'], 0)}%"]
        assert _celdas(_fila(doc, f"| {etiqueta} |")) == esperado, etiqueta


def test_v3_lectura_honesta_coincide_con_las_cifras():
    doc = _texto_v3("CONCEPT_SOLUTION.md")
    nino = CIFRAS_V3["el_nino_factor_0.85"]
    etapas = {_redondeo(nino[p]["etapas_promedio"]) for p in ("fija", "adaptado")}
    assert len(etapas) == 1 and f"son {etapas.pop()} con ambos planes" in doc
    otros = CIFRAS_V3["por_rubro_factor_0.85"]
    fija = {_redondeo(otros[r]["fija_pct"], 0) for r in ("bodega", "servicios")}
    adaptado = {_redondeo(otros[r]["adaptado_pct"], 0) for r in ("bodega", "servicios")}
    assert len(fija) == len(adaptado) == 1
    assert f"{fija.pop()}% con la cuota fija y {adaptado.pop()}% con el plan del prototipo" in doc
    interes = CIFRAS_V3["interes_medio"]
    assert f"{_soles(interes['fija'])} con la cuota fija y {_soles(interes['adaptado'])}" in doc


def test_v3_resumen_y_componentes_oficiales():
    doc = _texto_v3("CONCEPT_SOLUTION.md")
    componentes = ["Problema abordado", "Concepto de solución", "Impacto esperado", "Enfoque tecnológico",
                   "Tecnología preexistente", "Funcionalidad crítica", "Nivel de desarrollo esperado",
                   "Factibilidad y dependencias"]
    posiciones = [doc.index(f"## {i}. {nombre}") for i, nombre in enumerate(componentes, start=1)]
    assert posiciones == sorted(posiciones)
    resumen = doc.split("## Resumen ejecutivo")[1].split("## 1.")[0]
    assert len(resumen.split()) <= 150
    c85 = CIFRAS_V3["factor_0.85"]
    assert f"{_pct(c85['fija']['clientes_pct'])} a {_pct(c85['adaptado']['clientes_pct'])}" in resumen
    assert "default" not in resumen.lower() and " mora" not in resumen.lower()  # sin titular de mora de cartera


def test_v3_cumple_la_lista_de_verificacion_de_las_faq():
    import re

    doc = _texto_v3("CONCEPT_SOLUTION.md")
    texto = doc.lower()
    # El cliente ya no aplaza cuotas ni activa alivios durante el crédito
    assert "aplaz" not in texto and "alivio" not in texto
    for termino in ("Asesor de Negocios", "Asesor de Riesgos", "comité", "vista"):
        assert termino in doc, termino
    for termino in ("TED", "base 360", "seguros", "prelación", "pendiente sin capitalizar", "TCEA"):
        assert termino in doc, termino
    # Fuentes públicas que usa el modelo de ciclo del lote B (docs/ciclo/FUENTES.md)
    for fuente in ("MIDAGRI", "SENAMHI", "INEI", "BCRP", "PRODUCE", "ENFEN", "calendarios comerciales"):
        assert fuente in doc, fuente
    # El historial de pagos solo aparece para decir que no se usa
    menciones = [m.start() for m in re.finditer("historial de pagos", doc)]
    assert menciones and all(re.search(r"(sin usar el|no usa el) $", doc[:i]) for i in menciones)
    assert "LLM externo" in doc and "créditos nuevos" in doc


def test_v3_alineado_con_los_lotes_b_y_c():
    # Validación del ciclo: resultados/ciclo_validacion.md (PR #11, 84cbd35).
    # Casos estrella: docs/demo/comite/README.md (PR #12, 9484c35).
    doc = _texto_v3("CONCEPT_SOLUTION.md")
    for cifra in ("16 combinaciones de actividad y zona", "640 clientes y 7,680 meses", "**79.8%**",
                  "rango aceptado de 75% a 85%", "MAPE de ventas p50 fue **18.5%**"):
        assert cifra in doc, cifra
    casos = {"E001 · Rosa": ["S/ 7,000 a 24 meses", "10 etapas superarían el factor"],
             "E002 · Martín": ["S/ 5,200 a 12 meses", "tope de 4 meses"],
             "E003 · Luis": ["Pide S/ 8,000 a 12 meses", "sugiere S/ 1,900"]}
    for caso, textos in casos.items():
        fila = _fila(doc, f"| **{caso}")
        assert all(t in fila for t in textos), caso
    for texto in (doc, (V3 / "img" / "arquitectura-v3.mmd").read_text(encoding="utf-8")):
        assert "SUNAT" not in texto  # el modelo de ciclo no usa SUNAT


def test_v3_figura_1_coincide_con_el_texto(figura_v3):
    cliente, propuesta = figura_v3.elegir_ejemplo()
    d = figura_v3.datos(cliente, propuesta)
    assert d["meses_sobre_adaptado"] < d["meses_sobre_fija"]
    leyenda = _texto_v3("CONCEPT_SOLUTION.md").split("*Figura 1.")[1].split("*")[0]
    assert d["cliente_id"] in leyenda
    assert f"S/ {d['principal']:,.0f} a {d['plazo']} meses" in leyenda
    assert f"en {d['meses_sobre_fija']} meses de valle y el plan del prototipo en {d['meses_sobre_adaptado']}" in leyenda


def test_v3_figuras_y_diagramas():
    img = V3 / "img"
    for nombre in ("arquitectura-v3", "flujo-plan-v3"):
        assert (img / f"{nombre}.mmd").read_text(encoding="utf-8").strip()
        assert (img / f"{nombre}.png").read_bytes()[:8] == PNG
    assert (img / "cuota-un-ejemplo.png").read_bytes()[:8] == PNG
    doc = _texto_v3("CONCEPT_SOLUTION.md")
    for nombre in ("cuota-un-ejemplo.png", "arquitectura-v3.png", "flujo-plan-v3.png"):
        assert f"(img/{nombre})" in doc


def test_v3_one_pager_coincide_con_las_cifras():
    doc = _texto_v3("one-pager.md")
    c85, nino = CIFRAS_V3["factor_0.85"], CIFRAS_V3["el_nino_factor_0.85"]
    assert _celdas(_fila(doc, "| Clientes con alguna etapa donde Cuota/UN > 0.85")) == [
        _pct(c85[p]["clientes_pct"]) for p in ("fija", "adaptado")]
    assert _celdas(_fila(doc, "| Escenario El Niño")) == [_pct(nino[p]["clientes_pct"]) for p in ("fija", "adaptado")]
    assert "Concepto v3" in doc and "Asesor de Riesgos" in doc
    assert "**79.8%**" in doc and "SUNAT" not in doc


def test_exportacion_pdf_del_concepto_v3():
    pdf = PdfReader(V3 / "export" / "CuotaFlex-Solution-Concept-v3.pdf")
    assert len(pdf.pages) <= 8
    texto = " ".join(pagina.extract_text() for pagina in pdf.pages)
    assert "Versión 3" in texto and "Figura 1." in texto and "Cuota/UN" in texto
    assert _pct(CIFRAS_V3["factor_0.85"]["adaptado"]["clientes_pct"]) in texto
