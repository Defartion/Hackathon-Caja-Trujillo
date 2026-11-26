import { Riesgo } from "../api";
import { fmtPct, fmtS0 } from "../formato";

interface Props {
  fija: Riesgo;
  flex: Riesgo;
  n: number;
}

function Kpi({ k, a, b, fmt, menosEsMejor }: { k: string; a: number; b: number; fmt: (v: number) => string; menosEsMejor: boolean }) {
  const d = b - a;
  const mejora = menosEsMejor ? d < 0 : d > 0;
  const igual = Math.abs(d) < 1e-9;
  return (
    <div className="kpi tarjeta">
      <div className="k">{k}</div>
      <div className="v">
        <span style={{ color: "var(--cf-gris-600)" }}>{fmt(a)}</span> → <span style={{ color: "var(--cf-azul)" }}>{fmt(b)}</span>
      </div>
      <div className={`delta ${igual ? "" : mejora ? "mejor" : "peor"}`}>
        {igual ? "sin cambio" : `${d > 0 ? "+" : ""}${fmt(d)} ${mejora ? "▲ mejora" : "▼ empeora"}`}
      </div>
    </div>
  );
}

export default function Comparativa({ fija, flex, n }: Props) {
  return (
    <div className="tarjeta">
      <h2>Riesgo simulado: cuota fija → esta propuesta</h2>
      <div className="rejilla r3">
        <Kpi k="Atraso > 30 días" a={fija.mora30} b={flex.mora30} fmt={(v) => fmtPct(v)} menosEsMejor />
        <Kpi k="Incumplimiento (3 cuotas impagas)" a={fija.default} b={flex.default} fmt={(v) => fmtPct(v)} menosEsMejor />
        <Kpi k="Ganancia esperada para la Caja (VPN)" a={fija.vpn_medio} b={flex.vpn_medio} fmt={fmtS0} menosEsMejor={false} />
      </div>
      <div style={{ color: "var(--cf-gris-600)", fontSize: 12, marginTop: 10 }}>
        {n} escenarios de ventas y El Niño, con las mismas trayectorias para ambas estrategias. La ganancia descuenta fondeo, costo operativo y
        pérdidas. En el 5% de escenarios más malos: {fmtS0(fija.vpn_p5)} → {fmtS0(flex.vpn_p5)}.
      </div>
    </div>
  );
}
