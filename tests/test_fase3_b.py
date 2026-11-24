"""Contratos de la cartera estrella y resultados que se muestran en la final."""
from fastapi.testclient import TestClient

from cuotaflex.api.main import app
from cuotaflex.datos import generar_cartera, indice_estacionalidad
from cuotaflex.demo.casos_estrella import casos_estrella

api = TestClient(app)


def _propuesta(caso):
    respuesta = api.post("/motor/propuesta", json=caso)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_cartera_antepone_casos_reproducibles_y_conserva_las_solicitudes_sinteticas():
    n, semilla = 4, 15
    respuesta = api.get("/motor/cartera-demo", params={"n": n, "semilla": semilla})
    assert respuesta.status_code == 200, respuesta.text
    cartera = respuesta.json()
    respuesta_alternativa = api.get("/motor/cartera-demo", params={"n": 1, "semilla": 8})
    assert respuesta_alternativa.status_code == 200, respuesta_alternativa.text
    estrellas = cartera[:3]
    assert [caso["cliente_id"] for caso in estrellas] == ["E001", "E002", "E003"]
    assert estrellas == respuesta_alternativa.json()[:3] == casos_estrella()
    assert all(len(caso["historial_ventas"]) == 24 for caso in estrellas)

    clientes, historial = generar_cartera(n, semilla, meses_historia=24)
    solicitudes = []
    for cliente in clientes.to_dict("records"):
        ventas = historial[historial["cliente_id"] == cliente["cliente_id"]].sort_values("t")
        solicitudes.append({
            **cliente,
            "historial_ventas": ventas["ventas"].tolist(),
            "indice_estacionalidad": round(indice_estacionalidad(cliente["rubro"]), 3),
        })
    assert cartera[3:] == solicitudes
    assert all(caso.keys() == solicitudes[0].keys() for caso in estrellas)


def test_e001_el_motor_elige_estacional_con_menor_default_y_cuotas_por_temporada():
    rosa, _, _ = casos_estrella()
    resultado = _propuesta(rosa)
    propuesta = resultado["propuesta"]
    seleccion = next(paso for paso in propuesta["bitacora"] if paso["paso"] == "seleccion")
    assert propuesta["valido"] and propuesta["clausula_el_nino"]
    assert propuesta["producto"] == seleccion["elegido"] == "estacional"
    comparativa = resultado["comparativa"]
    assert comparativa["fija"]["default"] - comparativa["cuotaflex"]["default"] >= 0.05
    alternativas = seleccion["candidatos"]
    assert alternativas["fija"]["default"] > alternativas["estacional"]["default"]

    siembra = [fila["cuota"] for fila in propuesta["cronograma"] if fila["mes"] in {"ene", "feb", "mar"}]
    cosecha = [fila["cuota"] for fila in propuesta["cronograma"] if fila["mes"] in {"may", "jun", "jul"}]
    assert min(cosecha) > max(siembra)


def test_e002_la_pesca_esta_cubierta_por_la_clausula():
    _, martin, _ = casos_estrella()
    propuesta = _propuesta(martin)["propuesta"]
    assert martin["rubro"] == "pesca"
    assert propuesta["valido"] and propuesta["clausula_el_nino"]


def test_e003_reduccion_por_capacidad_explicada_en_bitacora_y_chat(monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_LLM", "0")
    _, _, luis = casos_estrella()
    propuesta = _propuesta(luis)["propuesta"]
    solicitado, sugerido = propuesta["principal_solicitado"], propuesta["principal_aprobado"]
    assert luis["otras_cuotas"] > 0
    assert propuesta["valido"] and sugerido < solicitado
    assert propuesta["bitacora"][0]["sobreendeudado"]
    assert any(paso["paso"] == "replanificar" and paso["nuevo_principal"] == sugerido
               for paso in propuesta["bitacora"])

    sesion = api.post("/agente/sesion", json=luis)
    assert sesion.status_code == 200, sesion.text
    ruta = f"/agente/sesion/{sesion.json()['sesion_id']}/mensaje"
    respuesta = api.post(ruta, json={"texto": "¿Por qué bajó el monto?"})
    assert respuesta.status_code == 200, respuesta.text
    explicacion = respuesta.json()
    assert explicacion["cifras_verificadas"]
    assert explicacion["herramientas_usadas"] == ["explicar_paso_bitacora"]
    assert f"S/ {solicitado:,.2f}" in explicacion["respuesta"]
    assert f"S/ {sugerido:,.2f}" in explicacion["respuesta"]
