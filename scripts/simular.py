"""Corre la comparación cuota fija vs. CuotaFlex y guarda resultados en resultados/.

Uso: python scripts/simular.py [--clientes 600] [--escenarios 200] [--pronostico perfil|mixto]
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cuotaflex.simulacion import comparar_cartera  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--clientes", type=int, default=None)
ap.add_argument("--escenarios", type=int, default=None)
ap.add_argument("--pronostico", default="perfil")
a = ap.parse_args()
out = RAIZ / "resultados"
out.mkdir(exist_ok=True)
resumen = {}
for nombre, rp in (("completo", True), ("solo_cronograma", False)):
    det, res = comparar_cartera(a.clientes, a.escenarios, metodo_pronostico=a.pronostico, replanificar=rp)
    det.to_csv(out / f"detalle_{nombre}.csv", index=False)
    resumen[nombre] = res
(out / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
for k, r in resumen.items():
    print(k, "| fija:", r["fija"], "\n   cuotaflex:", r["cuotaflex"], "\n   delta:", r["delta"])
