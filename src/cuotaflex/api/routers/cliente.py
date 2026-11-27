"""Operaciones de la app del cliente sobre los préstamos del core de demo."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from json import dumps
from threading import Lock
from typing import Annotated, Literal

from fastapi import APIRouter, Body, HTTPException

from ... import cronograma as crono
from ...config import cargar_parametros, cuota_francesa, tea_a_tem
from ...datos import PERFILES
from ...politica import PRODUCTOS

router = APIRouter(prefix="/cliente", tags=["cliente"])
_bloqueo = Lock()
_alerta_el_nino = {"activo": False, "desde": None, "fuente": "demo"}


def _prestamo(loan_id: int) -> dict:
    prestamo = api.DB["loans"].get(loan_id)
    if prestamo is None:
        raise HTTPException(404, "No encontramos este préstamo.")
    return prestamo


def _validar_activo(prestamo: dict) -> None:
    if prestamo["status"]["value"] != "Active":
        raise HTTPException(409, "Tu préstamo debe estar activo para hacer este cambio.")


def _temporada(cuota: float, referencia: float) -> str:
    if cuota > referencia * 1.05:
        return "alta"
    if cuota < referencia * 0.95:
        return "baja"
    return "normal"


def _cronograma(prestamo: dict, cuotas: list[float]) -> list[dict]:
    """Además de número, mes, monto, estado y temporada: vencimiento, capital, interés, saldo y fecha de pago."""
    referencia = prestamo["propuesta"]["cuota_fija_referencia"]
    return [{"numero": fila["numero"], "mes": fila["mes"], "cuota": cuota, "estado": fila["estado"],
             "temporada": _temporada(cuota, referencia), "fecha": fila["fecha"], "capital": fila["capital"],
             "interes": fila["interes"], "saldo": fila["saldo"], "fechaPago": fila["fechaPago"]}
            for fila, cuota in zip(crono.detalle(prestamo, cuotas), cuotas)]


def _validar_aplazamiento(prestamo: dict, installment: int) -> None:
    if prestamo["aplazamientosRestantes"] <= 0:
        raise HTTPException(409, "Ya no tienes aplazamientos disponibles.")
    _validar_activo(prestamo)
    if not 1 <= installment < len(prestamo["cuotas"]):
        raise HTTPException(400, "Elige una cuota del cronograma que no sea la última.")
    if installment in crono.pagadas(prestamo):
        raise HTTPException(400, "Esa cuota ya está pagada.")
    tem = tea_a_tem(prestamo["tea"])
    if prestamo["cuotas"][installment - 1] <= round(_piso(prestamo, tem), 2):
        raise HTTPException(409, "Esa cuota ya está en el mínimo o por debajo.")


def _piso(prestamo: dict, tem: float) -> float:
    proporcion_minima = cargar_parametros()["flexibilidad"]["cuota_minima_pct"]
    return proporcion_minima * cuota_francesa(prestamo["principal"], tem, len(prestamo["cuotas"]))


def _redistribuir_cuota(prestamo: dict, indice: int) -> tuple[list[float], float]:
    """Aplica la fórmula y el redondeo del core a una copia del cronograma."""
    cuotas = prestamo["cuotas"].copy()
    n = len(cuotas)
    tem = tea_a_tem(prestamo["tea"])
    piso = _piso(prestamo, tem)
    diferido = max(cuotas[indice] - piso, 0)
    extra = cuota_francesa(diferido, tem, n - indice - 1)
    cuotas[indice] = round(piso, 2)
    for siguiente in range(indice + 1, n):
        cuotas[siguiente] = round(cuotas[siguiente] + extra, 2)
    return cuotas, round(extra, 2)


def _revision_aplazamiento(prestamo: dict, installment: int) -> str:
    condiciones = (installment, prestamo["cuotas"], prestamo.get("cuotasPagadas", 0),
                   prestamo["aplazamientosRestantes"], prestamo["principal"], prestamo["tea"],
                   sorted(prestamo.get("cuotasAdelantadas", [])))
    return sha256(dumps(condiciones).encode("utf-8")).hexdigest()


def _alivio_disponible(prestamo: dict) -> int:
    if not prestamo["propuesta"]["clausula_el_nino"]:
        return 0
    return prestamo.get("alivioRestante", cargar_parametros()["el_nino"]["meses_alivio"])


def _puede_aplicar_alivio(prestamo: dict, alerta_activa: bool) -> bool:
    proxima = prestamo.get("cuotasPagadas", 0) + 1
    return (alerta_activa and _alivio_disponible(prestamo) > 0
            and prestamo["status"]["value"] == "Active" and proxima < len(prestamo["cuotas"])
            and proxima != prestamo.get("ultimaCuotaConAlivio"))


@router.post("/demo-seed")
def demo_seed(producto: Literal["estacional", "aplazamiento"] = "estacional"):
    rubro = "bodega" if producto == "aplazamiento" else "agricultura"
    nombre = "Luis Ramos" if producto == "aplazamiento" else "Rosa Salazar"
    mes = date.today().month - 1
    ventas_medias = 7000
    # El mismo perfil sintético permite repetir la demo sin depender del ID del cliente.
    historial = [float(ventas_medias * PERFILES[rubro][(mes + i) % 12]) for i in range(-24, 0)]
    cliente = api.crear_cliente(api.ClienteIn(
        nombre=nombre, rubro=rubro, ventas_medias=ventas_medias, margen=0.35,
        gasto_familiar=1000, dias_atraso_max=0, historial_ventas=historial,
    ))
    client_id = cliente["clientId"]
    prestamo = api.crear_prestamo(api.PrestamoIn(
        clientId=client_id, principal=6000, numberOfRepayments=12, mesPrimeraCuota=mes,
        productoPreferido=producto,
    ))
    loan_id = prestamo["loanId"]
    # Fase 4: llave fija por número para los préstamos de demo, así su código sobrevive a un reinicio
    # (al volver a sembrar se recrean con el mismo número) y el jurado no lo ve cambiar.
    from ... import llaves

    llaves.preparar_prestamo(api.DB["loans"][loan_id], uid=f"demo-{loan_id}")
    with _bloqueo:
        api.comando_prestamo(loan_id, "approve")
        api.comando_prestamo(loan_id, "disburse")
    return {"loanId": loan_id, "clientId": client_id}


@router.get("/prestamos/{loan_id}")
def ver_prestamo(loan_id: int):
    with _bloqueo:
        prestamo = _prestamo(loan_id)
        propuesta = prestamo["propuesta"]
        cronograma = _cronograma(prestamo, prestamo["cuotas"])
        siguiente = crono.proxima(prestamo)
        proxima = None
        if siguiente is not None:
            fila = cronograma[siguiente - 1]
            proxima = {"numero": fila["numero"], "mes": fila["mes"], "monto": fila["cuota"],
                       "temporada": fila["temporada"], "fecha": fila["fecha"]}
        activo = estado_el_nino()["activo"]
        cliente = api.DB["clients"].get(prestamo["clientId"], {})
        return {
            "loanId": loan_id,
            "nombre": cliente.get("nombre"),
            "producto": prestamo["producto"],
            "descripcion": PRODUCTOS[prestamo["producto"]],
            "estado": prestamo["status"]["value"],
            "tea": prestamo["tea"],
            "principal": prestamo["principal"],
            "fechaDesembolso": prestamo.get("fechaDesembolso"),
            "proximaCuota": proxima,
            "cuotasPagadas": len(crono.pagadas(prestamo)),
            "totalCuotas": len(cronograma),
            "aplazamientosRestantes": prestamo["aplazamientosRestantes"],
            "clausulaElNino": propuesta["clausula_el_nino"],
            "elNino": {"activo": activo, "alivioDisponible": _alivio_disponible(prestamo),
                       "puedeAplicar": _puede_aplicar_alivio(prestamo, activo)},
            "cronograma": cronograma,
            "cuotaFijaReferencia": propuesta["cuota_fija_referencia"],
            "resumen": crono.resumen(prestamo),
            "explicacion": propuesta["explicacion"],
        }


@router.post("/prestamos/{loan_id}/pagar")
def pagar_cuota(loan_id: int, cuota: Annotated[int | None, Body(embed=True)] = None):
    """Paga la cuota que elige el cliente; sin `cuota`, la próxima (como antes). Adelantar una cuota no cambia
    el plan: solo la marca como pagada y la próxima sigue siendo la primera sin pagar."""
    with _bloqueo:
        prestamo = _prestamo(loan_id)
        _validar_activo(prestamo)
        siguiente = crono.proxima(prestamo)
        if siguiente is None:
            raise HTTPException(409, "Ya pagaste todas tus cuotas.")
        numero = siguiente if cuota is None else cuota
        if not 1 <= numero <= len(prestamo["cuotas"]):
            raise HTTPException(400, "Esa cuota no está en tu cronograma.")
        if numero in crono.pagadas(prestamo):
            raise HTTPException(409, "Esa cuota ya está pagada.")
        respuesta = api.pagar(loan_id, "repayment", {"transactionAmount": prestamo["cuotas"][numero - 1]})
        prestamo["pagos"][-1]["cuota"] = numero
        crono.registrar_pago(prestamo, numero)
        return {**respuesta, "cuota": numero}


@router.post("/prestamos/{loan_id}/aplazamiento/preview")
def previsualizar_aplazamiento(loan_id: int, installment: Annotated[int, Body(embed=True)]):
    with _bloqueo:
        prestamo = _prestamo(loan_id)
        _validar_aplazamiento(prestamo, installment)
        indice = installment - 1
        cuotas = prestamo["cuotas"]
        nuevas, extra = _redistribuir_cuota(prestamo, indice)
        return {
            "cuotaActual": cuotas[indice],
            "nuevaCuota": nuevas[indice],
            "incrementoCuotasSiguientes": extra,
            "costoAdicionalTotal": round(sum(nuevas) - sum(cuotas), 2),
            "cronogramaNuevo": _cronograma(prestamo, nuevas),
            "revision": _revision_aplazamiento(prestamo, installment),
        }


@router.post("/prestamos/{loan_id}/aplazamiento")
def confirmar_aplazamiento(
    loan_id: int, installment: Annotated[int, Body(embed=True)], revision: Annotated[str | None, Body()] = None,
):
    with _bloqueo:
        prestamo = _prestamo(loan_id)
        if revision is not None and revision != _revision_aplazamiento(prestamo, installment):
            raise HTTPException(409, "Tu cronograma cambió. Vuelve a calcular el costo antes de confirmar.")
        _validar_aplazamiento(prestamo, installment)
        return api.aplazar(loan_id, "deferInstallment", api.AplazamientoIn(installment=installment))


@router.get("/el-nino")
def estado_el_nino() -> dict:
    """Alerta de El Niño para la app del cliente, según el ENFEN (fase 2 · lote C: integraciones/enfen.py).

    Mismo formato de la fase 1: {"activo", "desde", "fuente"}. `activo` solo es verdadero con "Alerta de
    El Niño Costero". Con "Vigilancia de El Niño Costero" se agrega `aviso` (preventivo, sin alivio).
    En modo demo (ENFEN_MODO=demo), el interruptor de esta app (POST /cliente/el-nino) sigue fijando la alerta.
    """
    from ...integraciones import enfen  # import local: el lote C solo modifica esta función

    if enfen.modo() == "demo":
        enfen.sincronizar_interruptor(_alerta_el_nino)
    try:
        estado = enfen.estado_actual()
    except enfen.EnfenNoDisponible:  # sin internet ni caché: no se habilita el alivio
        return {"activo": False, "desde": None, "fuente": "enfen"}
    salida = {"activo": estado.activo,
              "desde": estado.desde.isoformat() if estado.activo and estado.desde else None,
              "fuente": "demo" if estado.modo == "demo" else "enfen"}
    if estado.vigilancia:
        salida["aviso"] = "Vigilancia de El Niño Costero: aviso preventivo, todavía sin alivio."
    return salida


@router.post("/el-nino")
def cambiar_alerta_el_nino(activo: Annotated[bool, Body(embed=True)]):
    global _alerta_el_nino
    with _bloqueo:
        estado = estado_el_nino()
        if activo != estado["activo"]:
            _alerta_el_nino = {"activo": activo, "desde": date.today().isoformat() if activo else None,
                              "fuente": "demo"}
        return estado_el_nino()


@router.post("/prestamos/{loan_id}/alivio-el-nino")
def aplicar_alivio(loan_id: int):
    with _bloqueo:
        prestamo = _prestamo(loan_id)
        _validar_activo(prestamo)
        if not estado_el_nino()["activo"]:
            raise HTTPException(409, "La alerta de El Niño está apagada.")
        restantes = _alivio_disponible(prestamo)
        if restantes <= 0:
            raise HTTPException(409, "No tienes alivios por El Niño disponibles.")
        indice = prestamo.get("cuotasPagadas", 0)
        if indice >= len(prestamo["cuotas"]) - 1:
            raise HTTPException(409, "Necesitas cuotas posteriores para usar el alivio.")
        if prestamo.get("ultimaCuotaConAlivio") == indice + 1:
            raise HTTPException(409, "Ya usaste el alivio para esta cuota.")
        nuevas, _ = _redistribuir_cuota(prestamo, indice)
        if nuevas[indice] < prestamo["cuotas"][indice]:
            prestamo["cuotas"] = nuevas
        prestamo["alivioRestante"] = restantes - 1
        prestamo["ultimaCuotaConAlivio"] = indice + 1
        return {"loanId": loan_id, "nuevaCuota": prestamo["cuotas"][indice], "alivioDisponible": restantes - 1}


# El core descubre los routers al importarse. Carga el core después de declarar las rutas
# para que el registro también funcione si otro módulo importa primero este router.
from .. import main as api  # noqa: E402
