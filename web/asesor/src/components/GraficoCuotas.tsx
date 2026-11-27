import { Bar, CartesianGrid, Cell, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtS, fmtS0, mesRelativo } from "../formato";

interface Props {
  fija: number[];
  flex: number[];
  capacidad: number[];
  mesInicio: number;
}

export default function GraficoCuotas({ fija, flex, capacidad, mesInicio }: Props) {
  const n = Math.max(fija.length, flex.length);
  const filas = Array.from({ length: n }, (_, i) => ({
    mes: `${mesRelativo(mesInicio, i)} ${i + 1}`,
    fija: fija[i] ?? null,
    flex: flex[i] ?? null,
    capacidad: capacidad[i] ?? null,
  }));
  const excede = (v: number | null, c: number | null) => v !== null && c !== null && v > c + 0.5;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={filas} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid stroke="#eee" vertical={false} />
        <XAxis dataKey="mes" fontSize={11} interval={n > 18 ? 1 : 0} />
        <YAxis tickFormatter={(v: number) => fmtS0(v)} width={70} fontSize={11} />
        <Tooltip formatter={(v: number, nombre) => [fmtS(v), nombre]} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="fija" name="Cuota fija" fill="#8792A6">
          {filas.map((f, i) => (
            <Cell key={i} fill={excede(f.fija, f.capacidad) ? "#B7791F" : "#8792A6"} />
          ))}
        </Bar>
        <Bar dataKey="flex" name="Cuota Thinku" fill="#0B5CAD">
          {filas.map((f, i) => (
            <Cell key={i} fill={excede(f.flex, f.capacidad) ? "#B7791F" : "#0B5CAD"} />
          ))}
        </Bar>
        <Line dataKey="capacidad" name="Capacidad de pago (mes flojo)" stroke="#C8102E" strokeWidth={2} dot={false} type="stepAfter" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
