"""API mock compatible con Apache Fineract + endpoints del motor CuotaFlex.

Imita la forma de los recursos de Fineract (/fineract-provider/api/v1) para que el cambio a
una instancia real sea directo. Almacenamiento en memoria (solo demo, datos sintéticos).
Ejecutar:  uvicorn cuotaflex.api.main:app --reload
"""
from __future__ import annotations

import importlib
import os
import pkgutil
import threading
from datetime import date
from itertools import count

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..agente import AgenteAsesor
from ..config import cargar_parametros, cuota_francesa, desglose_cronograma, tea_a_tem
from ..datos import RUBROS, simular_ventas
from .. import persistencia

BASE = "/fineract-provider/api/v1"
app = FastAPI(title="CuotaFlex · API compatible con Fineract", version="0.1.0")
DB: dict[str, dict] = {"clients": {}, "loans": {}}
_ids = count(1)
_candado_db = threading.Lock()
_ESCRITURAS = {"POST", "PUT", "PATCH", "DELETE"}


def siguiente_id() -> int:
    """Próximo ID sin consumirlo (para la instantánea)."""
    global _ids
    n = next(_ids)
    _ids = count(n)
    return n


def guardar_instantanea() -> None:
    if persistencia.activa():
        with _candado_db:
            try:
                persistencia.guardar(DB, siguiente_id())
            except Exception as e:  # p. ej. Upstash caído: la operación ya se hizo en memoria, no se rompe la respuesta
                print(f"[persistencia] no se pudo guardar la instantánea: {e}")


CARGA_FALLIDA = False  # True si al arrancar no se pudo leer la instantánea (p. ej. Upstash caído)


def cargar_instantanea() -> None:
    global _ids, CARGA_FALLIDA
    if persistencia.activa():
        with _candado_db:
            try:
                _ids = count(persistencia.cargar(DB))
                CARGA_FALLIDA = False
            except Exception as e:  # se arranca con lo que haya; desactualizada() recarga cuando vuelva
                print(f"[persistencia] no se pudo cargar la instantánea: {e}")
                CARGA_FALLIDA = True


@app.middleware("http")
async def _persistir(request: Request, call_next):
    """Fase 3: tras cada escritura exitosa se guarda la instantánea en SQLite y, si se desembolsó un
    préstamo, se programa su espejo en Fineract (solo con CORE_ESPEJO=1)."""
    respuesta = await call_next(request)
    if request.method in _ESCRITURAS and respuesta.status_code < 300:
        guardar_instantanea()
        if request.query_params.get("command") == "disburse":
            from .routers import espejo_automatico

            espejo_automatico.programar(request.url.path)
    return respuesta


@app.middleware("http")
async def _autorizar(request: Request, call_next):
    """Fase 3: con CUOTAFLEX_AUTH=1 cada prefijo exige un rol (ver routers/auth.py).
    Fase 4: antes de nada se recarga la instantánea si otra instancia la cambió en Upstash, y las llaves
    personales (código del préstamo, usuario + PIN) se revisan en cuotaflex/llaves.py."""
    from .routers import auth

    if persistencia.desactualizada():
        cargar_instantanea()
    if not auth.activa() or request.method == "OPTIONS":
        return await call_next(request)
    ruta = request.url.path
    prefijo = request.scope.get("root_path", "")  # p. ej. "/api" cuando la API se monta en server.py
    if prefijo and ruta.startswith(prefijo):
        ruta = ruta[len(prefijo):] or "/"
    roles = auth.permiso_requerido(ruta, request.method)
    if roles == set():
        return await call_next(request)
    encabezado = request.headers.get("authorization", "")
    datos = auth.datos_token(encabezado[7:]) if encabezado.lower().startswith("bearer ") else None
    if datos is None:
        return JSONResponse({"detail": "Inicia sesión con tu llave o el PIN de tu rol."}, status_code=401)
    rol = datos["rol"]
    if roles is not None and rol not in roles:
        return JSONResponse({"detail": f"El rol {rol} no tiene acceso a esta sección."}, status_code=403)
    from .. import llaves

    problema = llaves.revisar(datos, ruta, request.method)
    if problema:
        return JSONResponse({"detail": problema[1]}, status_code=problema[0])
    return await call_next(request)
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
    productoPreferido: str | None = Field(None, description="fija | aplazamiento | estacional (si es elegible)")


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
           "mes_desembolso": p.mesPrimeraCuota, "producto_preferido": p.productoPreferido}
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
    from .. import llaves

    llaves.preparar_prestamo(DB["loans"][lid])  # fase 4: llave del cliente (código de 6 dígitos)
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
    if command == "disburse":  # las fechas de vencimiento del cronograma se cuentan desde aquí
        l.setdefault("fechaDesembolso", date.today().isoformat())
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


@app.get("/motor/prestamos")
def listar_prestamos():
    """Préstamos registrados en el core, del más reciente al más antiguo (para el panel del asesor).

    Va bajo /motor y no bajo /fineract-provider para que el rol cliente no vea la lista completa."""
    filas = []
    for l in sorted(DB["loans"].values(), key=lambda x: -x["id"]):
        c = DB["clients"].get(l["clientId"], {})
        cuotas = l.get("cuotas") or [0]
        filas.append({"id": l["id"], "clientId": l["clientId"], "cliente": c.get("nombre", f"Cliente {l['clientId']}"),
                      "rubro": c.get("rubro"), "estado": l["status"]["value"], "principal": l["principal"],
                      "plazo": l["numberOfRepayments"], "producto": l.get("producto"),
                      "cuota_min": float(min(cuotas)), "cuota_max": float(max(cuotas)),
                      "aplazamientos_restantes": l.get("aplazamientosRestantes", 0)})
    return filas


@app.get("/motor/parametros")
def parametros():
    return cargar_parametros()


def _registrar_routers() -> None:
    """Incluye todo `router` definido en cuotaflex.api.routers.* (un archivo por lote)."""
    from . import routers

    for mod in pkgutil.iter_modules(routers.__path__):
        m = importlib.import_module(f"{routers.__name__}.{mod.name}")
        if hasattr(m, "router"):
            app.include_router(m.router)


_registrar_routers()

# CORS al final = middleware más externo: también las respuestas 401/403 llevan sus encabezados.
# Frontends locales: asesor 5173, cliente 5174, tablero 5175; los desplegados van en CUOTAFLEX_ORIGENES.
app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(localhost|127\.0\.0\.1):51\d\d",
                   allow_origins=[o.strip() for o in os.getenv("CUOTAFLEX_ORIGENES", "").split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"])
cargar_instantanea()
