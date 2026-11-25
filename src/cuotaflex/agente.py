"""Agente asesor: orquesta las herramientas del motor y deja una bitácora explicable.

Plan del agente para cada solicitud:
  1. evaluar elegibilidad y sobreendeudamiento  -> politica
  2. pronosticar ventas con incertidumbre        -> pronostico
  3. elegir producto según perfil y estacionalidad
  4. optimizar cronograma (MILP); si no cabe, re-planificar con plazo mayor o monto menor
  5. validar contra políticas de riesgo
  6. explicar la propuesta al asesor y al cliente (plantilla o LLM opcional)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import cargar_parametros, cuota_francesa, desglose_cronograma, tea_a_tem
from .optimizador import optimizar_cronograma
from .politica import (PRODUCTOS, aplica_clausula_el_nino, evaluar_elegibilidad,
                       recargo_producto, recomendar_producto, validar_cronograma)
from .pronostico import excedente_cuantiles, pronosticar
from .seleccion import seleccionar_por_simulacion

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]


class AgenteAsesor:
    def __init__(self, par: dict | None = None, metodo_pronostico: str | None = None,
                 replanificar: bool = True):
        """replanificar=False mantiene monto y plazo solicitados (aísla el efecto del cronograma)."""
        self.par = par or cargar_parametros()
        self.metodo = metodo_pronostico
        self.replanificar = replanificar

    def _dimensionar(self, cliente: dict, producto: str, pronostico_24m: np.ndarray) -> dict:
        """Cronograma, monto y plazo para una modalidad; replanifica (plazo mayor, luego monto menor)."""
        par, pasos, cli = self.par, [], dict(cliente)
        plazos = [p for p in par["credito"]["plazos_meses"] if p >= cli["plazo"]] or [cli["plazo"]]
        principal = cli["principal"]
        tea = cli["tea"] + recargo_producto(par, producto)
        tem = tea_a_tem(tea)
        intentos = len(plazos) + 3
        for intento in range(intentos):
            cli["plazo"] = plazos[min(intento, len(plazos) - 1)]
            exc = excedente_cuantiles(cli, pronostico_24m[:, :cli["plazo"]])  # (4, plazo): p10, p25, p50, p90
            capacidad = np.maximum(exc[1], 0) * par["capacidad_pago"]["ratio_cuota_excedente_max"]
            if producto == "estacional":
                cuotas = optimizar_cronograma(principal, tem, capacidad, par)["cuotas"]
            else:
                cuotas = np.full(cli["plazo"], round(cuota_francesa(principal, tem, cli["plazo"]), 2))
            deficit = float(np.sum(np.maximum(cuotas - capacidad, 0)))
            pasos.append({"paso": "cronograma", "plazo": cli["plazo"], "principal": principal,
                          "deficit_p25": round(deficit, 2)})
            if deficit <= 0.02 * principal or not self.replanificar:
                break
            if len(plazos) - 1 <= intento < intentos - 1:  # ya no hay plazo mayor: reducir monto 10%
                principal = round(principal * 0.9, -2)
                pasos.append({"paso": "replanificar", "accion": "reducir monto", "nuevo_principal": principal})
        return {"plazo": cli["plazo"], "principal": principal, "tea": tea, "tem": tem, "cuotas": cuotas,
                "exc": exc, "pasos": pasos}

    def proponer(self, cliente: dict, historial: pd.DataFrame | None = None,
                 pronostico_24m: np.ndarray | None = None) -> dict:
        """pronostico_24m: cuantiles precalculados (4, >=24) para procesar carteras en lote."""
        par, bitacora = self.par, []
        cli = dict(cliente)
        if pronostico_24m is None:
            h = max(par["credito"]["plazos_meses"])
            pronostico_24m = pronosticar(pd.DataFrame([{**cli, "plazo": h}]), historial,
                                         metodo=self.metodo)[cli["cliente_id"]]
        eleg = evaluar_elegibilidad(cli, par)
        bitacora.append({"paso": "elegibilidad", **eleg})
        producto = recomendar_producto(cli, eleg)
        candidatos = [producto]
        preferido = cli.get("producto_preferido")
        if preferido in PRODUCTOS and (eleg["elegible_flex"] or preferido == "fija"):
            producto, candidatos = preferido, [preferido]  # el asesor fija la modalidad (p. ej. a pedido del cliente)
            bitacora.append({"paso": "producto_preferido", "producto": preferido})
        elif eleg["elegible_flex"] and par.get("seleccion", {}).get("modo", "regla") == "simulacion":
            candidatos = ["fija", "aplazamiento", "estacional"]
        dims = {p: self._dimensionar(cli, p, pronostico_24m) for p in candidatos}
        if len(candidatos) > 1:
            producto, paso_seleccion = seleccionar_por_simulacion(cli, dims, par, pronostico_24m)
            bitacora.append(paso_seleccion)
        bitacora.append({"paso": "producto", "producto": producto})
        d = dims[producto]
        bitacora.extend(d["pasos"])
        cli["plazo"], principal, tea, tem, cuotas, exc = (d["plazo"], d["principal"], d["tea"], d["tem"],
                                                         d["cuotas"], d["exc"])

        valid = validar_cronograma(principal, tem, cuotas, exc[2], par)
        bitacora.append({"paso": "validacion", **valid})
        meses = [(cli["mes_desembolso"] + k) % 12 for k in range(cli["plazo"])]
        prop = {
            "cliente_id": cli["cliente_id"], "producto": producto, "descripcion_producto": PRODUCTOS[producto],
            "principal_solicitado": cliente["principal"], "principal_aprobado": principal,
            "plazo": cli["plazo"], "tea": round(tea, 4), "cuota_fija_referencia": round(cuota_francesa(principal, tem, cli["plazo"]), 2),
            "clausula_el_nino": aplica_clausula_el_nino(cli, par),
            "aplazamientos_disponibles": par["flexibilidad"]["max_aplazamientos"] if producto == "aplazamiento" else 0,
            "cronograma": [{**f, "mes": MESES_ES[m], "excedente_p25": round(float(exc[1][i]), 2),
                            "excedente_p50": round(float(exc[2][i]), 2)}
                           for i, (f, m) in enumerate(zip(desglose_cronograma(principal, tem, cuotas), meses))],
            "valido": valid["valido"], "bitacora": bitacora,
        }
        prop["explicacion"] = self.explicar(prop, eleg)
        return prop

    def explicar(self, prop: dict, eleg: dict) -> str:
        from .explicador import explicar

        return explicar(prop, eleg, usar_llm=False)["texto"]
