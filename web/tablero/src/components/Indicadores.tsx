import type { Resumen } from '../api';
import { deltaPct, deltaSoles, pct1, soles } from '../formato';
import type { DeltaInfo } from '../formato';

export function Delta({ d, clase = 'delta' }: { d: DeltaInfo; clase?: string }) {
  return (
    <span className={`${clase} ${d.tono}`}>
      {d.flecha && <span aria-hidden="true">{d.flecha} </span>}
      {d.texto}
    </span>
  );
}

interface TarjetaProps {
  etiqueta: string;
  fija: string;
  flex: string;
  delta: DeltaInfo;
  sub?: string;
}

function Tarjeta({ etiqueta, fija, flex, delta, sub }: TarjetaProps) {
  return (
    <div className="kpi">
      <div className="kpi-etiqueta">{etiqueta}</div>
      <div className="kpi-valores">
        <span className="kpi-par kpi-fija">
          <span className="muestra fija" aria-hidden="true" />
          <span className="nombre">Fija</span>
          <span>{fija}</span>
        </span>
        <span className="kpi-flecha" aria-hidden="true">
          →
        </span>
        <span className="kpi-par kpi-flex">
          <span className="muestra flex" aria-hidden="true" />
          <span className="nombre">Thinku</span>
          <span>{flex}</span>
        </span>
      </div>
      <Delta d={delta} />
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

export default function Indicadores({ resumen }: { resumen: Resumen }) {
  const f = resumen.fija;
  const c = resumen.cuotaflex;
  return (
    <div className="kpis">
      <Tarjeta
        etiqueta="Créditos con atraso > 30 días"
        fija={pct1(f.mora30_pct)}
        flex={pct1(c.mora30_pct)}
        delta={deltaPct(f.mora30_pct, c.mora30_pct, true)}
      />
      <Tarjeta
        etiqueta="Incumplimiento (3 cuotas impagas)"
        fija={pct1(f.default_pct)}
        flex={pct1(c.default_pct)}
        delta={deltaPct(f.default_pct, c.default_pct, true)}
      />
      <Tarjeta
        etiqueta="Margen neto / cartera"
        fija={pct1(f.margen_sobre_cartera_pct)}
        flex={pct1(c.margen_sobre_cartera_pct)}
        delta={deltaPct(f.margen_sobre_cartera_pct, c.margen_sobre_cartera_pct, false)}
        sub={`Margen neto: ${soles(f.margen_neto_total)} → ${soles(c.margen_neto_total)}`}
      />
      <Tarjeta
        etiqueta="Cartera colocada"
        fija={soles(f.cartera)}
        flex={soles(c.cartera)}
        delta={deltaSoles(f.cartera, c.cartera, true)}
      />
    </div>
  );
}
