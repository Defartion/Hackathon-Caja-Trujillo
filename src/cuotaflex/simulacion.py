"""Simulación Monte Carlo: cuota fija vs. CuotaFlex sobre la misma cartera y mismas semillas.

Para cada crédito se simulan trayectorias de ventas (estacionalidad + choques + El Niño) y
el flujo de caja del negocio. Se miden mora (>30 días), default y rentabilidad para la Caja.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .agente import AgenteAsesor
from .config import cargar_parametros, cuota_francesa, factores_descuento, tea_a_tem
from .datos import RUBROS, generar_cartera, simular_ventas
from .pronostico import pronosticar


def _trayectorias_el_nino(n_tray: int, plazo: int, rng, par: dict) -> np.ndarray:
    """Matriz booleana (n_tray, plazo): meses con alerta de El Niño costero activa."""
    en = par["el_nino"]
    activo = np.zeros((n_tray, plazo), dtype=bool)
    ocurre = rng.random(n_tray) < 1 - (1 - en["probabilidad_anual"]) ** (plazo / 12)
    inicio = rng.integers(0, plazo, n_tray)
    dur = rng.integers(3, 7, n_tray)
    for k in np.where(ocurre)[0]:
        activo[k, inicio[k]:inicio[k] + dur[k]] = True
    return activo


def simular_credito(cli: dict, cuotas: np.ndarray, tem: float, ventas: np.ndarray, nino: np.ndarray,
                    par: dict, aplazamientos: int = 0, alivio_nino: bool = False) -> dict:
    """Simula el pago de un crédito en n_tray trayectorias (vectorizado)."""
    sim, fx, cr = par["simulacion"], par["flexibilidad"], par["credito"]
    n_tray, n = ventas.shape
    caida = par["el_nino"]["caida_ingresos"].get(cli["rubro"], 0.05)
    ventas = ventas * np.where(nino, 1 - caida, 1.0)
    excedente = ventas * cli["margen"] - cli["gasto_familiar"] - cli["otras_cuotas"]

    ref = cuota_francesa(cli["principal"], tem, n)
    piso = fx["cuota_minima_pct"] * ref
    prog = np.tile(np.asarray(cuotas, float), (n_tray, 1))   # cronograma vigente por trayectoria
    caja = np.full(n_tray, sim["colchon_meses"] * max(cli["ventas_medias"] * cli["margen"] - cli["gasto_familiar"], 0))
    atraso = np.zeros(n_tray)
    meses_atraso = np.zeros(n_tray, int)
    aplaz_rest = np.full(n_tray, aplazamientos)
    alivio_rest = np.full(n_tray, par["el_nino"]["meses_alivio"] if alivio_nino else 0)
    vivo = np.ones(n_tray, bool)
    mora30 = np.zeros(n_tray, bool)
    usados = np.zeros(n_tray, int)
    cobros = np.zeros((n_tray, n + 1))
    d_fondeo = (1 + tea_a_tem(cr["costo_fondeo_tea"])) ** -np.arange(0, n + 1)

    for t in range(n):
        caja = caja + np.where(vivo, excedente[:, t], 0)
        cuota_t = prog[:, t].copy()
        restantes = n - t - 1
        # alivio El Niño (automático, por alerta ENFEN) o aplazamiento (a pedido, si está al día)
        usa_alivio = vivo & nino[:, t] & (alivio_rest > 0) & (cuota_t > piso)
        pide = vivo & ~usa_alivio & (caja < cuota_t + atraso) & (aplaz_rest > 0) & (atraso <= 0.01) & (cuota_t > piso)
        flex = usa_alivio | pide
        if restantes > 0 and flex.any():
            diferido = np.where(flex, cuota_t - piso, 0)
            prog[:, t + 1:] += (diferido * tem /(1 - (1 + tem) ** -restantes))[:, None] \
                if tem > 0 else (diferido / restantes)[:, None]
            cuota_t = np.where(flex, piso, cuota_t)
            alivio_rest -= usa_alivio
            aplaz_rest -= pide
            usados += pide
        debido = np.where(vivo, cuota_t + atraso, 0)
        pago = np.clip(np.minimum(caja, debido), 0, None)
        caja = (caja - pago) * (1 - sim.get("fuga_caja_mensual", 0.0))
        atraso = debido - pago
        cobros[:, t + 1] += pago
        en_atraso = vivo & (atraso > 0.05 * ref)
        meses_atraso = np.where(en_atraso, meses_atraso + 1, 0)
        mora30 |= en_atraso
        # pierde la flexibilidad si acumula atrasos
        aplaz_rest = np.where(meses_atraso * 30 >= fx["pierde_flex_con_atraso_dias"], 0, aplaz_rest)
        cae = vivo & (meses_atraso >= sim["meses_default"])
        if cae.any():
            saldo = atraso + (prog[:, t + 1:] * (1 + tem) ** -np.arange(1, restantes + 1)).sum(axis=1)
            cobros[:, t + 1] += np.where(cae, cr["recuperacion_default"] * saldo, 0)
            vivo &= ~cae
    # cobro final de atrasos remanentes al cierre (si queda caja en el mes siguiente)
    vpn = cobros @ d_fondeo - cli["principal"] - cr["costo_operativo_pct"] * cli["principal"] * n / 24
    return {"mora30": mora30, "default": ~vivo, "vpn": vpn, "aplazamientos_usados": usados,
            "atraso_final": atraso > 0.05 * ref}


def comparar_cartera(n_clientes: int | None = None, n_escenarios: int | None = None,
                     semilla: int | None = None, metodo_pronostico: str = "perfil",
                     par: dict | None = None, replanificar: bool = True) -> tuple[pd.DataFrame, dict]:
    """Corre la comparación completa. Devuelve (detalle por crédito, resumen de KPIs)."""
    par = par or cargar_parametros()
    sim = par["simulacion"]
    n_esc = n_escenarios or sim["n_escenarios"]
    semilla = sim["semilla"] if semilla is None else semilla
    clientes, hist = generar_cartera(n_clientes, semilla)
    h = max(par["credito"]["plazos_meses"])
    q = pronosticar(clientes.assign(plazo=h), hist, metodo=metodo_pronostico)
    agente = AgenteAsesor(par, metodo_pronostico, replanificar)
    rng_base = np.random.default_rng(semilla + 1)
    filas = []
    for cli in clientes.to_dict("records"):
        prop = agente.proponer(cli, pronostico_24m=q[cli["cliente_id"]])
        semilla_cli = int(rng_base.integers(1 << 31))
        for estrategia in ("fija", "cuotaflex"):
            rng = np.random.default_rng(semilla_cli)  # mismas trayectorias para ambas estrategias
            if estrategia == "fija":
                c, tem, plazo, aplz, alivio = None, tea_a_tem(cli["tea"]), cli["plazo"], 0, False
                principal = cli["principal"]
            else:
                c = np.array([f["cuota"] for f in prop["cronograma"]])
                tem, plazo, principal = tea_a_tem(prop["tea"]), prop["plazo"], prop["principal_aprobado"]
                aplz, alivio = prop["aplazamientos_disponibles"], prop["clausula_el_nino"]
            ventas = simular_ventas(cli["rubro"], cli["ventas_medias"], h, rng, cli["mes_desembolso"], n_esc)[:, :plazo]
            nino = _trayectorias_el_nino(n_esc, h, rng, par)[:, :plazo]
            ccli = {**cli, "principal": principal}
            if c is None:
                c = np.full(plazo, cuota_francesa(principal, tem, plazo))
            r = simular_credito(ccli, c, tem, ventas, nino, par, aplz, alivio)
            filas.append({"cliente_id": cli["cliente_id"], "rubro": cli["rubro"], "estrategia": estrategia,
                          "producto": prop["producto"] if estrategia == "cuotaflex" else "fija",
                          "principal": principal, "mora30": r["mora30"].mean(), "default": r["default"].mean(),
                          "vpn": r["vpn"].mean(), "vpn_p5": np.percentile(r["vpn"], 5),
                          "aplazamientos_usados": r["aplazamientos_usados"].mean()})
    det = pd.DataFrame(filas)
    return det, resumir(det)


def resumir(det: pd.DataFrame) -> dict:
    res = {}
    for e, g in det.groupby("estrategia"):
        res[e] = {"mora30_pct": round(100 * g["mora30"].mean(), 2), "default_pct": round(100 * g["default"].mean(), 2),
                  "margen_neto_total": round(g["vpn"].sum(), 0), "cartera": round(g["principal"].sum(), 0),
                  "margen_sobre_cartera_pct": round(100 * g["vpn"].sum() / g["principal"].sum(), 2)}
    f, x = res.get("fija"), res.get("cuotaflex")
    if f and x:
        res["delta"] = {"mora30_relativa_pct": round(100 * (x["mora30_pct"] / f["mora30_pct"] - 1), 1) if f["mora30_pct"] else None,
                        "default_relativo_pct": round(100 * (x["default_pct"] / f["default_pct"] - 1), 1) if f["default_pct"] else None,
                        "margen_neto_dif": round(x["margen_neto_total"] - f["margen_neto_total"], 0)}
    por_rubro = det.pivot_table(index="rubro", columns="estrategia", values=["mora30", "vpn"], aggfunc="mean")
    res["por_rubro"] = {r: {"mora30_fija": round(100 * row[("mora30", "fija")], 1),
                            "mora30_cuotaflex": round(100 * row[("mora30", "cuotaflex")], 1),
                            "vpn_fija": round(row[("vpn", "fija")], 0), "vpn_cuotaflex": round(row[("vpn", "cuotaflex")], 0)}
                        for r, row in por_rubro.iterrows()}
    res["mix_productos"] = det[det.estrategia == "cuotaflex"]["producto"].value_counts().to_dict()
    return res
