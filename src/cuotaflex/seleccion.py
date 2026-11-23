"""Selección de producto por simulación (fase 2).

En lugar de una regla fija por estacionalidad, el agente construye las modalidades candidatas
(fija, aplazamiento, estacional), las simula en los mismos escenarios de ventas y El Niño del
cliente y elige la de menor default, siempre que el VPN para la Caja no caiga más de lo permitido
respecto de la cuota fija.
"""
from __future__ import annotations

import hashlib

import numpy as np

ORDEN_DESEMPATE = {"fija": 0, "aplazamiento": 1, "estacional": 2}


def semilla_cliente(cli: dict) -> int:
    clave = f"{cli['cliente_id']}|{cli['rubro']}|{float(cli['ventas_medias']):.2f}|{cli['mes_desembolso']}"
    return int(hashlib.sha256(clave.encode()).hexdigest()[:8], 16)


def escenarios_desde_pronostico(q: np.ndarray, n: int, rng, rho: float = 0.5) -> np.ndarray:
    """Trayectorias de ventas (n, h) coherentes con los cuantiles del pronóstico del cliente.

    Usa solo lo que la Caja conoce (p50 y la dispersión p10–p90 del pronóstico), con choques
    log-normales autocorrelacionados AR(1). No usa el generador de la cartera sintética.
    """
    from scipy.stats import norm

    p10, p50, p90 = np.maximum(q[0], 1.0), np.maximum(q[2], 1.0), np.maximum(q[3], 1.0)
    sigma = np.maximum(np.log(p90 / p10) / (2 * norm.ppf(0.9)), 0.03)
    h = q.shape[1]
    z = np.zeros((n, h))
    eps = rng.normal(size=(n, h))
    for t in range(h):
        z[:, t] = (rho * z[:, t - 1] if t else 0) + np.sqrt(1 - rho**2) * eps[:, t]
    return p50 * np.exp(sigma * z)


def simular_candidatos(cli: dict, dims: dict[str, dict], par: dict, pronostico_24m: np.ndarray,
                       n_escenarios: int | None = None) -> dict:
    """Métricas de riesgo y rentabilidad por modalidad, con las mismas trayectorias para todas."""
    from .simulacion import _trayectorias_el_nino, simular_credito  # diferido: simulacion importa agente

    n = n_escenarios or par.get("seleccion", {}).get("n_escenarios", 200)
    h = max([d["plazo"] for d in dims.values()] + par["credito"]["plazos_meses"])
    semilla = semilla_cliente(cli)
    alivio = cli["rubro"] in par["el_nino"]["rubros_expuestos"]
    res = {}
    for prod, d in dims.items():
        rng = np.random.default_rng(semilla)
        ventas = escenarios_desde_pronostico(pronostico_24m[:, :h], n, rng)[:, :d["plazo"]]
        nino = _trayectorias_el_nino(n, h, rng, par)[:, :d["plazo"]]
        aplz = par["flexibilidad"]["max_aplazamientos"] if prod == "aplazamiento" else 0
        r = simular_credito({**cli, "principal": d["principal"]}, np.asarray(d["cuotas"], float), d["tem"],
                            ventas, nino, par, aplz, alivio)
        res[prod] = {"default": round(float(r["default"].mean()), 4), "mora30": round(float(r["mora30"].mean()), 4),
                     "vpn": round(float(r["vpn"].mean()), 2)}
    return res


def elegir(metricas: dict[str, dict], max_perdida_vpn_pct: float) -> str:
    """Menor default; desempata por mora y VPN. Exige VPN >= VPN_fija - tolerancia."""
    vpn_fija = metricas["fija"]["vpn"]
    piso = vpn_fija - abs(vpn_fija) * max_perdida_vpn_pct / 100
    factibles = [p for p, m in metricas.items() if p == "fija" or m["vpn"] >= piso]
    return min(factibles, key=lambda p: (metricas[p]["default"], metricas[p]["mora30"], -metricas[p]["vpn"],
                                         ORDEN_DESEMPATE[p]))


def seleccionar_por_simulacion(cli: dict, dims: dict[str, dict], par: dict,
                               pronostico_24m: np.ndarray) -> tuple[str, dict]:
    metricas = simular_candidatos(cli, dims, par, pronostico_24m)
    tol = par.get("seleccion", {}).get("max_perdida_vpn_pct", 5)
    elegido = elegir(metricas, tol)
    return elegido, {"paso": "seleccion", "candidatos": metricas, "elegido": elegido,
                     "criterio": f"menor default con VPN >= fija - {tol}%"}
