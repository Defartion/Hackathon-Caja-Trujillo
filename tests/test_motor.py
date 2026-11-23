import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from cuotaflex.agente import AgenteAsesor
from cuotaflex.config import cargar_parametros, cuota_francesa, factores_descuento, tea_a_tem
from cuotaflex.datos import generar_cartera
from cuotaflex.optimizador import optimizar_cronograma
from cuotaflex.politica import evaluar_elegibilidad, validar_cronograma
from cuotaflex.simulacion import comparar_cartera

PAR = cargar_parametros()


def test_optimizador_cierra_vp_y_respeta_politicas():
    tem = tea_a_tem(0.45)
    cap = np.array([300, 250, 200, 600, 700, 650, 500, 300, 250, 400, 600, 650] * 2, float)
    r = optimizar_cronograma(8000, tem, cap, PAR)
    c = r["cuotas"]
    assert abs(factores_descuento(tem, 24) @ c - 8000) < 1
    v = validar_cronograma(8000, tem, c, cap / 0.7, PAR)
    assert v["chequeos"]["respeta_piso"] and v["chequeos"]["respeta_techo"] and v["chequeos"]["meses_reducidos_ok"]
    assert c[4] > c[2]  # paga más en temporada alta


def test_elegibilidad_bloquea_mal_historial_y_sobreendeudamiento():
    base = dict(principal=5000, tea=0.45, plazo=12, ventas_medias=6000, margen=0.3, gasto_familiar=900, otras_cuotas=0)
    assert evaluar_elegibilidad({**base, "dias_atraso_max": 0})["elegible_flex"]
    assert not evaluar_elegibilidad({**base, "dias_atraso_max": 60})["elegible_flex"]
    assert evaluar_elegibilidad({**base, "dias_atraso_max": 0, "otras_cuotas": 700})["sobreendeudado"]


def test_agente_propone_cronograma_valido():
    cli, hist = generar_cartera(10, semilla=1)
    ag = AgenteAsesor(metodo_pronostico="perfil")
    for r in cli.to_dict("records"):
        p = ag.proponer(r, hist)
        assert p["valido"], p["bitacora"][-1]
        assert p["principal_aprobado"] <= r["principal"]
        assert len(p["cronograma"]) == p["plazo"]


def test_simulacion_corre_y_compara():
    det, res = comparar_cartera(n_clientes=20, n_escenarios=30, semilla=3)
    assert set(det.estrategia) == {"fija", "cuotaflex"}
    assert 0 <= res["fija"]["mora30_pct"] <= 100


def test_api_flujo_completo():
    from cuotaflex.api.main import BASE, app
    c = TestClient(app)
    cid = c.post(f"{BASE}/clients", json={"nombre": "Demo", "rubro": "agricultura", "ventas_medias": 7000,
                                          "margen": 0.35, "gasto_familiar": 1000}).json()["clientId"]
    lid = c.post(f"{BASE}/loans", json={"clientId": cid, "principal": 6000, "numberOfRepayments": 12,
                                        "mesPrimeraCuota": 0}).json()["loanId"]
    sch = c.post(f"{BASE}/loans/{lid}/schedule?command=calculateLoanSchedule").json()
    assert len(sch["periods"]) >= 12
    assert c.post(f"{BASE}/loans/{lid}?command=approve").status_code == 200
    assert c.post(f"{BASE}/loans/{lid}/schedule?command=addVariations", json={"cuotas": [1] * 12}).status_code == 400
