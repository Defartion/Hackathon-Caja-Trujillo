"""API mock compatible con Apache Fineract + endpoints del motor CuotaFlex.

Imita la forma de los recursos de Fineract (/fineract-provider/api/v1) para que el cambio a
una instancia real sea directo. Almacenamiento en memoria (solo demo, datos sintéticos).
Ejecutar:  uvicorn cuotaflex.api.main:app --reload
"""
from __future__ import annotations

from datetime import date
from itertools import count

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..agente import AgenteAsesor
from ..config import cargar_parametros, cuota_francesa, desglose_cronograma, tea_a_tem
from ..datos import RUBROS, simular_ventas

BASE = "/fineract-provider/api/v1"
app = FastAPI(title="CuotaFlex · API compatible con Fineract", version="0.1.0")
DB: dict[str, dict] = {"clients": {}, "loans": {}}
_ids = count(1)
agente = AgenteAsesor(metodo_pronostico="perfil")


class ClienteIn(BaseModel):
    nombre: str
    rubro: str = Field(description=f"uno de: {', '.join(RUBROS)}")
    ventas_medias: float
    margen: float = 0.3
    gasto_familiar: float
    otras_cuotas: float = 0.0
    dias_atraso_max: int = 0
    ajuste_asesor: float = 1.0
    historial_ventas: list[float] | None = Field(None, description="últimos 12-36 meses; si falta se simula")


class PrestamoIn(BaseModel):
    clientId: int
    principal: float
    numberOfRepayments: int = 12
    tea: float | None = None
    mesPrimeraCuota: int = Field(date.today().month % 12, ge=0, le=11, description="0=ene .. 11=dic")


class AplazamientoIn(BaseModel):
    installment: int


def _cliente(cid: int) -> dict:
    if cid not in DB["clients"]:
        raise HTTPException(404, "cliente no existe")
    return DB["clients"][cid]


def _loan(lid: int) -> dict:
    if lid not in DB["loans"]:
        raise HTTPException(404, "préstamo no existe")
    return DB["loans"][lid]


@app.post(f"{BASE}/clients")
def crear_cliente(c: ClienteIn):
    if c.rubro not in RUBROS:
        raise HTTPException(400, f"rubro inválido; use {list(RUBROS)}")
    cid = next(_ids)
    DB["clients"][cid] = {"id": cid, **c.model_dump()}
    return {"clientId": cid, "resourceId": cid}


@app.get(f"{BASE}/clients/{{cid}}")
def ver_cliente(cid: int):
    return _cliente(cid)


@app.post(f"{BASE}/loans")
def crear_prestamo(p: PrestamoIn):
    """Crea el préstamo en estado 'Submitted and pending approval' con la propuesta del agente."""
    c = _cliente(p.clientId)
    par = cargar_parametros()
    cli = {"cliente_id": f"API{c['id']}", **{k: c[k] for k in ("rubro", "ventas_medias", "margen", "gasto_familiar",
            "otras_cuotas", "dias_atraso_max", "ajuste_asesor")},
           "principal": p.principal, "plazo": p.numberOfRepayments, "tea": p.tea or par["credito"]["tea_base"],
           "mes_desembolso": p.mesPrimeraCuota}
    hist = c["historial_ventas"]
    if not hist or len(hist) < 12:
        rng = np.random.default_rng(c["id"])
        hist = simular_ventas(c["rubro"], c["ventas_medias"], 24, rng, (p.mesPrimeraCuota - 24) % 12).tolist()
    hdf = pd.DataFrame({"cliente_id": cli["cliente_id"], "t": range(-len(hist), 0), "ventas": hist})
    prop = agente.proponer(cli, hdf)
    lid = next(_ids)
    DB["loans"][lid] = {"id": lid, "clientId": c["id"], "status": {"value": "Submitted and pending approval"},
                        "principal": prop["principal_aprobado"], "numberOfRepayments": prop["plazo"],
                        "tea": prop["tea"], "producto": prop["producto"], "propuesta": prop,
                        "cuotas": [f["cuota"] for f in prop["cronograma"]],
                        "aplazamientosRestantes": prop["aplazamientos_disponibles"], "pagos": []}
    return {"loanId": lid, "resourceId": lid, "producto": prop["producto"], "explicacion": prop["explicacion"]}


@app.get(f"{BASE}/loans/{{lid}}")
def ver_prestamo(lid: int, associations: str | None = None):
    l = _loan(lid)
    out = {k: v for k, v in l.items() if k not in ("propuesta", "cuotas")}
    if associations and "repaymentSchedule" in associations:
        tem = tea_a_tem(l["tea"])
        out["repaymentSchedule"] = {"periods": [
            {"period": f["numero"], "totalDueForPeriod": f["cuota"], "principalDue": f["capital"],
             "interestDue": f["interes"], "principalLoanBalanceOutstanding": f["saldo"]}
            for f in desglose_cronograma(l["principal"], tem, l["cuotas"])]}
    return out


@app.post(f"{BASE}/loans/{{lid}}/schedule")
def variaciones(lid: int, command: str, body: dict | None = None):
    """calculateLoanSchedule | addVariations | deleteVariations (solo antes de aprobar, como en Fineract)."""
    l = _loan(lid)
    if command == "calculateLoanSchedule":
        return ver_prestamo(lid, "repaymentSchedule")["repaymentSchedule"]
    if l["status"]["value"] != "Submitted and pending approval":
        raise HTTPException(400, "las variaciones solo se permiten antes de aprobar")
    if command == "deleteVariations":
        l["cuotas"] = [round(cuota_francesa(l["principal"], tea_a_tem(l["tea"]), l["numberOfRepayments"]), 2)] * l["numberOfRepayments"]
        l["producto"] = "fija"
        return {"loanId": lid, "changes": "cronograma restablecido a cuota fija"}
    if command == "addVariations":
        cuotas = (body or {}).get("cuotas")
        if not cuotas or len(cuotas) != l["numberOfRepayments"]:
            raise HTTPException(400, "envíe 'cuotas' con una cuota por periodo")
        tem = tea_a_tem(l["tea"])
        d = (1 + tem) ** -np.arange(1, len(cuotas))
        cuotas[-1] = round((l["principal"] - float(np.dot(d, cuotas[:-1]))) * (1 + tem) ** len(cuotas), 2)  # la última la calcula el sistema
        l["cuotas"] = cuotas
        return {"loanId": lid, "changes": {"cuotas": cuotas}}
    raise HTTPException(400, "command no soportado")


@app.post(f"{BASE}/loans/{{lid}}")
def comando_prestamo(lid: int, command: str):
    l = _loan(lid)
    estados = {"approve": "Approved", "disburse": "Active"}
    if command not in estados:
        raise HTTPException(400, "command debe ser approve o disburse")
    l["status"] = {"value": estados[command]}
    return {"loanId": lid, "status": l["status"]}


@app.post(f"{BASE}/loans/{{lid}}/transactions")
def pagar(lid: int, command: str, body: dict):
    l = _loan(lid)
    if command != "repayment":
        raise HTTPException(400, "command debe ser repayment")
    l["pagos"].append({"monto": float(body.get("transactionAmount", 0)), "fecha": body.get("transactionDate", str(date.today()))})
    return {"loanId": lid, "pagos": len(l["pagos"])}


@app.post(f"{BASE}/loans/{{lid}}/flex")
def aplazar(lid: int, command: str, a: AplazamientoIn):
    """Extensión CuotaFlex: paga solo la cuota mínima en `installment` y redistribuye el resto con interés."""
    l, par = _loan(lid), cargar_parametros()
    if command != "deferInstallment":
        raise HTTPException(400, "command debe ser deferInstallment")
    if l["aplazamientosRestantes"] <= 0:
        raise HTTPException(409, "no quedan aplazamientos o el producto no los incluye")
    if l["status"]["value"] != "Active":
        raise HTTPException(409, "el préstamo debe estar activo")
    k, n, tem = a.installment - 1, l["numberOfRepayments"], tea_a_tem(l["tea"])
    if not 0 <= k < n - 1:
        raise HTTPException(400, "cuota inválida (no se puede aplazar la última)")
    piso = par["flexibilidad"]["cuota_minima_pct"] * cuota_francesa(l["principal"], tem, n)
    diferido = max(l["cuotas"][k] - piso, 0)
    extra = cuota_francesa(diferido, tem, n - k - 1)
    l["cuotas"][k] = round(piso, 2)
    for j in range(k + 1, n):
        l["cuotas"][j] = round(l["cuotas"][j] + extra, 2)
    l["aplazamientosRestantes"] -= 1
    return {"loanId": lid, "cuotaAplazada": a.installment, "nuevaCuota": round(piso, 2),
            "incrementoCuotasSiguientes": round(extra, 2), "aplazamientosRestantes": l["aplazamientosRestantes"]}


@app.get("/motor/parametros")
def parametros():
    return cargar_parametros()
