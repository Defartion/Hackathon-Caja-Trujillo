import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Resumen } from '../api';
import { COLOR_EJE, COLOR_FIJA, COLOR_FLEX, COLOR_GRID, COLOR_TEXTO_EJE, RUBROS } from '../colores';
import { decimal1, pct1 } from '../formato';
import TarjetaGrafico from './TarjetaGrafico';

const TICK = { fontSize: 12, fill: COLOR_TEXTO_EJE };

interface Fila {
  id: string;
  nombre: string;
  corto: string;
  fija: number;
  flex: number;
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Fila }[] }) {
  if (!active || !payload?.length) return null;
  const f = payload[0].payload;
  const d = f.flex - f.fija;
  return (
    <div className="tt">
      <div className="tt-titulo">{f.nombre}</div>
      <div className="tt-fila">
        <span className="muestra fija" /> Fija: {pct1(f.fija)}
      </div>
      <div className="tt-fila">
        <span className="muestra flex" /> CuotaFlex: {pct1(f.flex)}
      </div>
      <div>
        Diferencia: {d > 0 ? '+' : d < 0 ? '−' : ''}
        {decimal1(Math.abs(d))} pp
      </div>
    </div>
  );
}

/** Marcas limpias del eje Y (0, 10, 20, …) que cubren el máximo. */
function marcas(max: number): number[] {
  const paso = max <= 10 ? 2 : max <= 25 ? 5 : max <= 50 ? 10 : 20;
  const techo = Math.max(paso, Math.ceil(max / paso) * paso);
  const out: number[] = [];
  for (let v = 0; v <= techo; v += paso) out.push(v);
  return out;
}

export default function GraficoRubros({ resumen }: { resumen: Resumen }) {
  const datos: Fila[] = RUBROS.filter((r) => resumen.por_rubro[r.id]).map((r) => ({
    id: r.id,
    nombre: r.nombre,
    corto: r.corto,
    fija: resumen.por_rubro[r.id].mora30_fija,
    flex: resumen.por_rubro[r.id].mora30_cuotaflex,
  }));
  const ticks = marcas(Math.max(0, ...datos.flatMap((f) => [f.fija, f.flex])));

  const grafico = (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={datos} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} barGap={2}>
        <CartesianGrid vertical={false} stroke={COLOR_GRID} strokeDasharray="0" />
        <XAxis dataKey="corto" tick={TICK} axisLine={{ stroke: COLOR_EJE }} tickLine={false} interval={0} />
        <YAxis
          tick={TICK}
          axisLine={false}
          tickLine={false}
          width={40}
          domain={[0, ticks[ticks.length - 1]]}
          ticks={ticks}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip content={<Tip />} cursor={{ fill: '#F0F1F3' }} />
        <Legend verticalAlign="top" height={28} iconType="square" iconSize={10} />
        <Bar dataKey="fija" name="Fija" fill={COLOR_FIJA} maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        <Bar dataKey="flex" name="CuotaFlex" fill={COLOR_FLEX} maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );

  const tabla = (
    <table className="tabla">
      <thead>
        <tr>
          <th>Rubro</th>
          <th className="num">Fija</th>
          <th className="num">CuotaFlex</th>
          <th className="num">Diferencia</th>
        </tr>
      </thead>
      <tbody>
        {datos.map((f) => {
          const d = f.flex - f.fija;
          return (
            <tr key={f.id}>
              <td>{f.nombre}</td>
              <td className="num">{pct1(f.fija)}</td>
              <td className="num">{pct1(f.flex)}</td>
              <td className="num">
                {d > 0 ? '+' : d < 0 ? '−' : ''}
                {decimal1(Math.abs(d))} pp
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  return (
    <TarjetaGrafico
      titulo="Atraso > 30 días por rubro"
      subtitulo="Porcentaje de créditos con más de 30 días de atraso, según el rubro del cliente"
      grafico={grafico}
      tabla={tabla}
    />
  );
}
