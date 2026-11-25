import json
from pathlib import Path
from statistics import mean

import pytest
from fastapi.testclient import TestClient

from cuotaflex.api.main import app
from cuotaflex.ciclo.catalogo import cargar_patrones
from cuotaflex.ciclo.estimador import estimar_ciclo


RAIZ = Path(__file__).resolve().parents[1]
CONTRATOS = RAIZ / "tests" / "fixtures" / "contratos"
DATOS_CICLO = RAIZ / "data" / "ciclos"


def _json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.fixture
def api():
    return TestClient(app)


@pytest.fixture
def rosa():
    return _json(CONTRATOS / "ciclo_estimar_solicitud.json")


def _estimar(api, solicitud):
    respuesta = api.post("/ciclo/estimar", json=solicitud)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _etapas(periodos, etapa):
    return {int(p["periodo"][5:7]) for p in periodos if p["etapa"] == etapa}


def test_respuesta_cumple_contrato_y_es_determinista(api, rosa):
    respuesta = _estimar(api, rosa)
    ilustrativo = _json(CONTRATOS / "ciclo_estimar_respuesta.json")
    assert respuesta.keys() == ilustrativo.keys() - {"_ilustrativo"}
    assert respuesta == _estimar(api, rosa)
    assert all(respuesta[campo] == rosa[campo] for campo in (
        "cliente_id", "sector", "actividad", "zona", "fecha_inicio", "meses",
    ))
    periodos = respuesta["periodos"]
    assert len(periodos) == rosa["meses"]
    assert [p["periodo"] for p in periodos] == [p["periodo"] for p in ilustrativo["periodos"]]
    assert all(p.keys() == ilustrativo["periodos"][0].keys() for p in periodos)
    assert all(p["un_p10"] <= p["un_p50"] <= p["un_p90"] for p in periodos)
    assert respuesta["calidad"].keys() == ilustrativo["calidad"].keys()
    assert 0.75 <= respuesta["calidad"]["cobertura_p10_p90_backtest"] <= 0.85
    assert all({"nombre", "uso"} <= f.keys() <= {"nombre", "uso", "url"} for f in respuesta["fuentes"])
    assert respuesta["supuestos"] and all(isinstance(s, str) for s in respuesta["supuestos"])

    escenarios = {s["id"]: s["un"] for s in respuesta["escenarios"]}
    assert escenarios.keys() == {s["id"] for s in ilustrativo["escenarios"]}
    assert all(s.keys() == ilustrativo["escenarios"][0].keys() for s in respuesta["escenarios"])
    assert all(len(u) == len(periodos) for u in escenarios.values())
    assert escenarios["base"] == [p["un_p50"] for p in periodos]
    assert min(escenarios["el_nino"]) < min(escenarios["base"])
    assert all(adverso <= base for adverso, base in zip(escenarios["caida_precios"], escenarios["base"]))


def test_catalogo_con_patrones_datos_fuentes_y_zonas(api):
    respuesta = api.get("/ciclo/catalogo")
    assert respuesta.status_code == 200
    actividades = respuesta.json()["actividades"]
    opciones = {
        (actividad["sector"], actividad["actividad"], zona["departamento"], zona["provincia"], zona["distrito"])
        for actividad in actividades
        for zona in actividad["zonas"]
    }
    patrones = cargar_patrones()
    assert opciones == {(p.sector, p.actividad, p.departamento, p.provincia, p.distrito) for p in patrones}
    assert len(opciones) >= 12
    assert len({actividad["actividad"] for actividad in actividades}) >= 12
    assert {opcion[3] for opcion in opciones} >= {"Trujillo", "Chepén", "Pacasmayo", "Virú", "Ascope", "Sánchez Carrión"}
    for patron in patrones:
        assert len(patron.indices) == 12
        assert mean(patron.indices) == pytest.approx(1)
        assert patron.volatilidad > 0
        assert patron.fuentes and patron.supuestos


def test_arroz_campana_y_un_anual_coherente_con_captura(api, rosa):
    captura = rosa["captura"]
    captura["evidencias"] = []
    periodos = _estimar(api, rosa)["periodos"][:12]
    assert _etapas(periodos, "cima") == {6, 7}
    assert _etapas(periodos, "valle") == {1, 2, 3}
    assert sum(p["ventas_p50"] for p in periodos) == pytest.approx(
        2 * captura["ventas_mes_alto"] + 7 * captura["ventas_mes_normal"] + 3 * captura["ventas_mes_bajo"],
        abs=0.06,
    )
    gastos = sum(captura[k] for k in ("gastos_operativos", "gastos_tributarios", "carga_familiar", "otras_deudas_cuota"))
    for periodo in periodos:
        assert periodo["un_p50"] == pytest.approx(periodo["ventas_p50"] * (1 - captura["costo_ventas_pct"]) - gastos, abs=0.01)


def test_si_falta_calendario_de_captura_se_usa_el_del_catalogo(api, rosa):
    del rosa["captura"]["meses_altos"]
    del rosa["captura"]["meses_bajos"]
    periodos = _estimar(api, rosa)["periodos"]
    assert _etapas(periodos, "cima") == {6, 7}
    assert _etapas(periodos, "valle") == {1, 2, 3}


def test_prevalece_el_calendario_capturado(api, rosa):
    rosa["captura"].update(meses_altos=[8, 9], meses_bajos=[1, 2, 4], evidencias=[])
    respuesta = _estimar(api, rosa)
    assert _etapas(respuesta["periodos"], "cima") == {8, 9}
    assert _etapas(respuesta["periodos"], "valle") == {1, 2, 4}
    assert any("asesor" in s.lower() and "patrón" in s.lower() for s in respuesta["supuestos"])


def test_yape_y_boletas_acotan_sin_duplicar(api, rosa):
    rosa["captura"]["evidencias"] = []
    original = _estimar(api, rosa)
    rosa["captura"]["evidencias"] = [{"tipo": "yape", "meses": 12, "monto_promedio_mensual": 9500}]
    con_yape = _estimar(api, rosa)
    ventas = [p["ventas_p50"] for p in con_yape["periodos"][:12]]
    assert mean(ventas) == pytest.approx(9500, abs=0.01)
    assert ventas != [p["ventas_p50"] for p in original["periodos"][:12]]
    rosa["captura"]["evidencias"].append({"tipo": "Boletas", "meses": 12, "monto_promedio_mensual": 9000})
    ambas = _estimar(api, rosa)
    assert ambas["periodos"] == con_yape["periodos"]


def test_casos_estrella_en_api_con_veda_y_bodega(api):
    casos = {caso["cliente_id"]: caso for caso in _json(DATOS_CICLO / "casos_estrella.json")}
    assert casos.keys() == {"E001", "E002", "E003"}
    e001, e002, e003 = (_estimar(api, casos[id_]) for id_ in ("E001", "E002", "E003"))
    assert _etapas(e001["periodos"], "cima") == {6, 7}
    assert e002["zona"]["provincia"] == "Pacasmayo"
    assert _etapas(e002["periodos"], "valle") >= {5, 6, 7, 8, 9}
    veda = next(s["un"] for s in e002["escenarios"] if s["id"] == "veda_extendida")
    assert min(u - p["un_p50"] for u, p in zip(veda, e002["periodos"])) < 0
    assert e003["zona"]["provincia"] == "Trujillo"
    assert _etapas(e003["periodos"], "cima") == {7, 12}
    assert _etapas(e003["periodos"], "valle") == {2, 3}
    assert sum(p["un_p50"] for p in e003["periodos"]) > 0


@pytest.mark.parametrize("nivel", ["solicitud", "captura"])
def test_api_rechaza_campos_de_historial_de_pagos(api, rosa, nivel):
    contenedor = rosa if nivel == "solicitud" else rosa["captura"]
    contenedor["dias_atraso"] = 99
    respuesta = api.post("/ciclo/estimar", json=rosa)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["type"] == "extra_forbidden"


def test_estimador_independiente_de_historial_de_pagos(rosa):
    original = estimar_ciclo(rosa)
    rosa["dias_atraso"] = 90
    rosa["captura"]["dias_atraso_max"] = 60
    assert estimar_ciclo(rosa) == original
    componentes = list((RAIZ / "src" / "cuotaflex" / "ciclo").glob("*.py"))
    componentes.append(RAIZ / "src" / "cuotaflex" / "api" / "routers" / "ciclo.py")
    assert not any("dias_atraso" in p.read_text(encoding="utf-8") for p in componentes)


def test_historial_de_pagos_no_se_acepta_como_evidencia_de_venta(api, rosa):
    rosa["captura"]["evidencias"][0]["tipo"] = "historial_de_pagos"
    assert api.post("/ciclo/estimar", json=rosa).status_code == 422
    with pytest.raises(ValueError):
        estimar_ciclo(rosa)


@pytest.mark.parametrize("cambio", [
    {"meses_altos": [0]},
    {"meses_altos": [6, 6]},
    {"meses_bajos": [6]},
    {"ventas_mes_bajo": 20_000},
    {"costo_ventas_pct": 1.1},
])
def test_api_rechaza_captura_inconsistente(api, rosa, cambio):
    rosa["captura"].update(cambio)
    assert api.post("/ciclo/estimar", json=rosa).status_code == 422


def test_api_rechaza_combinacion_fuera_del_catalogo(api, rosa):
    rosa["zona"]["provincia"] = "Lima"
    assert api.post("/ciclo/estimar", json=rosa).status_code == 422
