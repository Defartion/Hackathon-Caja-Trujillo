import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Symbols,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PuntoDispersion } from '../api';
import { COLOR_EJE, COLOR_GRID, COLOR_TEXTO_EJE, NOMBRE_PRODUCTO, RUBROS, infoRubro } from '../colores';
import type { InfoRubro } from '../colores';
import { decimal1, entero } from '../formato';
import TarjetaGrafico from './TarjetaGrafico';

const TICK = { fontSize: 12, fill: COLOR_TEXTO_EJE };
const UMBRAL = 0.005;

interface Pt {
  x: number;
  y: number;
  cliente_id: string;
  rubro: string;
  producto: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function Forma(props: any, r: InfoRubro, opacidad: number) {
  const { cx, cy } = props;
  if (typeof cx !== 'number' || typeof cy !== 'number') return <g />;
  return (
    <g opacity={opacidad}>
      <circle cx={cx} cy={cy} r={10} fill="transparent" />
      <Symbols cx={cx} cy={cy} type={r.simbolo} size={56} fill={r.color} stroke="#fff" strokeWidth={1.5} />
    </g>
  );
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Pt }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (!p || p.cliente_id === undefined) return null;
  return (
    <div className="tt">
      <div className="tt-titulo">{p.cliente_id}</div>
      <div>Rubro: {infoRubro(p.rubro).nombre}</div>
      <div>Producto: {NOMBRE_PRODUCTO[p.producto] ?? p.producto}</div>
      <div className="tt-fila">
        <span className="muestra fija" /> Mora fija: {decimal1(p.x)}%
      </div>
      <div className="tt-fila">
        <span className="muestra flex" /> Mora Thinku: {decimal1(p.y)}%
      </div>
    </div>
  );
}

function Simbolo({ r }: { r: InfoRubro }) {
  return (
    <svg className="cf-graf" width="16" height="16" aria-hidden="true">
      <Symbols cx={8} cy={8} type={r.simbolo} size={56} fill={r.color} stroke="#fff" strokeWidth={1.5} />
    </svg>
  );
}

function clasificar(d: PuntoDispersion): 'mejora' | 'igual' | 'empeora' {
  if (d.mora_flex < d.mora_fija - UMBRAL) return 'mejora';
  if (d.mora_flex > d.mora_fija + UMBRAL) return 'empeora';
  return 'igual';
}

export default function GraficoDispersion({ datos }: { datos: PuntoDispersion[] }) {
  const [aislado, setAislado] = useState<string | null>(null);

  const { puntos, M, resumen, porRubro } = useMemo(() => {
    const puntos: Pt[] = datos.map((d) => ({
      x: d.mora_fija * 100,
      y: d.mora_flex * 100,
      cliente_id: d.cliente_id,
      rubro: d.rubro,
      producto: d.producto,
    }));
    let max = 0;
    for (const p of puntos) max = Math.max(max, p.x, p.y);
    const M = Math.max(10, Math.ceil(max / 10) * 10);
    const cnt = { mejora: 0, igual: 0, empeora: 0 };
    const porRubro = RUBROS.map((r) => {
      const ds = datos.filter((d) => d.rubro === r.id);
      const c = { mejora: 0, igual: 0, empeora: 0 };
      let sf = 0;
      let sx = 0;
      for (const d of ds) {
        c[clasificar(d)]++;
        sf += d.mora_fija;
        sx += d.mora_flex;
      }
      return { r, n: ds.length, c, mf: ds.length ? (sf / ds.length) * 100 : 0, mx: ds.length ? (sx / ds.length) * 100 : 0 };
    });
    for (const d of datos) cnt[clasificar(d)]++;
    const n = datos.length || 1;
    const pc = (v: number) => Math.round((v / n) * 100);
    return {
      puntos,
      M,
      porRubro,
      resumen: `▼ ${pc(cnt.mejora)}% mejora · ${pc(cnt.igual)}% igual · ▲ ${pc(cnt.empeora)}% empeora`,
    };
  }, [datos]);

  const rubrosPresentes = RUBROS.filter((r) => puntos.some((p) => p.rubro === r.id));

  const grafico = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="leyenda" role="group" aria-label="Rubros (clic para aislar)">
        {rubrosPresentes.map((r) => (
          <button
            key={r.id}
            type="button"
            className="leyenda-item"
            aria-pressed={aislado === r.id}
            onClick={() => setAislado((a) => (a === r.id ? null : r.id))}
          >
            <Simbolo r={r} />
            {r.corto}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 14, left: 0, bottom: 18 }}>
            <CartesianGrid stroke={COLOR_GRID} strokeDasharray="0" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, M]}
              tick={TICK}
              axisLine={{ stroke: COLOR_EJE }}
              tickLine={false}
              tickFormatter={(v: number) => `${v}%`}
              label={{ value: 'Mora con cuota fija', position: 'insideBottom', offset: -10, fontSize: 12, fill: COLOR_TEXTO_EJE }}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, M]}
              tick={TICK}
              axisLine={false}
              tickLine={false}
              width={62}
              tickFormatter={(v: number) => `${v}%`}
              label={{ value: 'Mora con Thinku', angle: -90, position: 'insideLeft', offset: 2, fontSize: 12, fill: COLOR_TEXTO_EJE, style: { textAnchor: 'middle' } }}
            />
            <Tooltip content={<Tip />} cursor={false} />
            <ReferenceLine
              segment={[
                { x: 0, y: 0 },
                { x: M, y: M },
              ]}
              stroke={COLOR_TEXTO_EJE}
              strokeWidth={1}
              strokeDasharray="0"
              ifOverflow="visible"
              label={{ value: 'y = x', position: 'insideTopLeft', fontSize: 12, fill: COLOR_TEXTO_EJE }}
            />
            {rubrosPresentes.map((r) => {
              const op = aislado === null || aislado === r.id ? 1 : 0.12;
              return (
                <Scatter
                  key={r.id}
                  name={r.nombre}
                  data={puntos.filter((p) => p.rubro === r.id)}
                  isAnimationActive={false}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  shape={(p: any) => Forma(p, r, op)}
                />
              );
            })}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const tabla = (
    <table className="tabla">
      <thead>
        <tr>
          <th>Rubro</th>
          <th className="num">Clientes</th>
          <th className="num">% mejora</th>
          <th className="num">% igual</th>
          <th className="num">% empeora</th>
          <th className="num">Mora media fija</th>
          <th className="num">Mora media Thinku</th>
        </tr>
      </thead>
      <tbody>
        {porRubro
          .filter((x) => x.n > 0)
          .map((x) => (
            <tr key={x.r.id}>
              <td>{x.r.nombre}</td>
              <td className="num">{entero(x.n)}</td>
              <td className="num">{decimal1((x.c.mejora / x.n) * 100)}%</td>
              <td className="num">{decimal1((x.c.igual / x.n) * 100)}%</td>
              <td className="num">{decimal1((x.c.empeora / x.n) * 100)}%</td>
              <td className="num">{decimal1(x.mf)}%</td>
              <td className="num">{decimal1(x.mx)}%</td>
            </tr>
          ))}
      </tbody>
    </table>
  );

  return (
    <TarjetaGrafico
      titulo="Mora por cliente: fija vs. Thinku"
      subtitulo="Cada punto es un cliente; por debajo de la diagonal, Thinku mejora su mora"
      extra={resumen}
      grafico={grafico}
      tabla={tabla}
    />
  );
}
