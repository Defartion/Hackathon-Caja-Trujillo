"""Lote A · Endpoints para la app del asesor.

GET  /motor/cartera-demo  -> solicitudes sintéticas con historial de ventas
POST /motor/propuesta     -> propuesta del agente + pronóstico + capacidad + comparativa de riesgo
"""
from __future__ import annotations

import copy
import hashlib

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...agente import AgenteAsesor
from ...config import cargar_parametros, cuota_francesa, tea_a_tem
from ...datos import RUBROS, generar_cartera, indice_estacionalidad, simular_ventas
from ...pronostico import pronosticar
from ...simulacion import _trayectorias_el_nino, simular_credito

router = APIRouter(prefix="/motor", tags=["asesor"])

N_ESCENARIOS = 300
MESES_HIST = 24
_CACHE_CARTERA: dict[tuple[int, int], list[dict]] = {}
_agente = AgenteAsesor(metodo_pronostico="mixto")


def _nativo(x):
    """Convierte tipos de NumPy/pandas a tipos nativos de Python (recursivo)."""
    if isinstance(x, dict):
        return {k: _nativo(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_nativo(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_nativo(v) for v in x.tolist()]
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    return x


class ClienteSolicitud(BaseModel):
    cliente_id: str = "DEMO"
    rubro: str
    region: str | None = None
    ventas_medias: float = Field(gt=0)
    margen: float = Field(gt=0, lt=1)
    gasto_familiar: float = Field(ge=0)
    otras_cuotas: float = Field(0, ge=0)
    dias_atraso_max: int = Field(0, ge=0)
    creditos_previos: int | None = None
    pct_cobros_yape: float | None = None
    antiguedad_negocio_anios: int | None = None
    ajuste_asesor: float = Field(1.0, ge=0.5, le=1.5)
    principal: float = Field(gt=0)
    plazo: int = Field(gt=0, le=36)
    tea: float = Field(gt=0, lt=2)
    mes_desembolso: int = Field(0, ge=0, le=11)
    historial_ventas: list[float] | None = None


@router.get("/cartera-demo")
def cartera_demo(n: int = 20, semilla: int = 7):
    if not 1 <= n <= 100:
        raise HTTPException(422, "n debe estar entre 1 y 100")
    clave = (n, semilla)
    if clave not in _CACHE_CARTERA:
        clientes, hist = generar_cartera(n, semilla, meses_historia=MESES_HIST)
        ventas = {k: g.sort_values("t")["ventas"].tolist() for k, g in hist.groupby("cliente_id")}
        filas = []
        for c in clientes.to_dict("records"):
            c["historial_ventas"] = ventas[c["cliente_id"]]
            c["indice_estacionalidad"] = round(indice_estacionalidad(c["rubro"]), 3)
            filas.append(_nativo(c))
        _CACHE_CARTERA[clave] = filas
    return _CACHE_CARTERA[clave]


def _semilla(cli: dict) -> int:
    """Semilla estable por cliente: misma entrada -> mismo resultado."""
    clave = f"{cli['cliente_id']}|{cli['rubro']}|{cli['ventas_medias']:.2f}|{cli['mes_desembolso']}"
    return int(hashlib.sha256(clave.encode()).hexdigest()[:8], 16)


def _comparar(cli: dict, prop: dict, par: dict) -> dict:
    h = max(par["credito"]["plazos_meses"] + [cli["plazo"], prop["plazo"]])
    semilla = _semilla(cli)

    def correr(cuotas, tem, principal, plazo, aplz, alivio):
        rng = np.random.default_rng(semilla)  # mismas trayectorias para ambas estrategias
        ventas = simular_ventas(cli["rubro"], cli["ventas_medias"], h, rng, cli["mes_desembolso"], N_ESCENARIOS)[:, :plazo]
        nino = _trayectorias_el_nino(N_ESCENARIOS, h, rng, par)[:, :plazo]
        r = simular_credito({**cli, "principal": principal}, np.asarray(cuotas, float), tem, ventas, nino, par, aplz, alivio)
        return {"mora30": float(r["mora30"].mean()), "default": float(r["default"].mean()),
                "vpn_medio": round(float(r["vpn"].mean()), 2), "vpn_p5": round(float(np.percentile(r["vpn"], 5)), 2),
                "cuotas": [round(float(c), 2) for c in cuotas]}

    tem_f = tea_a_tem(cli["tea"])
    fija = np.full(cli["plazo"], round(cuota_francesa(cli["principal"], tem_f, cli["plazo"]), 2))
    flex = [f["cuota"] for f in prop["cronograma"]]
    return {
        "fija": correr(fija, tem_f, cli["principal"], cli["plazo"], 0, False),
        "cuotaflex": correr(flex, tea_a_tem(prop["tea"]), prop["principal_aprobado"], prop["plazo"],
                            prop["aplazamientos_disponibles"], prop["clausula_el_nino"]),
        "n_escenarios": N_ESCENARIOS,
    }


@router.post("/propuesta")
def propuesta(sol: ClienteSolicitud):
    if sol.rubro not in RUBROS:
        raise HTTPException(422, f"rubro inválido; use {list(RUBROS)}")
    par = copy.deepcopy(cargar_parametros())
    cli = sol.model_dump(exclude={"historial_ventas"})
    hist = sol.historial_ventas
    if not hist or len(hist) < 12:
        rng = np.random.default_rng(_semilla(cli))
        hist = simular_ventas(cli["rubro"], cli["ventas_medias"], MESES_HIST, rng,
                              (cli["mes_desembolso"] - MESES_HIST) % 12).round(2).tolist()
    historial = pd.DataFrame({"cliente_id": cli["cliente_id"], "t": range(-len(hist), 0), "ventas": hist})

    prop = _agente.proponer(cli, historial)
    q = pronosticar(pd.DataFrame([{**cli, "plazo": prop["plazo"]}]), historial, metodo="mixto")[cli["cliente_id"]]
    ratio = par["capacidad_pago"]["ratio_cuota_excedente_max"]
    capacidad = [round(max(f["excedente_p25"], 0) * ratio, 2) for f in prop["cronograma"]]

    return _nativo({
        "propuesta": prop,
        "historial_ventas": [round(float(v), 2) for v in hist],
        "pronostico": {k: np.round(q[i], 2) for i, k in enumerate(("p10", "p25", "p50", "p90"))},
        "capacidad": capacidad,
        "comparativa": _comparar(cli, prop, par),
    })
