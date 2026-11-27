import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { HistogramaVpn } from '../api';
import { COLOR_EJE, COLOR_FIJA, COLOR_FLEX, COLOR_GRID, COLOR_TEXTO_EJE } from '../colores';
import { entero, solesEje, solesExacto } from '../formato';
import TarjetaGrafico from './TarjetaGrafico';

const TICK = { fontSize: 12, fill: COLOR_TEXTO_EJE };

interface Punto {
  x: number;
  x1: number;
  fija: number;
  flex: number;
  ultimo: boolean;
}

function ticksNice(lo: number, hi: number): number[] {
  const rango = hi - lo;
  const crudo = rango / 6;
  const pot = Math.pow(10, Math.floor(Math.log10(crudo)));
  const f = crudo / pot;
  const paso = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pot;
  const out: number[] = [];
  for (let t = Math.ceil(lo / paso) * paso; t <= hi; t += paso) out.push(Math.round(t));
  return out;
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Punto }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (p.ultimo) return null;
  return (
    <div className="tt">
      <div className="tt-titulo">
        {solesExacto(p.x)} a {solesExacto(p.x1)}
      </div>
      <div className="tt-fila">
        <span className="muestra fija" /> Fija: {entero(p.fija)} créditos
      </div>
      <div className="tt-fila">
        <span className="muestra flex" /> Thinku: {entero(p.flex)} créditos
      </div>
    </div>
  );
}

export default function GraficoHistograma({ h }: { h: HistogramaVpn }) {
  const n = h.fija.length;
  const puntos: Punto[] = [];
  for (let i = 0; i < n; i++) {
    puntos.push({ x: h.bordes[i], x1: h.bordes[i + 1], fija: h.fija[i], flex: h.cuotaflex[i], ultimo: false });
  }
  const lo = h.bordes[0];
  const hi = h.bordes[n];
  puntos.push({ x: hi, x1: hi, fija: h.fija[n - 1], flex: h.cuotaflex[n - 1], ultimo: true });
  const ceroDentro = lo < 0 && hi > 0;

  const grafico = (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={puntos} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={COLOR_GRID} strokeDasharray="0" />
        <XAxis
          type="number"
          dataKey="x"
          domain={[lo, hi]}
          ticks={ticksNice(lo, hi)}
          tick={TICK}
          axisLine={{ stroke: COLOR_EJE }}
          tickLine={false}
          tickFormatter={solesEje}
        />
        <YAxis tick={TICK} axisLine={false} tickLine={false} width={34} allowDecimals={false} />
        <Tooltip content={<Tip />} />
        <Legend verticalAlign="top" height={28} iconType="square" iconSize={10} />
        {ceroDentro && (
          <ReferenceLine
            x={0}
            stroke={COLOR_TEXTO_EJE}
            strokeWidth={1}
            label={{ value: 'VPN = 0', position: 'insideTopRight', fontSize: 12, fill: COLOR_TEXTO_EJE }}
          />
        )}
        <Area
          type="stepAfter"
          dataKey="fija"
          name="Fija"
          stroke={COLOR_FIJA}
          strokeWidth={2}
          fill={COLOR_FIJA}
          fillOpacity={0}
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />
        <Area
          type="stepAfter"
          dataKey="flex"
          name="Thinku"
          stroke={COLOR_FLEX}
          strokeWidth={2}
          fill={COLOR_FLEX}
          fillOpacity={0.12}
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  const tabla = (
    <table className="tabla">
      <thead>
        <tr>
          <th>Ganancia por crédito (VPN)</th>
          <th className="num">Fija</th>
          <th className="num">Thinku</th>
        </tr>
      </thead>
      <tbody>
        {puntos
          .filter((p) => !p.ultimo)
          .map((p) => (
            <tr key={p.x}>
              <td>
                {solesExacto(p.x)} a {solesExacto(p.x1)}
              </td>
              <td className="num">{entero(p.fija)}</td>
              <td className="num">{entero(p.flex)}</td>
            </tr>
          ))}
      </tbody>
    </table>
  );

  return (
    <TarjetaGrafico
      titulo="Ganancia por crédito (VPN)"
      subtitulo="Cuántos créditos ganan o pierden dinero para la Caja; a la izquierda de VPN = 0, el crédito pierde"
      grafico={grafico}
      tabla={tabla}
    />
  );
}
