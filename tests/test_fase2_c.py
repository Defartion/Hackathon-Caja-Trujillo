"""Fase 2 · Lote C: lector del ENFEN, caché, modo demo, alertas y notificaciones.

Ninguna prueba sale a internet: las páginas y los PDF reales están en tests/fixtures/enfen/ (ver su README).
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from cuotaflex.api import main as api
from cuotaflex.api.routers import alertas
from cuotaflex.config import desglose_cronograma, tea_a_tem
from cuotaflex.integraciones import enfen
from cuotaflex.integraciones.enfen import EstadoAlerta
from cuotaflex.notificaciones import Outbox, plantillas

FIXTURES = Path(__file__).parent / "fixtures" / "enfen"
REFERENCIA = datetime(2026, 11, 23, 12, 0).astimezone()
URL_FICHA = "https://www.gob.pe/institucion/senamhi/informes-publicaciones/8827660-comunicado-oficial-enfen-n-20-2026"
URL_PDF_GOBPE = ("https://cdn.www.gob.pe/uploads/document/file/10965414/"
                 "8827660-comunicado-oficial-enfen-n-20-2026.pdf?v=1794613689")
URL_PDF_IMARPE = ("https://enfen.imarpe.gob.pe/download/comunicado-oficial-enfen-n-20-2026/"
                  "?wpdmdl=2218&refresh=6b04a663c156b1795466851")


# ---------------------------------------------------------------- utilidades

@pytest.fixture(autouse=True)
def aislado(monkeypatch, tmp_path):
    """Sin internet, con caché y bitácora temporales y el modo demo en NO_ACTIVO."""
    intentos: list[str] = []

    def sin_internet():
        def registrar(request):
            intentos.append(str(request.url))
            raise httpx.ConnectError("las pruebas no salen a internet", request=request)
        return httpx.Client(transport=httpx.MockTransport(registrar))

    monkeypatch.setattr(enfen, "nuevo_cliente_http", sin_internet)
    monkeypatch.setattr(enfen, "RUTA_CACHE", tmp_path / "enfen_cache.json")
    monkeypatch.setattr(alertas, "outbox", Outbox(tmp_path / "outbox.jsonl"))
    monkeypatch.setattr(alertas, "_eventos", [])
    for variable in ("ENFEN_MODO", "ENFEN_REVISION_AUTOMATICA", "NOTIFICACIONES_CANAL"):
        monkeypatch.delenv(variable, raising=False)
    enfen.reiniciar()
    yield
    enfen.reiniciar()
    assert not intentos, f"Una prueba intentó salir a internet: {intentos}"


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(api, "DB", {"clients": {}, "loans": {}})
    with TestClient(api.app) as c:
        yield c


def red_simulada(respuestas: dict[str, tuple[int, bytes, str]], visitas: list[str] | None = None) -> httpx.Client:
    def responder(request):
        url = str(request.url)
        if visitas is not None:
            visitas.append(url)
        codigo, cuerpo, tipo = respuestas.get(url, (404, b"", "text/plain"))
        return httpx.Response(codigo, content=cuerpo, headers={"content-type": tipo})
    return httpx.Client(transport=httpx.MockTransport(responder))


def red_caida(intentos: list[str] | None = None):
    def fallar(request):
        if intentos is not None:
            intentos.append(str(request.url))
        raise httpx.ConnectError("sin red", request=request)
    return lambda: httpx.Client(transport=httpx.MockTransport(fallar))


def paginas_reales(pdf: str = "comunicado-20-2026.pdf") -> dict[str, tuple[int, bytes, str]]:
    def html(nombre):
        return 200, (FIXTURES / nombre).read_bytes(), "text/html; charset=utf-8"
    documento = (200, (FIXTURES / pdf).read_bytes(), "application/pdf")
    return {enfen.URL_GOBPE: html("gobpe-coleccion.html"), URL_FICHA: html("gobpe-ficha-20-2026.html"),
            URL_PDF_GOBPE: documento, enfen.URL_IMARPE: html("imarpe-comunicados.html"), URL_PDF_IMARPE: documento}


def escribir_cache(numero: str, estado: EstadoAlerta, fecha: date, *, hace: timedelta, desde: date | None = None):
    leido = datetime.now().astimezone() - hace
    comunicado = enfen.Comunicado(numero, fecha, estado, None, f"https://fuente.test/{numero}.pdf", leido,
                                  f"Comunicado Oficial ENFEN N° {numero}", enfen.FUENTE_GOBPE)
    enfen._guardar_cache(enfen._Lectura(comunicado, leido, desde or fecha))


def sembrar(cliente, producto: str | None = None) -> int:
    respuesta = cliente.post("/cliente/demo-seed", params={"producto": producto} if producto else None)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["loanId"]


# ---------------------------------------------------------------- lector de comunicados

CASOS_PDF = [
    # archivo, número, fecha, estado, magnitud
    ("comunicado-20-2026.pdf", "20-2026", date(2026, 11, 13), EstadoAlerta.ALERTA_NINO, "extraordinaria"),
    ("comunicado-17-2026.pdf", "17-2026", date(2026, 9, 28), EstadoAlerta.ALERTA_NINO, "extraordinaria"),
    ("comunicado-03-2026.pdf", "03-2026", date(2026, 2, 13), EstadoAlerta.ALERTA_NINO, "débil"),
    ("comunicado-01-2026.pdf", "01-2026", date(2026, 1, 15), EstadoAlerta.VIGILANCIA_NINO, "débil"),
    ("comunicado-13-2025.pdf", "13-2025", date(2025, 12, 18), EstadoAlerta.NO_ACTIVO, None),
    ("comunicado-extraordinario-01-2025.pdf", "01-2025", date(2025, 2, 28), EstadoAlerta.VIGILANCIA_NINO, "débil"),
    ("comunicado-09-2024.pdf", "09-2024", date(2024, 6, 14), EstadoAlerta.VIGILANCIA_NINA, "débil"),
    ("comunicado-11-2022.pdf", "11-2022", date(2022, 11, 14), EstadoAlerta.ALERTA_NINA, "moderada"),
]


@pytest.mark.parametrize(("archivo", "numero", "fecha", "estado", "magnitud"), CASOS_PDF)
def test_el_parser_extrae_el_estado_de_cada_pdf_real(archivo, numero, fecha, estado, magnitud):
    comunicado = enfen.interpretar_pdf((FIXTURES / archivo).read_bytes(), url_fuente="https://fuente.test",
                                       obtenido_en=REFERENCIA)
    assert (comunicado.numero, comunicado.fecha, comunicado.estado, comunicado.magnitud) == (
        numero, fecha, estado, magnitud)


def test_el_parser_cubre_los_cinco_estados_y_los_casos_raros_del_enfen():
    assert {estado for *_, estado, _ in CASOS_PDF} == set(EstadoAlerta)
    extraordinario = enfen.interpretar_pdf((FIXTURES / "comunicado-extraordinario-01-2025.pdf").read_bytes(),
                                           url_fuente="x", obtenido_en=REFERENCIA)
    assert extraordinario.titulo == "Comunicado Extraordinario ENFEN N° 01-2025"
    # El N° 17-2026 trae la errata "28 septiembre 2027": se corrige y queda anotado.
    errata = enfen.interpretar_pdf((FIXTURES / "comunicado-17-2026.pdf").read_bytes(), url_fuente="x",
                                   obtenido_en=REFERENCIA)
    assert errata.fecha == date(2026, 9, 28)
    assert "2027" in errata.advertencias[0]


@pytest.mark.parametrize(("texto", "estado"), [
    ("COMUNICADO OFICIAL ENFEN Nº 05-2026\n13 de marzo 2026\nESTADO DEL SISTEMA\nDE ALERTA:  ALERTA DE EL NIÑO\n"
     "COSTERO1\nRESUMEN EJECUTIVO", EstadoAlerta.ALERTA_NINO),
    ("Comunicado Oficial ENFEN N° 7-2026 16 de abril 2026 Estado del sistema de alerta: Vigilan-\ncia de El Nino "
     "Costero", EstadoAlerta.VIGILANCIA_NINO),
    ("comunicado oficial enfen n.° 02-2025\n14 de febrero de 2025\nEstado del sistema de alerta: “No Activo”\n"
     "ENFEN mantiene el estado del sistema de alerta ante El Niño Costero y La Niña Costera", EstadoAlerta.NO_ACTIVO),
    ("COMUNICADO OFICIAL ENFEN N°21-2026\n27 noviembre 2026\nVigilancia de La Niña\nCostera1\nEL ENFRIAMIENTO",
     EstadoAlerta.VIGILANCIA_NINA),
    ("COMUNICADO OFICIAL ENFEN N° 22-2026 11 de diciembre 2026 Estado del sistema de alerta:AlertadeLaNiñaCostera",
     EstadoAlerta.ALERTA_NINA),
])
def test_el_parser_tolera_tildes_mayusculas_y_saltos_de_linea(texto, estado):
    assert enfen.interpretar_texto(texto, url_fuente="x", obtenido_en=REFERENCIA).estado is estado


def test_el_parser_falla_claro_si_el_comunicado_no_trae_estado():
    with pytest.raises(enfen.ComunicadoIlegible, match="estado"):
        enfen.interpretar_texto("COMUNICADO OFICIAL ENFEN N° 01-2027 15 de enero 2027 El mar se calienta.",
                                url_fuente="x", obtenido_en=REFERENCIA)


def test_los_listados_reales_apuntan_al_ultimo_comunicado():
    gobpe = enfen.candidatos_gobpe((FIXTURES / "gobpe-coleccion.html").read_text(encoding="utf-8"), enfen.URL_GOBPE)
    ultimo = max(gobpe, key=lambda c: c.orden)
    assert (ultimo.numero, ultimo.anio, ultimo.fecha, ultimo.url) == (20, 2026, date(2026, 11, 13), URL_FICHA)
    assert len(gobpe) == 25  # una página de la colección
    ficha = (FIXTURES / "gobpe-ficha-20-2026.html").read_text(encoding="utf-8")
    assert enfen.pdf_en_ficha(ficha, URL_FICHA) == URL_PDF_GOBPE
    imarpe = enfen.candidatos_imarpe((FIXTURES / "imarpe-comunicados.html").read_text(encoding="utf-8"),
                                     enfen.URL_IMARPE)
    assert [(c.numero, c.anio, c.fecha, c.url) for c in imarpe] == [(20, 2026, date(2026, 11, 13), URL_PDF_IMARPE)]


def test_obtener_ultimo_comunicado_sigue_la_estrategia_con_las_paginas_reales():
    visitas: list[str] = []
    comunicado = enfen.obtener_ultimo_comunicado(red_simulada(paginas_reales(), visitas))
    # 1. colecciones de las dos fuentes, 2. ficha y PDF del más reciente (3. pypdf y 4. regex)
    assert visitas == [enfen.URL_GOBPE, enfen.URL_IMARPE, URL_FICHA, URL_PDF_GOBPE]
    assert (comunicado.numero, comunicado.estado, comunicado.fecha) == ("20-2026", EstadoAlerta.ALERTA_NINO,
                                                                        date(2026, 11, 13))
    assert (comunicado.url_fuente, comunicado.fuente) == (URL_PDF_GOBPE, enfen.FUENTE_GOBPE)


def test_si_gobpe_no_responde_usa_la_otra_fuente_oficial():
    paginas = paginas_reales()
    paginas[enfen.URL_GOBPE] = (503, b"", "text/html")
    comunicado = enfen.obtener_ultimo_comunicado(red_simulada(paginas))
    assert (comunicado.numero, comunicado.fuente) == ("20-2026", enfen.FUENTE_IMARPE)
    # El enlace de descarga lleva un token temporal; se guarda la página estable del comunicado.
    assert comunicado.url_fuente == "https://enfen.imarpe.gob.pe/download/comunicado-oficial-enfen-n-20-2026/"


def test_si_ninguna_fuente_responde_el_error_lo_explica():
    with pytest.raises(enfen.ErrorEnfen, match="gob.pe · SENAMHI: sin conexión"):
        enfen.obtener_ultimo_comunicado(red_caida()())


# ---------------------------------------------------------------- caché y modos

def test_con_cache_vigente_no_sale_a_la_red(monkeypatch):
    monkeypatch.setenv("ENFEN_MODO", "oficial")
    escribir_cache("20-2026", EstadoAlerta.ALERTA_NINO, date(2026, 11, 13), hace=timedelta(hours=1))
    estado = enfen.estado_actual()  # la fixture falla si hay algún intento de red
    assert (estado.modo, estado.estado, estado.desactualizado) == ("oficial", EstadoAlerta.ALERTA_NINO, False)


def test_sin_red_usa_la_cache_y_la_marca_desactualizada(monkeypatch, cliente):
    monkeypatch.setenv("ENFEN_MODO", "oficial")
    intentos: list[str] = []
    monkeypatch.setattr(enfen, "nuevo_cliente_http", red_caida(intentos))
    escribir_cache("19-2026", EstadoAlerta.ALERTA_NINO, date(2026, 10, 30), hace=timedelta(hours=7),
                   desde=date(2026, 2, 13))

    respuesta = cliente.get("/alertas/enfen")
    assert respuesta.status_code == 200, respuesta.text
    estado = respuesta.json()
    assert (estado["numero"], estado["fecha"], estado["desactualizado"]) == ("19-2026", "2026-10-30", True)
    assert "sin conexión" in estado["error"]
    assert cliente.get("/cliente/el-nino").json() == {"activo": True, "desde": "2026-02-13", "fuente": "enfen"}
    # Tras un fallo no se reintenta en cada solicitud (espera ESPERA_TRAS_FALLO).
    assert len(intentos) == 2
    assert cliente.get("/alertas/enfen").json()["desactualizado"] is True
    assert len(intentos) == 2


def test_sin_red_ni_cache_responde_503_y_no_habilita_el_alivio(monkeypatch, cliente):
    monkeypatch.setenv("ENFEN_MODO", "oficial")
    monkeypatch.setattr(enfen, "nuevo_cliente_http", red_caida())
    assert cliente.get("/alertas/enfen").status_code == 503
    assert cliente.get("/cliente/el-nino").json() == {"activo": False, "desde": None, "fuente": "enfen"}


def test_una_lectura_mas_antigua_no_reemplaza_la_cache(monkeypatch):
    monkeypatch.setenv("ENFEN_MODO", "oficial")
    escribir_cache("20-2026", EstadoAlerta.ALERTA_NINO, date(2026, 11, 13), hace=timedelta(hours=8))
    paginas = paginas_reales(pdf="comunicado-13-2025.pdf")  # una fuente desactualizada devuelve un PDF viejo
    estado, cambio = enfen.revisar(cliente=red_simulada(paginas))
    assert (estado.comunicado.numero, estado.estado, cambio) == ("20-2026", EstadoAlerta.ALERTA_NINO, None)


def test_el_modo_demo_no_se_puede_usar_en_modo_oficial(monkeypatch, cliente):
    monkeypatch.setenv("ENFEN_MODO", "oficial")
    escribir_cache("20-2026", EstadoAlerta.ALERTA_NINO, date(2026, 11, 13), hace=timedelta(hours=1))
    assert cliente.post("/alertas/enfen/demo", json={"estado": "NO_ACTIVO"}).status_code == 409


# ---------------------------------------------------------------- app del cliente

def test_estado_el_nino_conserva_el_formato_de_la_fase_1(cliente):
    assert cliente.get("/cliente/el-nino").json() == {"activo": False, "desde": None, "fuente": "demo"}
    hoy = date.today().isoformat()
    # El interruptor de la app del cliente sigue funcionando y mueve el estado del ENFEN en modo demo.
    assert cliente.post("/cliente/el-nino", json={"activo": True}).json() == {"activo": True, "desde": hoy,
                                                                             "fuente": "demo"}
    assert cliente.get("/alertas/enfen").json()["estado"] == "ALERTA_NINO"
    # Y al revés: lo que fija /alertas/enfen/demo es lo que ve la app del cliente.
    cliente.post("/alertas/enfen/demo", json={"estado": "NO_ACTIVO"})
    assert cliente.get("/cliente/el-nino").json() == {"activo": False, "desde": None, "fuente": "demo"}
    assert cliente.post("/cliente/el-nino", json={"activo": True}).json()["activo"] is True


def test_la_alerta_oficial_habilita_el_alivio_en_la_app_del_cliente(monkeypatch, cliente):
    loan_id = sembrar(cliente)
    monkeypatch.setenv("ENFEN_MODO", "oficial")
    monkeypatch.setattr(enfen, "nuevo_cliente_http", lambda: red_simulada(paginas_reales()))
    # Caché vigente con "No Activo": hasta la revisión, la app del cliente no ofrece el alivio.
    escribir_cache("13-2025", EstadoAlerta.NO_ACTIVO, date(2025, 12, 18), hace=timedelta(hours=1))
    assert cliente.get(f"/cliente/prestamos/{loan_id}").json()["elNino"]["activo"] is False

    revision = cliente.post("/alertas/enfen/revisar").json()
    assert revision["cambio"] is True
    assert (revision["evento"]["anterior"], revision["evento"]["estado"], revision["evento"]["comunicado"]) == (
        "NO_ACTIVO", "ALERTA_NINO", "20-2026")
    assert cliente.get("/cliente/el-nino").json() == {"activo": True, "desde": "2026-11-13", "fuente": "enfen"}
    prestamo = cliente.get(f"/cliente/prestamos/{loan_id}").json()
    assert prestamo["elNino"] == {"activo": True, "alivioDisponible": 3, "puedeAplicar": True}
    assert cliente.post(f"/cliente/prestamos/{loan_id}/alivio-el-nino").status_code == 200


def test_vigilancia_es_un_aviso_preventivo_sin_alivio(cliente):
    loan_id = sembrar(cliente)
    cliente.post("/alertas/enfen/demo", json={"estado": "VIGILANCIA_NINO"})
    estado = cliente.get("/cliente/el-nino").json()
    assert estado["activo"] is False and "preventivo" in estado["aviso"]
    assert cliente.get(f"/cliente/prestamos/{loan_id}").json()["elNino"]["puedeAplicar"] is False
    assert cliente.post(f"/cliente/prestamos/{loan_id}/alivio-el-nino").status_code == 409
    avisos = cliente.get("/alertas/notificaciones", params={"loanId": loan_id}).json()
    assert [a["plantilla"] for a in avisos] == ["vigilancia_el_nino"]


# ---------------------------------------------------------------- alertas y notificaciones

def test_un_cambio_a_alerta_notifica_solo_a_los_prestamos_con_clausula(cliente):
    con_clausula = sembrar(cliente)                  # agricultura: rubro expuesto
    sin_clausula = sembrar(cliente, "aplazamiento")  # bodega
    respuesta = cliente.post("/alertas/enfen/demo", json={"estado": "ALERTA_NINO", "magnitud": "fuerte"}).json()
    assert respuesta["cambio"] is True
    assert respuesta["evento"]["prestamosConClausula"] == 1 and respuesta["evento"]["notificaciones"] == 1

    avisos = cliente.get("/alertas/notificaciones").json()
    assert [(a["destinatario"], a["plantilla"], a["estado"]) for a in avisos] == [
        (con_clausula, "alerta_el_nino", "pendiente")]
    assert "Usar alivio" in avisos[0]["texto"]
    assert cliente.get("/alertas/notificaciones", params={"loanId": sin_clausula}).json() == []
    # Sin cambio de estado no hay avisos nuevos.
    assert cliente.post("/alertas/enfen/demo", json={"estado": "ALERTA_NINO"}).json()["cambio"] is False
    assert len(cliente.get("/alertas/notificaciones").json()) == 1
    eventos = cliente.get("/alertas/eventos").json()
    assert [(e["anterior"], e["estado"], e["origen"]) for e in eventos] == [("NO_ACTIVO", "ALERTA_NINO", "demo")]


def test_el_interruptor_de_la_app_del_cliente_tambien_genera_los_avisos(cliente):
    loan_id = sembrar(cliente)
    cliente.post("/cliente/el-nino", json={"activo": True})
    avisos = cliente.get("/alertas/notificaciones", params={"loanId": loan_id}).json()
    assert [a["plantilla"] for a in avisos] == ["alerta_el_nino"]
    assert cliente.get("/alertas/eventos").json()[0]["origen"] == "app del cliente"


def test_recordatorio_tres_dias_antes_con_monto_y_fecha(cliente):
    loan_id = sembrar(cliente, "aplazamiento")
    proxima = cliente.get(f"/cliente/prestamos/{loan_id}").json()["proximaCuota"]
    vence = alertas._vencimiento(proxima["mes"], date.today())
    generar = "/alertas/notificaciones/generar-recordatorios"

    antes = cliente.post(generar, params={"hoy": (vence - timedelta(days=4)).isoformat()}).json()
    assert antes["generadas"] == []
    justo = cliente.post(generar, params={"hoy": (vence - timedelta(days=3)).isoformat()}).json()["generadas"]
    assert [m["plantilla"] for m in justo] == ["recordatorio_cuota"]
    assert plantillas.soles(proxima["monto"]) in justo[0]["texto"]
    assert f"{vence:%d/%m}" in justo[0]["texto"]
    # No se repite el mismo recordatorio.
    assert cliente.post(generar, params={"hoy": (vence - timedelta(days=2)).isoformat()}).json()["generadas"] == []


def test_aviso_de_temporada_baja_con_mensaje_positivo(cliente):
    loan_id = sembrar(cliente)  # estacional: las cuotas bajan en temporada baja
    cronograma = cliente.get(f"/cliente/prestamos/{loan_id}").json()["cronograma"]
    baja = next(fila for fila in cronograma if fila["temporada"] == "baja")
    for _ in range(baja["numero"] - 1):
        assert cliente.post(f"/cliente/prestamos/{loan_id}/pagar").status_code == 200
    generadas = cliente.post("/alertas/notificaciones/generar-recordatorios").json()["generadas"]
    aviso = next(m for m in generadas if m["plantilla"] == "temporada_baja")
    assert aviso["texto"].startswith("¡Buenas noticias")
    assert plantillas.soles(baja["cuota"]) in aviso["texto"]


def test_aplazamiento_confirmado_avisa_el_nuevo_monto_y_el_costo_adicional(cliente):
    loan_id = sembrar(cliente, "aplazamiento")
    ruta = f"/cliente/prestamos/{loan_id}/aplazamiento"
    previa = cliente.post(f"{ruta}/preview", json={"installment": 2}).json()
    assert cliente.post(ruta, json={"installment": 12}).status_code == 400  # rechazado: sin aviso
    assert cliente.post(ruta, json={"installment": 2, "revision": previa["revision"]}).status_code == 200

    avisos = cliente.get("/alertas/notificaciones", params={"loanId": loan_id}).json()
    assert [a["plantilla"] for a in avisos] == ["aplazamiento_confirmado"]
    texto = avisos[0]["texto"]
    assert "cuota 2" in texto
    assert plantillas.soles(previa["nuevaCuota"]) in texto
    assert plantillas.soles(previa["costoAdicionalTotal"]) in texto


@pytest.mark.parametrize("canal", ["sms", "whatsapp"])
def test_ninguna_plantilla_sms_pasa_de_160_caracteres(canal):
    largo = "Maximiliana Rosalinda de los Ángeles"
    mensajes = [
        plantillas.recordatorio_cuota(largo, 24, 24, 99_999.99, date(2026, 12, 28)),
        plantillas.temporada_baja(largo, "set", 99_999.99),
        plantillas.alerta_el_nino(largo),
        plantillas.vigilancia_el_nino(largo),
        plantillas.aplazamiento_confirmado(largo, 24, 99_999.99, 99_999.99),
    ]
    assert len(mensajes) == len(plantillas.PLANTILLAS)
    for mensaje in mensajes:
        texto = plantillas.para_canal(mensaje, canal)
        if canal == "sms":
            assert plantillas.largo_sms(texto) <= plantillas.LARGO_SMS, texto  # y solo caracteres GSM-7
        else:
            assert texto == mensaje  # WhatsApp conserva las tildes
    assert "declaró" in plantillas.alerta_el_nino("Rosa")
    assert "declaro" in plantillas.para_canal(plantillas.alerta_el_nino("Rosa"), "sms")


def test_el_outbox_simula_el_envio_y_deja_bitacora(cliente):
    sembrar(cliente)
    cliente.post("/alertas/enfen/demo", json={"estado": "ALERTA_NINO"})
    assert cliente.post("/alertas/notificaciones/enviar").json() == {"enviadas": 1}
    aviso = cliente.get("/alertas/notificaciones").json()[0]
    assert aviso["estado"] == "enviado-simulado" and aviso["enviado_en"]
    lineas = [json.loads(linea) for linea in alertas.outbox.archivo.read_text(encoding="utf-8").splitlines()]
    assert [linea["estado"] for linea in lineas] == ["pendiente", "enviado-simulado"]
    assert {"canal", "destinatario", "plantilla", "texto", "fecha", "estado"} <= set(lineas[0])


def test_impacto_por_rubro_y_region(cliente):
    creados = cliente.post("/alertas/demo/cartera", params={"n": 12}).json()["creados"]
    assert len(creados) == 12
    pagado = next(lid for lid in creados if api.DB["loans"][lid]["propuesta"]["clausula_el_nino"])
    assert cliente.post(f"/cliente/prestamos/{pagado}/pagar").status_code == 200

    impacto = cliente.get("/alertas/impacto").json()
    expuestos = [api.DB["loans"][lid] for lid in creados if api.DB["loans"][lid]["propuesta"]["clausula_el_nino"]]
    assert impacto["total"]["prestamos"] == len(expuestos) > 0
    assert impacto["cartera"]["prestamos"] == 12
    assert impacto["total"]["cuotasAlivio"] == 3 * len(expuestos)
    prestamo = api.DB["loans"][pagado]
    saldo_pagado = desglose_cronograma(prestamo["principal"], tea_a_tem(prestamo["tea"]), prestamo["cuotas"])[0]["saldo"]
    saldo_esperado = sum(p["principal"] for p in expuestos) - prestamo["principal"] + saldo_pagado
    assert impacto["total"]["saldo"] == pytest.approx(saldo_esperado, abs=0.05)
    for agrupado in ("grupos", "porRubro", "porRegion"):
        assert sum(g["prestamos"] for g in impacto[agrupado]) == impacto["total"]["prestamos"]
    assert {g["rubro"] for g in impacto["grupos"]} <= set(impacto["rubrosExpuestos"])
    assert alertas.SIN_REGION not in {g["region"] for g in impacto["porRegion"]}
    assert impacto["alivioHabilitado"] is False


def test_la_tarea_programada_esta_apagada_en_las_pruebas_y_se_puede_activar(monkeypatch):
    def hilos_vivos():
        return [h for h in threading.enumerate() if h.name == "revision-enfen" and h.is_alive()]

    with TestClient(api.app):
        assert hilos_vivos() == []

    revisado = threading.Event()
    monkeypatch.setattr(enfen, "revisar", lambda **_: revisado.set() or (enfen.estado_actual(), None))
    monkeypatch.setenv("ENFEN_REVISION_AUTOMATICA", "1")
    with TestClient(api.app):
        assert revisado.wait(5)
        assert len(hilos_vivos()) == 1
    assert hilos_vivos() == []
