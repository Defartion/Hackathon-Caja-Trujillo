"""Pruebas del lote D con un proveedor simulado y llamadas locales al motor."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from cuotaflex.agente import AgenteAsesor
from cuotaflex.agente_chat import SesionChat
from cuotaflex.agente_chat.herramientas import Herramientas
from cuotaflex.agente_chat.llm import ClienteLLM, Llamada, RespuestaLLM
from cuotaflex.api.main import app
from cuotaflex.api.routers.asesor import ClienteSolicitud
from cuotaflex.explicador import cifras_validas, explicar


@pytest.fixture(autouse=True)
def limpiar_config_llm(monkeypatch):
    for variable in ("CUOTAFLEX_LLM", "CUOTAFLEX_LLM_PROVEEDOR", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def solicitud():
    return {"cliente_id": "SINTETICO-D", "rubro": "bodega", "ventas_medias": 7000, "margen": 0.35,
            "gasto_familiar": 1000, "principal": 6000, "plazo": 12, "tea": 0.45}


@pytest.fixture
def sesion(solicitud):
    return SesionChat(ClienteSolicitud.model_validate(solicitud))


class Stub:
    def __init__(self, texto: str = "", llamada: Llamada | None = None):
        self.texto = texto
        self.llamada = llamada
        self.mensajes = []

    def completar(self, *, sistema, mensajes, herramientas=None, plazo_fin=None):
        self.mensajes.append(mensajes.copy())
        if self.llamada and mensajes[-1]["role"] == "user":
            return RespuestaLLM(llamadas=(self.llamada,), tokens_entrada=8, tokens_salida=4)
        return RespuestaLLM(texto=self.texto, tokens_entrada=10, tokens_salida=5)


def _elegibilidad(sesion):
    return next(p for p in sesion.propuesta["bitacora"] if p["paso"] == "elegibilidad")


@pytest.mark.parametrize("texto", [
    "La TEA es 47%. Aplazar tiene costo por intereses. Tu cuota sería S/ 999,999.00.",
    "Tu préstamo fue aprobado. La TEA es 47%. Aplazar tiene costo por intereses.",
    "La TEA es 47%. Puedes aplazar si estás al día.",
    "Puedes aplazar si estás al día y aplazar genera intereses.",
])
def test_explicacion_descarta_cifras_inventadas_o_incumplimientos(sesion, monkeypatch, texto):
    stub = Stub(texto)
    monkeypatch.setattr("cuotaflex.agente_chat.llm.obtener_llm", lambda _: stub)
    respuesta = explicar(sesion.propuesta, _elegibilidad(sesion))
    assert respuesta["fuente"] == "plantilla"
    assert respuesta["cifras_verificadas"] is False
    assert "TEA" in respuesta["texto"] and "costo" in respuesta["texto"]
    payload = json.loads(stub.mensajes[0][0]["content"])
    assert set(payload) == {"propuesta", "borrador"}
    assert "cliente_id" not in payload["propuesta"]


def test_explicacion_valida_y_compatibilidad_agente(sesion, monkeypatch):
    p, eleg = sesion.propuesta, _elegibilidad(sesion)
    cliente = explicar(p, eleg, audiencia="cliente")
    asesor = explicar(p, eleg, audiencia="asesor")
    assert cliente["fuente"] == asesor["fuente"] == "plantilla"
    assert cliente["texto"] != asesor["texto"] and "Te sugerimos" in cliente["texto"]
    assert isinstance(AgenteAsesor().explicar(p, eleg), str)
    monkeypatch.setattr("cuotaflex.agente_chat.llm.obtener_llm", lambda _: Stub(cliente["texto"]))
    assert explicar(p, eleg) == {**cliente, "fuente": "llm"}


def test_guardas_distinguen_unidad_y_redondeo():
    evidencia = {"plazo": 24, "tea": 0.4712, "principal_aprobado": 6000}
    assert cifras_validas("Monto de S/ 6.000,00 a 24 meses con TEA de 47%.", evidencia)
    assert not cifras_validas("Monto de S/ 24.", evidencia)
    assert not cifras_validas("Monto de S/ quinientos.", evidencia)
    assert not cifras_validas("El plazo sería de 23 meses.", evidencia)
    assert not cifras_validas("Monto de S/ 6.100,00.", evidencia)


def test_api_sesion_recalcula_y_actualiza_explicacion(solicitud, monkeypatch):
    monkeypatch.setenv("CUOTAFLEX_LLM_PROVEEDOR", "anthropic")
    with TestClient(app) as api:
        inicio = api.post("/agente/sesion", json=solicitud)
        assert inicio.status_code == 200
        datos = inicio.json()
        assert datos["propuesta"] == api.post("/motor/propuesta", json=solicitud).json()["propuesta"]
        sesion_id = datos["sesion_id"]
        ruta = f"/agente/sesion/{sesion_id}/mensaje"
        respuesta = api.post(ruta, json={"texto": "¿Y a 24 meses?"}).json()
        assert respuesta["fuente"] == "plantilla"
        assert respuesta["cifras_verificadas"]
        assert respuesta["herramientas_usadas"] == ["recalcular_propuesta"]
        assert respuesta["propuesta_actualizada"]["plazo"] == 24
        para_asesor = api.get("/agente/explicacion", params={"sesion_id": sesion_id, "audiencia": "asesor"})
        assert para_asesor.status_code == 200 and "24 meses" in para_asesor.json()["texto"]
        assert api.get("/agente/explicacion", params={"sesion_id": "desconocida"}).status_code == 404
        assert api.post(ruta, json={"texto": " "}).status_code == 422


def test_simulacion_reutiliza_los_escenarios_del_motor(sesion, solicitud):
    with TestClient(app) as api:
        comparativa = api.post("/motor/propuesta", json=solicitud).json()["comparativa"]
    resultado = sesion.responder("¿Puedes simular el riesgo de mora?")
    assert resultado["herramientas_usadas"] == ["simular_cliente"]
    evidencia, = sesion.evidencia_respuesta
    assert evidencia["n_escenarios"] == comparativa["n_escenarios"]
    for modalidad in ("fija", "cuotaflex"):
        assert evidencia[modalidad] == {k: v for k, v in comparativa[modalidad].items() if k != "cuotas"}


def test_chat_llm_utiliza_herramienta_y_sus_cifras(sesion):
    llm = Stub("El motor contempla S/ 6,000.00 a 24 meses.", Llamada("calc", "recalcular_propuesta", {"plazo": 24}))
    respuesta = sesion.responder("¿Y a 24 meses?", cliente_llm=llm)
    assert respuesta["fuente"] == "llm" and respuesta["cifras_verificadas"]
    assert respuesta["propuesta_actualizada"]["plazo"] == 24
    assert json.loads(llm.mensajes[1][-1]["content"])["plazo"] == 24
    assert sesion.uso_llm == {"tokens_entrada": 18, "tokens_salida": 9}


def test_chat_descarta_borrador_y_cambios_no_aplicados(sesion):
    llm = Stub("El monto es de S/ 999,999.99.", Llamada("calc", "recalcular_propuesta", {"plazo": 24}))
    respuesta = sesion.responder("¿Por qué este producto?", cliente_llm=llm)
    assert respuesta["fuente"] == "plantilla" and respuesta["cifras_verificadas"]
    assert respuesta["herramientas_usadas"] == ["explicar_paso_bitacora"]
    assert "999,999" not in respuesta["respuesta"]
    assert "propuesta_actualizada" not in respuesta and sesion.propuesta["plazo"] == 12


def test_chat_rechaza_respuesta_del_modelo_sin_herramientas(sesion):
    respuesta = sesion.responder("Una consulta fuera del contexto", cliente_llm=Stub("El monto es de S/ 6,000.00."))
    assert respuesta["fuente"] == "plantilla"
    assert not respuesta["herramientas_usadas"] and not respuesta["cifras_verificadas"]


def test_limite_por_pregunta_incluye_la_herramienta_de_respaldo(sesion, monkeypatch):
    llamadas = []
    ejecutar = Herramientas.ejecutar

    def registrar(self, nombre, argumentos):
        llamadas.append(nombre)
        return ejecutar(self, nombre, argumentos)

    class Reiterativo:
        def completar(self, **kwargs):
            return RespuestaLLM(llamadas=(Llamada(str(len(llamadas)), "consultar_politica", {"tema": "credito"}),))

    monkeypatch.setattr(Herramientas, "ejecutar", registrar)
    respuesta = sesion.responder("¿Y a 24 meses?", cliente_llm=Reiterativo())
    assert respuesta["fuente"] == "plantilla"
    assert len(llamadas) == 4 and llamadas[-1] == "recalcular_propuesta"
    assert sesion.propuesta["plazo"] == 24


def test_rango_admitido_y_recalculo_invalido(solicitud):
    with TestClient(app) as api:
        inicio = api.post("/agente/sesion", json={**solicitud, "plazo": 36})
        assert inicio.status_code == 200 and inicio.json()["propuesta"]["plazo"] == 36
        ruta = f"/agente/sesion/{inicio.json()['sesion_id']}/mensaje"
        respuesta = api.post(ruta, json={"texto": "¿Y a -24 meses?"}).json()
        assert "propuesta_actualizada" not in respuesta


@pytest.mark.parametrize(("proveedor", "clave"), [("anthropic", "ANTHROPIC_API_KEY"), ("openai", "OPENAI_API_KEY")])
def test_adaptadores_transmiten_llamadas_y_resultados(sesion, monkeypatch, proveedor, clave):
    monkeypatch.setenv("CUOTAFLEX_LLM_PROVEEDOR", proveedor)
    monkeypatch.setenv(clave, "credencial-ficticia")
    peticiones = []
    parametros = {"plazo": 24}
    nombre = "recalcular_propuesta"

    def simular_http(url, cabeceras, cuerpo, plazo_fin):
        peticiones.append(cuerpo)
        if proveedor == "anthropic":
            bloques = [{"type": "text", "text": "El plazo propuesto es de 24 meses."}]
            if len(peticiones) == 1:
                bloques = [{"type": "tool_use", "id": "calc", "name": nombre, "input": parametros}]
            return {"content": bloques, "usage": {"input_tokens": 100, "output_tokens": 20}}
        mensaje = {"content": "El plazo propuesto es de 24 meses."}
        if len(peticiones) == 1:
            mensaje = {"content": None, "tool_calls": [
                {"id": "calc", "function": {"name": nombre, "arguments": json.dumps(parametros)}},
            ]}
        return {"choices": [{"message": mensaje}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}

    monkeypatch.setattr(ClienteLLM, "_enviar", staticmethod(simular_http))
    respuesta = sesion.responder("¿Y a 24 meses?")
    assert respuesta["fuente"] == "llm" and respuesta["propuesta_actualizada"]["plazo"] == 24
    assert sesion.uso_llm == {"tokens_entrada": 200, "tokens_salida": 40}
    ultimo = peticiones[-1]["messages"][-1]
    if proveedor == "anthropic":
        bloque, = ultimo["content"]
        assert bloque["type"] == "tool_result" and bloque["tool_use_id"] == "calc"
        contenido = bloque["content"]
    else:
        assert ultimo["role"] == "tool" and ultimo["tool_call_id"] == "calc"
        contenido = ultimo["content"]
    assert json.loads(contenido)["plazo"] == 24
