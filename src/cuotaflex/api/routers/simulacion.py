"""Lote C · Endpoints del tablero de simulación en vivo.

GET  /simulacion/parametros-editables -> controles del tablero (ruta, etiqueta, rango, paso, valor actual, ayuda)
GET  /simulacion/escenarios           -> escenarios predefinidos para los botones del tablero
POST /simulacion/correr               -> cuota fija vs. CuotaFlex sobre la cartera sintética, con los cambios pedidos

Los cambios se aplican sobre una copia profunda de los parámetros: `cargar_parametros()` está
cacheado y devuelve siempre el mismo dict, así que modificarlo alteraría toda la API.

Rendimiento: casi todo el tiempo de `comparar_cartera` se va en los cronogramas óptimos (MILP) que
el agente resuelve uno por uno (~30 ms cada uno, cientos por corrida). Para cumplir los tiempos del
tablero, las corridas grandes reparten esos cronogramas entre procesos trabajadores y después llaman
a `comparar_cartera` en un trabajador que los toma de memoria. El resultado es idéntico al secuencial
(la memoria se indexa por las entradas exactas del optimizador y, si falta alguna, se calcula). El
motor no se modifica y el proceso de la API tampoco: el envoltorio solo existe en los trabajadores.
`CUOTAFLEX_SIM_PROCESOS` fija el número de procesos (0 o 1 = todo en secuencia).
"""
from __future__ import annotations

import concurrent.futures as cf
import copy
import hashlib
import json
import logging
import math
import multiprocessing as mp
import os
import pickle
import threading
import time
from collections import OrderedDict

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ... import agente as motor_agente
from ... import optimizador as motor_optimizador
from ... import simulacion
from ...agente import AgenteAsesor
from ...config import cargar_parametros
from ...datos import generar_cartera
from ...pronostico import pronosticar

router = APIRouter(prefix="/simulacion", tags=["simulacion"])
log = logging.getLogger(__name__)

MAX_CLIENTES = 600
MAX_ESCENARIOS = 300
MAX_CACHE = 50
N_TRAMOS = 20
MIN_CLIENTES_PARALELO = 50        # por debajo, arrancar procesos no compensa
TIEMPO_MAX_TRABAJADOR_S = 300
PAUSA_TRAS_FALLO_S = 600          # si el modo paralelo falla, se usa el secuencial durante 10 min
# Los trabajadores heredan el entorno al arrancar. Con BLAS de un hilo cada proceso reserva ~130 MB en
# vez de ~2,2 GB en Windows (OpenBLAS, en numpy y en scipy, reserva búferes por hilo al importarse).
ENTORNO_TRABAJADOR = {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

# minimo/maximo/paso: rango del deslizador. limites: valores que acepta /correr (los escenarios de
# control pueden salir del rango del deslizador, p. ej. la cuota mínima al 95%).
PARAMETROS_EDITABLES: dict[str, dict] = {
    "flexibilidad.max_aplazamientos": {
        "grupo": "Flexibilidad", "etiqueta": "Aplazamientos por crédito",
        "minimo": 0, "maximo": 4, "paso": 1, "formato": "entero", "limites": (0, 12),
        "ayuda": "Veces que el cliente con producto de aplazamiento puede pagar solo la cuota mínima "
                 "en un mes difícil, si está al día. Lo diferido se reparte con interés en las cuotas siguientes.",
    },
    "flexibilidad.cuota_minima_pct": {
        "grupo": "Flexibilidad", "etiqueta": "Cuota mínima (% de la fija)",
        "minimo": 0.20, "maximo": 0.60, "paso": 0.05, "formato": "pct", "limites": (0.0, 1.0),
        "ayuda": "Piso de cualquier cuota frente a la cuota fija equivalente. Es lo que se paga en un "
                 "aplazamiento o durante el alivio El Niño, y el mínimo de una cuota estacional.",
    },
    "flexibilidad.cuota_maxima_mult": {
        "grupo": "Flexibilidad", "etiqueta": "Cuota máxima (× la fija)",
        "minimo": 1.2, "maximo": 2.5, "paso": 0.1, "formato": "mult", "limites": (1.0, 5.0),
        "ayuda": "Techo de cualquier cuota del cronograma estacional frente a la cuota fija. "
                 "Evita cuotas globo en temporada alta.",
    },
    "flexibilidad.recargo_spread_tea": {
        "grupo": "Flexibilidad", "etiqueta": "Recargo por flexibilidad (TEA)",
        "minimo": 0.0, "maximo": 0.05, "paso": 0.005, "formato": "pp", "limites": (0.0, 0.5),
        "ayuda": "Puntos de TEA que se suman a la tasa cuando el producto es flexible (aplazamiento o "
                 "estacional). Compensa a la Caja por el costo de la opción.",
    },
    "flexibilidad.requisito_dias_atraso_max": {
        "grupo": "Flexibilidad", "etiqueta": "Atraso máximo para acceder",
        "minimo": 0, "maximo": 30, "paso": 1, "formato": "dias", "limites": (0, 365),
        "ayuda": "Máximo atraso histórico, en días, para acceder a un producto flexible. "
                 "Quien lo supera recibe cuota fija.",
    },
    "capacidad_pago.ratio_cuota_excedente_max": {
        "grupo": "Capacidad de pago", "etiqueta": "Cuota / excedente máx.",
        "minimo": 0.5, "maximo": 0.9, "paso": 0.05, "formato": "pct", "limites": (0.1, 1.0),
        "ayuda": "Parte del excedente mensual del escenario conservador (p25) que puede comprometer la "
                 "cuota. En modo Completo, si no cabe, el agente alarga el plazo o reduce el monto.",
    },
    "capacidad_pago.ratio_deuda_total_max": {
        "grupo": "Capacidad de pago", "etiqueta": "Deuda total / excedente máx.",
        "minimo": 0.6, "maximo": 1.0, "paso": 0.05, "formato": "pct", "limites": (0.1, 2.0),
        "ayuda": "Límite de sobreendeudamiento: (cuota nueva + otras cuotas) / excedente medio. "
                 "Quien lo supera no accede a flexibilidad.",
    },
    "el_nino.probabilidad_anual": {
        "grupo": "El Niño costero", "etiqueta": "Probabilidad anual de El Niño",
        "minimo": 0.0, "maximo": 1.0, "paso": 0.05, "formato": "pct", "limites": (0.0, 1.0),
        "ayuda": "Probabilidad de que el ENFEN declare alerta de El Niño costero en un año. Cada episodio "
                 "dura de 3 a 6 meses y golpea sobre todo a agricultura, pesca y comercio de campaña.",
    },
    "el_nino.meses_alivio": {
        "grupo": "El Niño costero", "etiqueta": "Meses de alivio El Niño",
        "minimo": 0, "maximo": 6, "paso": 1, "formato": "meses", "limites": (0, 24),
        "ayuda": "Cuotas que bajan al mínimo de forma automática mientras dura la alerta, en los rubros "
                 "expuestos. Lo diferido se reparte en las cuotas siguientes.",
    },
    "simulacion.fuga_caja_mensual": {
        "grupo": "Comportamiento del cliente", "etiqueta": "Gasto del sobrante mensual",
        "minimo": 0.0, "maximo": 0.4, "paso": 0.05, "formato": "pct", "limites": (0.0, 1.0),
        "ayuda": "Parte de lo que le sobra al negocio cada mes que no se guarda para la siguiente cuota. "
                 "Con 0% el cliente ahorra todo y la flexibilidad aporta poco: es el supuesto clave a validar.",
    },
}
_ENTEROS = {r for r, p in PARAMETROS_EDITABLES.items() if p["formato"] in ("entero", "dias", "meses")}

ESCENARIOS = [
    {"id": "base", "nombre": "Base", "cambios": {},
     "descripcion": "Parámetros vigentes de config/parametros.yaml, sin cambios."},
    {"id": "el_nino", "nombre": "Año El Niño", "cambios": {"el_nino.probabilidad_anual": 1.0},
     "descripcion": "El ENFEN declara alerta en todos los escenarios: se ve el efecto del alivio automático."},
    {"id": "sin_flexibilidad", "nombre": "Sin flexibilidad",
     "cambios": {"flexibilidad.max_aplazamientos": 0, "flexibilidad.cuota_minima_pct": 0.95,
                 "flexibilidad.recargo_spread_tea": 0.0},
     "descripcion": "Control: sin aplazamientos, cuota mínima al 95% de la fija y sin recargo. Lo que "
                    "quede de mejora viene del dimensionamiento del monto y del plazo."},
    {"id": "ahorrador", "nombre": "Cliente ahorrador", "cambios": {"simulacion.fuga_caja_mensual": 0.0},
     "descripcion": "El cliente guarda todo lo que le sobra cada mes: muestra cuándo la flexibilidad aporta poco."},
    {"id": "estricta", "nombre": "Política estricta", "cambios": {"capacidad_pago.ratio_deuda_total_max": 0.6},
     "descripcion": "Deuda total hasta el 60% del excedente: menos clientes acceden a productos flexibles."},
]


class CorridaIn(BaseModel):
    n_clientes: int = Field(200, ge=1, le=MAX_CLIENTES)
    n_escenarios: int = Field(100, ge=1, le=MAX_ESCENARIOS)
    semilla: int = Field(2026, ge=0, le=2**31 - 1)
    replanificar: bool = Field(True, description="True = Completo (ajusta monto y plazo); False = solo cronograma")
    cambios: dict[str, float] = Field(default_factory=dict, description="ruta editable -> nuevo valor")


_cache: OrderedDict[str, dict] = OrderedDict()
_candado_cache = threading.Lock()
_candado_simulacion = threading.Lock()  # una simulación a la vez: el motor es intensivo en CPU


def _leer(par: dict, ruta: str):
    seccion, clave = ruta.split(".")
    return par[seccion][clave]


def _escribir(par: dict, ruta: str, valor) -> None:
    seccion, clave = ruta.split(".")
    par[seccion][clave] = valor


def _nativo(x):
    """Convierte tipos de NumPy/pandas a tipos nativos de Python (recursivo). NaN e infinito -> None."""
    if isinstance(x, dict):
        return {str(k): _nativo(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_nativo(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_nativo(v) for v in x.tolist()]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(x) else None
    return x


def _validar_cambios(cambios: dict[str, float]) -> dict[str, float | int]:
    limpios: dict[str, float | int] = {}
    for ruta, valor in cambios.items():
        if ruta not in PARAMETROS_EDITABLES:
            raise HTTPException(422, f"'{ruta}' no es un parámetro editable. Use una de: {', '.join(PARAMETROS_EDITABLES)}")
        lo, hi = PARAMETROS_EDITABLES[ruta]["limites"]
        if not math.isfinite(valor) or not lo <= valor <= hi:
            raise HTTPException(422, f"{ruta}: el valor {valor} está fuera del rango permitido [{lo}, {hi}]")
        if ruta in _ENTEROS:
            if not float(valor).is_integer():
                raise HTTPException(422, f"{ruta}: debe ser un número entero")
            valor = int(valor)
        limpios[ruta] = valor
    return limpios


def _histograma(det: pd.DataFrame) -> dict:
    """20 tramos comunes a las dos estrategias sobre el VPN medio por crédito."""
    vpn = det["vpn"].to_numpy(dtype=float)
    finito = np.isfinite(vpn)
    bordes = np.histogram_bin_edges(vpn[finito], bins=N_TRAMOS)
    out = {"bordes": np.round(bordes, 2)}
    for estrategia in ("fija", "cuotaflex"):
        sel = finito & (det["estrategia"].to_numpy() == estrategia)
        out[estrategia] = np.histogram(vpn[sel], bins=bordes)[0]
    return out


def _dispersion(det: pd.DataFrame) -> list[dict]:
    """Mora > 30 días de cada cliente con cuota fija (x) y con CuotaFlex (y)."""
    fija = det[det["estrategia"] == "fija"].set_index("cliente_id")
    flex = det[det["estrategia"] == "cuotaflex"].set_index("cliente_id")
    return [{"cliente_id": cid, "rubro": flex.at[cid, "rubro"], "producto": flex.at[cid, "producto"],
             "mora_fija": round(float(fija.at[cid, "mora30"]), 4), "mora_flex": round(float(flex.at[cid, "mora30"]), 4)}
            for cid in flex.index]


# ---------------------------------------------------------------------------------------------
# Procesos trabajadores: cronogramas en paralelo con memoria (solo se ejecuta dentro de ellos)
# ---------------------------------------------------------------------------------------------
_memoria: dict[bytes, dict] = {}
_contador = {"aciertos": 0, "calculados": 0}


def _clave_cronograma(principal, tem, capacidad, par, suavidad) -> bytes:
    """Entradas exactas de `optimizar_cronograma` (bit a bit): misma clave -> mismo resultado."""
    fx = (par or cargar_parametros())["flexibilidad"]
    datos = (float(principal), float(tem), np.ascontiguousarray(capacidad, dtype=float).tobytes(),
             tuple(sorted(fx.items())), float(suavidad))
    return hashlib.sha1(pickle.dumps(datos)).digest()


def _optimizar_con_memoria(principal, tem, capacidad, par=None, suavidad=0.02):
    clave = _clave_cronograma(principal, tem, capacidad, par, suavidad)
    r = _memoria.get(clave)
    if r is None:
        r = motor_optimizador.optimizar_cronograma(principal, tem, capacidad, par, suavidad)
        _memoria[clave] = r
        _contador["calculados"] += 1
    else:
        _contador["aciertos"] += 1
    return {**r, "cuotas": np.array(r["cuotas"], dtype=float, copy=True)}


def _iniciar_trabajador() -> None:
    motor_agente.optimizar_cronograma = _optimizar_con_memoria


def _calentar_trabajador() -> None:
    """Importa y ejercita CVXPY/HiGHS para que la primera corrida no pague el arranque."""
    motor_optimizador.optimizar_cronograma(5000.0, 0.03, np.full(12, 600.0), cargar_parametros())
    time.sleep(0.2)  # deja que cada tarea caiga en un proceso distinto


def _proponer_lote(par: dict, replanificar: bool, clientes: list[dict], pronosticos: list) -> dict:
    """Resuelve las propuestas de un grupo de clientes y devuelve los cronogramas calculados."""
    _memoria.clear()
    agente = AgenteAsesor(par, "perfil", replanificar)
    for cli, q in zip(clientes, pronosticos):
        agente.proponer(cli, pronostico_24m=q)
    return dict(_memoria)


def _comparar_con_memoria(consulta: dict, par: dict, memoria: dict):
    _memoria.clear()
    _memoria.update(memoria)
    _contador.update(aciertos=0, calculados=0)
    det, resumen = simulacion.comparar_cartera(consulta["n_clientes"], consulta["n_escenarios"], consulta["semilla"],
                                               "perfil", par, consulta["replanificar"])
    return det, resumen, dict(_contador)


# ---------------------------------------------------------------------------------------------
# Proceso de la API: reparto del trabajo
# ---------------------------------------------------------------------------------------------
_pool: cf.ProcessPoolExecutor | None = None
_pool_procesos = 0
_candado_pool = threading.Lock()
_paralelo_pausado_hasta = 0.0


def _n_procesos() -> int:
    valor = os.getenv("CUOTAFLEX_SIM_PROCESOS")
    if valor is not None:
        try:
            return max(0, int(valor))
        except ValueError:
            return 0
    return max(0, min(10, (os.cpu_count() or 1) - 2))  # deja dos núcleos para la API y el navegador


def _obtener_pool(n: int) -> cf.ProcessPoolExecutor:
    global _pool, _pool_procesos
    with _candado_pool:
        if _pool is None or _pool_procesos != n:
            if _pool is not None:
                _pool.shutdown(wait=False, cancel_futures=True)
            for clave, valor in ENTORNO_TRABAJADOR.items():
                os.environ.setdefault(clave, valor)  # respeta lo que haya fijado el usuario
            _pool = cf.ProcessPoolExecutor(max_workers=n, mp_context=mp.get_context("spawn"),
                                           initializer=_iniciar_trabajador)
            _pool_procesos = n
        return _pool


def _descartar_pool() -> None:
    global _pool
    with _candado_pool:
        if _pool is not None:
            _pool.shutdown(wait=False, cancel_futures=True)
            _pool = None


def _calentar_pool() -> None:
    """Arranca los procesos en segundo plano (el tablero lo pide al cargar), sin esperar."""
    n = _n_procesos()
    with _candado_pool:
        listo = _pool is not None and _pool_procesos == n
    if n >= 2 and not listo and time.monotonic() >= _paralelo_pausado_hasta:
        pool = _obtener_pool(n)
        for _ in range(n):
            pool.submit(_calentar_trabajador)


def _correr_paralelo(consulta: dict, par: dict, n: int):
    pool = _obtener_pool(n)
    t0 = time.perf_counter()
    # mismo arranque que comparar_cartera: cartera, horizonte y pronóstico
    clientes, hist = generar_cartera(consulta["n_clientes"], consulta["semilla"])
    h = max(par["credito"]["plazos_meses"])
    q = pronosticar(clientes.assign(plazo=h), hist, metodo="perfil")
    registros = clientes.to_dict("records")
    lotes = [registros[i::n] for i in range(n)]
    futuros = [pool.submit(_proponer_lote, par, consulta["replanificar"], lote, [q[c["cliente_id"]] for c in lote])
               for lote in lotes if lote]
    memoria: dict[bytes, dict] = {}
    for f in futuros:
        memoria.update(f.result(timeout=TIEMPO_MAX_TRABAJADOR_S))
    t1 = time.perf_counter()
    det, resumen, contador = pool.submit(_comparar_con_memoria, consulta, par, memoria).result(timeout=TIEMPO_MAX_TRABAJADOR_S)
    return det, resumen, {"modo": "paralelo", "procesos": n, "cronogramas_en_paralelo": len(memoria),
                          "cronogramas_de_memoria": contador["aciertos"], "cronogramas_recalculados": contador["calculados"],
                          "s_cronogramas": round(t1 - t0, 2), "s_simulacion": round(time.perf_counter() - t1, 2)}


def _correr_motor(consulta: dict, par: dict):
    global _paralelo_pausado_hasta
    n = _n_procesos()
    if n >= 2 and consulta["n_clientes"] >= MIN_CLIENTES_PARALELO and time.monotonic() >= _paralelo_pausado_hasta:
        try:
            return _correr_paralelo(consulta, par, n)
        except Exception:  # proceso caído, memoria, tiempo agotado...: se repite en secuencia
            log.exception("La simulación en paralelo falló; se calcula en secuencia y el modo paralelo "
                          "queda en pausa %d s", PAUSA_TRAS_FALLO_S)
            _paralelo_pausado_hasta = time.monotonic() + PAUSA_TRAS_FALLO_S
            _descartar_pool()
    det, resumen = simulacion.comparar_cartera(consulta["n_clientes"], consulta["n_escenarios"], consulta["semilla"],
                                               "perfil", par, consulta["replanificar"])
    return det, resumen, {"modo": "secuencial", "procesos": 1}


def _calcular(consulta: dict) -> dict:
    par = copy.deepcopy(cargar_parametros())
    for ruta, valor in consulta["cambios"].items():
        _escribir(par, ruta, valor)
    t0 = time.perf_counter()
    det, resumen, rendimiento = _correr_motor(consulta, par)
    out = {
        "resumen": resumen,
        "histograma_vpn": _histograma(det),
        "dispersion": _dispersion(det),
        "duracion_s": round(time.perf_counter() - t0, 2),
        "parametros_usados": {ruta: _leer(par, ruta) for ruta in PARAMETROS_EDITABLES},
        "consulta": consulta,
        "rendimiento": rendimiento,
    }
    return _nativo(out)


def _de_cache(clave: str) -> dict | None:
    with _candado_cache:
        if clave in _cache:
            _cache.move_to_end(clave)
            return _cache[clave]
    return None


def _a_cache(clave: str, valor: dict) -> None:
    with _candado_cache:
        _cache[clave] = valor
        _cache.move_to_end(clave)
        while len(_cache) > MAX_CACHE:
            _cache.popitem(last=False)


@router.get("/parametros-editables")
def parametros_editables():
    _calentar_pool()           # el tablero llama aquí al cargar: los procesos arrancan mientras se elige
    par = cargar_parametros()  # solo lectura
    return [{"ruta": ruta, **{k: v for k, v in p.items() if k != "limites"},
             "rango_valido": list(p["limites"]), "valor": _leer(par, ruta)}
            for ruta, p in PARAMETROS_EDITABLES.items()]


@router.get("/escenarios")
def escenarios():
    return copy.deepcopy(ESCENARIOS)


@router.post("/correr")
def correr(c: CorridaIn):
    consulta = {"n_clientes": c.n_clientes, "n_escenarios": c.n_escenarios, "semilla": c.semilla,
                "replanificar": c.replanificar, "cambios": _validar_cambios(c.cambios)}
    clave = hashlib.sha256(json.dumps(consulta, sort_keys=True).encode()).hexdigest()
    resultado, desde_cache = _de_cache(clave), True
    if resultado is None:
        with _candado_simulacion:
            resultado = _de_cache(clave)  # otra petición idéntica pudo terminarla mientras esperábamos
            if resultado is None:
                resultado, desde_cache = _calcular(consulta), False
                _a_cache(clave, resultado)
    return {**resultado, "desde_cache": desde_cache}
