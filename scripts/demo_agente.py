"""Muestra la propuesta del agente para algunos clientes sintéticos."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cuotaflex.agente import AgenteAsesor  # noqa: E402
from cuotaflex.datos import generar_cartera  # noqa: E402

clientes, hist = generar_cartera(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
ag = AgenteAsesor()
for c in clientes.to_dict("records"):
    p = ag.proponer(c, hist)
    print(f"\n== {c['cliente_id']} · {c['rubro']} · solicita S/ {c['principal']:,.0f} a {c['plazo']} meses")
    print(p["explicacion"])
    print("cuotas:", [f["cuota"] for f in p["cronograma"]])
    print("bitácora:", json.dumps(p["bitacora"], default=str, ensure_ascii=False)[:400])
