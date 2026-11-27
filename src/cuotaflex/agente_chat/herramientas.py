"""Herramientas de consulta y simulación sobre una propuesta de CuotaFlex."""
from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from ..api.routers import asesor
from ..config import cargar_parametros, tea_a_tem
from ..pronostico import pronosticar

Tema = Literal["credito", "flexibilidad", "capacidad_pago", "el_nino", "aplazamiento"]
PRODUCTOS = {"fija": "cuota fija", "estacional": "cuota estacional", "aplazamiento": "cuota con aplazamiento"}


class Argumentos(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Recalcular(Argumentos):
    monto: float | None = Field(None, gt=0)
    plazo: int | None = Field(None, gt=0, le=36)
    ajuste_asesor: float | None = Field(None, ge=0.5, le=1.5)


class Politica(Argumentos):
    tema: Tema


class Bitacora(Argumentos):
    indice: int = Field(gt=0, description="Paso de la bitácora, contado desde uno")


ESQUEMAS = {
    "recalcular_propuesta": (Recalcular, "Simula cambios de monto, plazo o ajuste. Usa únicamente cambios pedidos."),
    "simular_cliente": (Argumentos, "Compara el riesgo de la cuota fija y Thinku para la propuesta actual."),
    "consultar_politica": (Politica, "Consulta la política vigente. Usa aplazamiento para estimar su costo."),
    "explicar_paso_bitacora": (Bitacora, "Explica el paso indicado por su índice en la bitácora de esta propuesta."),
}

HERRAMIENTAS = [
    {"name": nombre, "description": descripcion, "input_schema": modelo.model_json_schema()}
    for nombre, (modelo, descripcion) in ESQUEMAS.items()
]


def limpiar_no_finitos(dato):
    if isinstance(dato, dict):
        return {k: limpiar_no_finitos(v) for k, v in dato.items()}
    if isinstance(dato, list):
        return [limpiar_no_finitos(v) for v in dato]
    if isinstance(dato, float) and not math.isfinite(dato):
        return None
    return dato


def calcular(solicitud: asesor.ClienteSolicitud) -> dict:
    cli = solicitud.model_dump(exclude={"historial_ventas"})
    hist = solicitud.historial_ventas
    if not hist or len(hist) < 12:
        rng = np.random.default_rng(asesor._semilla(cli))
        hist = asesor.simular_ventas(
            cli["rubro"], cli["ventas_medias"], asesor.MESES_HIST, rng,
            (cli["mes_desembolso"] - asesor.MESES_HIST) % 12,
        ).round(2).tolist()
    historial = pd.DataFrame({"cliente_id": cli["cliente_id"], "t": range(-len(hist), 0), "ventas": hist})
    motor = asesor._agente
    horizonte = max(motor.par["credito"]["plazos_meses"])
    cuantiles = None
    if cli["plazo"] > horizonte:
        cuantiles = pronosticar(pd.DataFrame([cli]), historial, metodo=motor.metodo)[cli["cliente_id"]]
    return limpiar_no_finitos(asesor._nativo(motor.proponer(cli, historial, pronostico_24m=cuantiles)))


class Herramientas:
    def __init__(self, solicitud: asesor.ClienteSolicitud, propuesta: dict):
        self.solicitud = solicitud
        self.propuesta = propuesta

    def ejecutar(self, nombre: str, argumentos: dict) -> dict:
        if nombre not in ESQUEMAS:
            raise ValueError("Herramienta desconocida")
        modelo, _ = ESQUEMAS[nombre]
        entrada = modelo.model_validate(argumentos).model_dump(exclude_none=True)
        return getattr(self, nombre)(**entrada)

    def recalcular_propuesta(self, monto=None, plazo=None, ajuste_asesor=None) -> dict:
        cambios = {"principal": monto, "plazo": plazo, "ajuste_asesor": ajuste_asesor}
        solicitud = self.solicitud.model_copy(update={k: v for k, v in cambios.items() if v is not None})
        p = calcular(solicitud)
        self.solicitud, self.propuesta = solicitud, p
        datos = {k: p[k] for k in ("principal_solicitado", "principal_aprobado", "plazo",
                                    "tea", "producto", "cuota_fija_referencia", "valido")}
        texto = (f"El motor propone S/ {p['principal_aprobado']:,.2f} "
                 f"a {p['plazo']} meses con TEA de {p['tea']:.2%}.")
        if not p["valido"]:
            texto += " El cronograma requiere revisión antes de continuar."
        return {**datos, "motivo": texto}

    def simular_cliente(self) -> dict:
        cli = self.solicitud.model_dump(exclude={"historial_ventas"})
        resultados = asesor._comparar(cli, self.propuesta, asesor._agente.par)
        fija, flex = resultados["fija"], resultados["cuotaflex"]
        for producto in (fija, flex):
            producto.pop("cuotas")
        texto = (f"En {resultados['n_escenarios']} escenarios, la mora simulada fue "
                 f"{fija['mora30']:.2%} con cuota fija y {flex['mora30']:.2%} con Thinku. "
                 f"El incumplimiento simulado fue {fija['default']:.2%} y {flex['default']:.2%}, respectivamente.")
        return {**resultados, "motivo": texto}

    def consultar_politica(self, tema: Tema) -> dict:
        par, p = cargar_parametros(), self.propuesta
        fx = par["flexibilidad"]
        if tema == "aplazamiento":
            from ..api.routers import cliente

            disponibles = p["aplazamientos_disponibles"]
            datos = {"aplazamientos_disponibles": disponibles}
            if not disponibles or len(p["cronograma"]) < 2:
                return {**datos, "motivo": "La propuesta no tiene cuotas disponibles para aplazar."}
            cuotas = [fila["cuota"] for fila in p["cronograma"]]
            prestamo = {"principal": p["principal_aprobado"], "tea": p["tea"], "cuotas": cuotas}
            tem = tea_a_tem(p["tea"])
            minimo = round(cliente._piso(prestamo, tem), 2)
            indice = next((i for i, cuota in enumerate(cuotas[:-1]) if cuota > minimo), None)
            if indice is None:
                return {**datos, "motivo": "Las cuotas elegibles del cronograma ya están en el mínimo."}
            nuevas, aumento = cliente._redistribuir_cuota(prestamo, indice)
            costo = round(sum(nuevas) - sum(cuotas), 2)
            return {**datos, "cuota_afectada": indice + 1, "costo_adicional": costo,
                    "cuota_minima": nuevas[indice], "incremento_cuotas_siguientes": aumento,
                    "motivo": f"La propuesta permite hasta {disponibles} aplazamientos. "
                              f"Si se aplaza la cuota {indice + 1}, el costo adicional estimado es "
                              f"S/ {costo:,.2f} porque el saldo diferido genera intereses."}
        if tema == "el_nino":
            datos = {"aplica": p["clausula_el_nino"], "meses_alivio": par[tema]["meses_alivio"],
                     "cuota_minima_pct": fx["cuota_minima_pct"]}
            texto = "La propuesta no incluye alivio por El Niño."
            if datos["aplica"]:
                texto = (f"Si hay una alerta del ENFEN, la cláusula permite hasta {datos['meses_alivio']} meses "
                         f"de alivio, con una cuota mínima de {datos['cuota_minima_pct']:.0%} de la cuota fija de referencia.")
            return {**datos, "motivo": texto}

        datos = par[tema]
        textos = {
            "credito": f"La TEA base referencial es {par['credito']['tea_base']:.0%}. "
                       "Los plazos de política son " + ", ".join(f"{n} meses" for n in par["credito"]["plazos_meses"]) + ".",
            "flexibilidad": f"La política establece hasta {fx['max_aplazamientos']} aplazamientos condicionados al buen pago "
                            f"y una cuota mínima de {fx['cuota_minima_pct']:.0%} de la cuota fija de referencia.",
            "capacidad_pago": f"La cuota se diseña hasta un {par['capacidad_pago']['ratio_cuota_excedente_max']:.0%} "
                              "del excedente mensual estimado en el escenario conservador.",
        }
        return {**datos, "motivo": textos[tema]}

    def explicar_paso_bitacora(self, indice: int) -> dict:
        p = self.propuesta
        if not 1 <= indice <= len(p["bitacora"]):
            raise ValueError("Ese paso no existe en la bitácora")
        paso = p["bitacora"][indice - 1]
        respuesta = {**paso, "indice": indice}
        if paso["paso"] == "replanificar":
            solicitado, monto = p["principal_solicitado"], paso["nuevo_principal"]
            respuesta["principal_solicitado"] = solicitado
            texto = (f"El motor redujo el monto solicitado de S/ {solicitado:,.2f} a S/ {monto:,.2f} "
                     "porque las cuotas superaban la capacidad estimada en el escenario conservador.")
        elif paso["paso"] == "cronograma":
            texto = (f"El motor evaluó un cronograma de {paso['plazo']} meses por S/ {paso['principal']:,.2f}.")
            if paso["principal"] == p["principal_solicitado"] == p["principal_aprobado"]:
                texto += " El monto solicitado se mantuvo."
        elif paso["paso"] == "producto":
            producto = paso["producto"]
            razones = {"fija": "la solicitud no cumple las condiciones de flexibilidad",
                       "estacional": "la actividad registra variaciones de ventas según la temporada",
                       "aplazamiento": "el perfil elegible permite incluir aplazamientos con cuotas regulares"}
            texto = f"El motor eligió {PRODUCTOS[producto]} porque {razones[producto]}."
        elif paso["paso"] == "elegibilidad":
            motivos = []
            if paso.get("sobreendeudado"):
                motivos.append("la carga de deuda supera el límite de capacidad")
            if any("atraso" in m for m in paso.get("motivos", [])):
                motivos.append("el historial de atrasos supera el límite para flexibilidad")
            if paso["elegible_flex"]:
                texto = "La solicitud cumple los criterios iniciales para una modalidad flexible."
            else:
                razon = " y ".join(motivos) or "el perfil de riesgo queda fuera de la política"
                texto = f"La solicitud queda fuera de flexibilidad porque {razon}."
        elif paso["paso"] == "validacion":
            texto = ("El cronograma cumple las comprobaciones de riesgo del motor."
                     if paso["valido"] else "El cronograma requiere revisión según las comprobaciones de riesgo.")
        else:
            texto = "El motor registró este paso en la evaluación de modalidades de la propuesta."
        return {**respuesta, "motivo": texto}
