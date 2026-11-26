import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtS0, mesRelativo } from "../formato";

interface Props {
  historial: number[];
  pronostico: { p10: number[]; p50: number[]; p90: number[] };
  mesInicio: number;
}

export default function GraficoVentas({ historial, pronostico, mesInicio }: Props) {
  const H = historial.length;
  const filas = [
    ...historial.map((v, i) => ({ t: i - H, historico: v })),
    ...pronostico.p50.map((v, i) => ({ t: i, p50: v, banda: [pronostico.p10[i], pronostico.p90[i]] })),
  ];
  // Une la línea histórica con el pronóstico en el último mes observado
  if (H > 0) Object.assign(filas[H - 1], { p50: historial[H - 1] });

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={filas} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid stroke="#eee" vertical={false} />
        <XAxis dataKey="t" tickFormatter={(t: number) => mesRelativo(mesInicio, t)} interval={2} fontSize={11} />
        <YAxis tickFormatter={(v: number) => fmtS0(v)} width={78} fontSize={11} />
        <Tooltip
          labelFormatter={(t) => `${mesRelativo(mesInicio, Number(t))} ${Number(t) < 0 ? "(histórico)" : "(pronóstico)"}`}
          formatter={(v: number | number[], n) =>
            Array.isArray(v) ? [`${fmtS0(v[0])} – ${fmtS0(v[1])}`, n] : [fmtS0(v), n]
          }
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area dataKey="banda" name="Rango probable" stroke="none" fill="#0B5CAD" fillOpacity={0.14} />
        <Line dataKey="historico" name="Ventas históricas" stroke="#172033" dot={false} strokeWidth={2} />
        <Line dataKey="p50" name="Pronóstico (p50)" stroke="#0B5CAD" strokeDasharray="5 4" dot={false} strokeWidth={2} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
