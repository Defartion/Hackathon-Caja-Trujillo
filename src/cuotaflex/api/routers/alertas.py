"""Fase 2 · Lote C: disparador ENFEN, impacto en la cartera y notificaciones simuladas.

GET  /alertas/enfen                                 estado oficial (o demo) con fuente, fecha y si está desactualizado
POST /alertas/enfen/revisar                         fuerza una lectura; si el estado cambió genera eventos y avisos
POST /alertas/enfen/demo                            fija el estado en modo demo (ENFEN_MODO=demo)
GET  /alertas/eventos                               cambios de estado detectados
GET  /alertas/impacto                               préstamos con cláusula El Niño por rubro y región
GET  /alertas/notificaciones?loanId=                bandeja de salida (simulada)
POST /alertas/notificaciones/generar-recordatorios  recordatorios de cuota y avisos de temporada baja
POST /alertas/notificaciones/enviar                 simula el envío de los mensajes pendientes
POST /alertas/demo/cartera                          registra créditos sintéticos con región (solo demo)

Con ENFEN_REVISION_AUTOMATICA=1, al iniciar la API un hilo revisa el ENFEN cada 6 h (ENFEN_REVISION_HORAS).
El aviso "Aplazamiento confirmado" se genera al observar POST /cliente/prestamos/{id}/aplazamiento.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...agente import MESES_ES
from ...config import cargar_parametros, desglose_cronograma, tea_a_tem
from ...datos import generar_cartera
from ...integraciones import enfen
from ...notificaciones import outbox, plantillas

log = logging.getLogger(__name__)

DIA_DE_PAGO = 28            # demo: las cuotas vencen el día 28 (el cronograma del core solo guarda el mes)
DIAS_RECORDATORIO = 3
HORAS_ENTRE_REVISIONES = 6
SIN_REGION = "Sin región"
Canal = Literal["sms", "whatsapp"]

_eventos: list[dict] = []
_lock_eventos = threading.Lock()


class _RevisionPeriodica(threading.Thread):
    def __init__(self, intervalo_s: float):
        super().__init__(name="revision-enfen", daemon=True)
        self.intervalo_s = intervalo_s
        self._parar = threading.Event()

    def run(self) -> None:
        while not self._parar.is_set():
            try:
                enfen.revisar(origen="tarea programada")
            except enfen.ErrorEnfen as e:
                log.warning("Revisión programada del ENFEN sin datos: %s", e)
            except Exception:
                log.exception("Falló la revisión programada del ENFEN")
            self._parar.wait(self.intervalo_s)

    def detener(self) -> None:
        self._parar.set()
        self.join(timeout=5)


@asynccontextmanager
async def _ciclo_de_vida(_app):
    hilo = None
    if os.getenv("ENFEN_REVISION_AUTOMATICA", "0") == "1":
        horas = float(os.getenv("ENFEN_REVISION_HORAS", HORAS_ENTRE_REVISIONES))
        hilo = _RevisionPeriodica(horas * 3600)
        hilo.start()
    try:
        yield
    finally:
        if hilo is not None:
            hilo.detener()


router = APIRouter(prefix="/alertas", tags=["alertas"], lifespan=_ciclo_de_vida)


# ---------------------------------------------------------------- préstamos del core

def _canal_por_defecto() -> str:
    return "whatsapp" if os.getenv("NOTIFICACIONES_CANAL", "sms").lower() == "whatsapp" else "sms"


def _saldo(prestamo: dict) -> float:
    pagadas = min(prestamo.get("cuotasPagadas", 0), len(prestamo["cuotas"]))
    if pagadas == 0:
        return round(float(prestamo["principal"]), 2)
    filas = desglose_cronograma(prestamo["principal"], tea_a_tem(prestamo["tea"]), prestamo["cuotas"])
    return filas[pagadas - 1]["saldo"]


def _vista(loan_id: int, prestamo: dict) -> dict:
    cliente = api.DB["clients"].get(prestamo["clientId"], {})
    propuesta = prestamo["propuesta"]
    cuotas = prestamo["cuotas"]
    pagadas = prestamo.get("cuotasPagadas", 0)
    proxima = None
    if pagadas < len(cuotas):
        monto = cuotas[pagadas]
        proxima = {"numero": pagadas + 1, "mes": propuesta["cronograma"][pagadas]["mes"], "monto": monto,
                   "temporada": _temporada(monto, propuesta["cuota_fija_referencia"])}
    return {"loanId": loan_id, "nombre": cliente.get("nombre"), "rubro": cliente.get("rubro"),
            "region": cliente.get("region") or SIN_REGION, "canal": cliente.get("canal") or _canal_por_defecto(),
            "clausula": bool(propuesta.get("clausula_el_nino")), "alivioDisponible": _alivio_disponible(prestamo),
            "saldo": _saldo(prestamo), "totalCuotas": len(cuotas), "proxima": proxima}


def _prestamos_activos() -> list[dict]:
    return [_vista(lid, p) for lid, p in list(api.DB["loans"].items()) if p["status"]["value"] == "Active"]


# ---------------------------------------------------------------- cambios de estado del ENFEN

def _procesar_cambio(cambio: enfen.Cambio) -> None:
    """Registra el evento y avisa a los clientes con cláusula El Niño (solo Alerta o Vigilancia de El Niño)."""
    nuevo = cambio.actual.estado
    expuestos = [p for p in _prestamos_activos() if p["clausula"]]
    avisos = 0
    for p in expuestos:
        if nuevo is enfen.EstadoAlerta.ALERTA_NINO:
            proxima = p["proxima"]
            if p["alivioDisponible"] <= 0 or proxima is None or proxima["numero"] >= p["totalCuotas"]:
                continue  # sin alivio que usar, el mensaje no aplica
            plantilla, texto = "alerta_el_nino", plantillas.alerta_el_nino(p["nombre"])
        elif nuevo is enfen.EstadoAlerta.VIGILANCIA_NINO:
            plantilla, texto = "vigilancia_el_nino", plantillas.vigilancia_el_nino(p["nombre"])
        else:
            break
        if outbox.agregar(canal=p["canal"], destinatario=p["loanId"], plantilla=plantilla, texto=texto,
                          clave=f"{plantilla}:{p['loanId']}:{cambio.id}", evento=cambio.id):
            avisos += 1
    comunicado = cambio.actual.comunicado
    evento = {"id": cambio.id, "fecha": cambio.fecha.isoformat(timespec="seconds"), "origen": cambio.origen,
              "modo": cambio.actual.modo, "anterior": cambio.anterior.value, "estado": nuevo.value,
              "etiqueta": nuevo.etiqueta, "comunicado": comunicado.numero if comunicado else None,
              "prestamosConClausula": len(expuestos), "notificaciones": avisos}
    with _lock_eventos:
        _eventos.append(evento)
    log.info("ENFEN: %s → %s (%s), %d avisos", cambio.anterior.value, nuevo.value, cambio.origen, avisos)


def _evento(id_cambio: int) -> dict | None:
    with _lock_eventos:
        return next((e for e in _eventos if e["id"] == id_cambio), None)


def _respuesta(estado: enfen.EstadoEnfen, cambio: enfen.Cambio | None) -> dict:
    return {"cambio": cambio is not None, "estado": estado.a_dict(),
            "evento": _evento(cambio.id) if cambio else None}


class EstadoDemo(BaseModel):
    estado: enfen.EstadoAlerta
    magnitud: Literal["débil", "moderada", "fuerte", "extraordinaria"] | None = None


@router.get("/enfen")
def ver_enfen():
    try:
        return enfen.estado_actual().a_dict()
    except enfen.EnfenNoDisponible as e:
        raise HTTPException(503, str(e)) from e


@router.post("/enfen/revisar")
def revisar_enfen():
    try:
        return _respuesta(*enfen.revisar(origen="revisión manual"))
    except enfen.EnfenNoDisponible as e:
        raise HTTPException(503, str(e)) from e


@router.post("/enfen/demo")
def fijar_enfen_demo(datos: EstadoDemo):
    if enfen.modo() != "demo":
        raise HTTPException(409, "El modo demo está apagado: inicia la API con ENFEN_MODO=demo.")
    return _respuesta(*enfen.fijar_demo(datos.estado, datos.magnitud, origen="demo"))


@router.get("/eventos")
def ver_eventos():
    with _lock_eventos:
        return _eventos[::-1]


# ---------------------------------------------------------------- impacto en la cartera

def _resumen(prestamos: list[dict]) -> dict:
    return {"prestamos": len(prestamos), "saldo": round(sum(p["saldo"] for p in prestamos), 2),
            "cuotasAlivio": sum(p["alivioDisponible"] for p in prestamos)}


def _agrupar(prestamos: list[dict], *claves: str) -> list[dict]:
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for p in prestamos:
        grupos[tuple(p[k] for k in claves)].append(p)
    filas = [{**dict(zip(claves, valores)), **_resumen(grupo)} for valores, grupo in grupos.items()]
    return sorted(filas, key=lambda f: (-f["saldo"], *(f[k] for k in claves)))


@router.get("/impacto")
def impacto():
    """Préstamos activos con cláusula El Niño (rubros expuestos): número, saldo y cuotas de alivio."""
    par = cargar_parametros()["el_nino"]
    try:
        estado = enfen.estado_actual()
        cabecera = {"estado": estado.estado.value, "etiqueta": estado.estado.etiqueta,
                    "alivioHabilitado": estado.activo, "desactualizado": estado.desactualizado}
    except enfen.EnfenNoDisponible:
        cabecera = {"estado": None, "etiqueta": "Sin datos del ENFEN", "alivioHabilitado": False,
                    "desactualizado": True}
    activos = _prestamos_activos()
    expuestos = [p for p in activos if p["clausula"]]
    return {**cabecera, "rubrosExpuestos": par["rubros_expuestos"], "mesesAlivio": par["meses_alivio"],
            "cartera": _resumen(activos), "total": _resumen(expuestos),
            "porRubro": _agrupar(expuestos, "rubro"), "porRegion": _agrupar(expuestos, "region"),
            "grupos": _agrupar(expuestos, "rubro", "region")}


# ---------------------------------------------------------------- notificaciones

def _vencimiento(mes: str, hoy: date) -> date:
    """Fecha de pago más cercana a hoy para la cuota del mes indicado."""
    numero_mes = MESES_ES.index(mes) + 1
    return min((date(hoy.year + d, numero_mes, DIA_DE_PAGO) for d in (-1, 0, 1)),
               key=lambda fecha: abs((fecha - hoy).days))


@router.get("/notificaciones")
def ver_notificaciones(loanId: int | None = None):  # noqa: N803 (mismo nombre que usa el core)
    return [m.a_dict() for m in outbox.listar(loanId)]


@router.post("/notificaciones/generar-recordatorios")
def generar_recordatorios(hoy: date | None = None, canal: Canal | None = None):
    """Recordatorio 3 días antes del vencimiento y aviso cuando la próxima cuota es de temporada baja.

    `hoy` permite simular otra fecha en la demo. No repite un aviso ya generado para la misma cuota.
    """
    hoy = hoy or date.today()
    generadas = []
    for p in _prestamos_activos():
        proxima = p["proxima"]
        if proxima is None:
            continue
        destino = canal or p["canal"]
        vence = _vencimiento(proxima["mes"], hoy)
        if 0 <= (vence - hoy).days <= DIAS_RECORDATORIO:
            texto = plantillas.recordatorio_cuota(p["nombre"], proxima["numero"], p["totalCuotas"], proxima["monto"], vence)
            generadas.append(outbox.agregar(canal=destino, destinatario=p["loanId"], plantilla="recordatorio_cuota",
                                            texto=texto, clave=f"recordatorio_cuota:{p['loanId']}:{proxima['numero']}"))
        if proxima["temporada"] == "baja":
            texto = plantillas.temporada_baja(p["nombre"], proxima["mes"], proxima["monto"])
            generadas.append(outbox.agregar(canal=destino, destinatario=p["loanId"], plantilla="temporada_baja",
                                            texto=texto, clave=f"temporada_baja:{p['loanId']}:{proxima['numero']}"))
    return {"hoy": hoy.isoformat(), "generadas": [m.a_dict() for m in generadas if m]}


@router.post("/notificaciones/enviar")
def enviar_notificaciones():
    """Simula el envío: no sale ningún SMS ni WhatsApp real."""
    return {"enviadas": len(outbox.enviar_pendientes())}


_RUTA_APLAZAMIENTO = re.compile(r"^/cliente/prestamos/(\d+)/aplazamiento/?$")


def _avisar_aplazamiento(loan_id: int, cuotas_antes: list[float], restantes_antes: int) -> None:
    prestamo = api.DB["loans"].get(loan_id)
    if prestamo is None or prestamo["aplazamientosRestantes"] >= restantes_antes:
        return
    cuotas = prestamo["cuotas"]
    indice = next((i for i, (antes, ahora) in enumerate(zip(cuotas_antes, cuotas)) if ahora < antes - 0.005), None)
    if indice is None:
        return
    cliente = api.DB["clients"].get(prestamo["clientId"], {})
    costo = round(sum(cuotas) - sum(cuotas_antes), 2)
    outbox.agregar(canal=cliente.get("canal") or _canal_por_defecto(), destinatario=loan_id,
                   plantilla="aplazamiento_confirmado",
                   texto=plantillas.aplazamiento_confirmado(cliente.get("nombre"), indice + 1, cuotas[indice], costo),
                   clave=f"aplazamiento_confirmado:{loan_id}:{restantes_antes}")


class _AvisoDeAplazamiento:
    """Middleware ASGI: al confirmarse un aplazamiento en la app del cliente deja el aviso en la bandeja.

    Así el lote C no modifica el router del cliente (lote B de la fase 1).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        coincide = (scope["type"] == "http" and scope["method"] == "POST"
                    and _RUTA_APLAZAMIENTO.match(scope["path"]))
        if not coincide:
            await self.app(scope, receive, send)
            return
        loan_id = int(coincide.group(1))
        prestamo = api.DB["loans"].get(loan_id)
        antes = (list(prestamo["cuotas"]), prestamo["aplazamientosRestantes"]) if prestamo else None
        estado_http = {}

        async def enviar(mensaje):
            if mensaje["type"] == "http.response.start":
                estado_http["codigo"] = mensaje["status"]
            await send(mensaje)

        await self.app(scope, receive, enviar)
        if antes is not None and estado_http.get("codigo") == 200:
            try:
                _avisar_aplazamiento(loan_id, *antes)
            except Exception:
                log.exception("No se pudo generar el aviso de aplazamiento del préstamo %s", loan_id)


# ---------------------------------------------------------------- cartera de demo

_NOMBRES = ["Rosa", "Luis", "Carmen", "Jorge", "María", "José", "Ana", "Pedro", "Julia", "Miguel", "Elena", "César"]
_APELLIDOS = ["Salazar", "Ramos", "Quispe", "Vásquez", "Rojas", "Mendoza", "Castillo", "Flores", "Gutiérrez", "Reyes"]


@router.post("/demo/cartera")
def sembrar_cartera_demo(n: Annotated[int, Query(ge=1, le=60)] = 20, semilla: int = 11):
    """Registra en el core n créditos sintéticos activos, con región y canal, para mostrar el impacto."""
    clientes, historial = generar_cartera(n, semilla)
    ventas = {k: g.sort_values("t")["ventas"].tolist() for k, g in historial.groupby("cliente_id")}
    mes = date.today().month - 1
    creados = []
    for i, c in enumerate(clientes.to_dict("records")):
        nombre = f"{_NOMBRES[i % len(_NOMBRES)]} {_APELLIDOS[(i * 7 + semilla) % len(_APELLIDOS)]}"
        client_id = api.crear_cliente(api.ClienteIn(
            nombre=nombre, rubro=c["rubro"], ventas_medias=c["ventas_medias"], margen=c["margen"],
            gasto_familiar=c["gasto_familiar"], otras_cuotas=c["otras_cuotas"],
            dias_atraso_max=c["dias_atraso_max"], ajuste_asesor=c["ajuste_asesor"],
            historial_ventas=ventas[c["cliente_id"]]))["clientId"]
        # Datos sintéticos: la región viene de la cartera de La Libertad y quien cobra con Yape usa WhatsApp.
        api.DB["clients"][client_id].update(region=c["region"],
                                            canal="whatsapp" if c["pct_cobros_yape"] >= 0.35 else "sms")
        loan_id = api.crear_prestamo(api.PrestamoIn(clientId=client_id, principal=c["principal"],
                                                    numberOfRepayments=c["plazo"], tea=c["tea"],
                                                    mesPrimeraCuota=mes))["loanId"]
        for comando in ("approve", "disburse"):
            api.comando_prestamo(loan_id, comando)
        creados.append(loan_id)
    return {"creados": creados}


# El core descubre los routers al importarse: se carga después de declarar las rutas (igual que cliente.py).
from .. import main as api  # noqa: E402
from .cliente import _alivio_disponible, _temporada  # noqa: E402  (mismas reglas que ve el cliente)

enfen.suscribir(_procesar_cambio)
api.app.add_middleware(_AvisoDeAplazamiento)
