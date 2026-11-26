import { Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PeriodoCiclo } from "../../contratos";
import { fmtS0 } from "../../formato";
import { CajaTooltip, escalaRedonda, ItemBanda, ItemEtapa, ItemLinea, Leyenda, TickMes, tramosDeEtapa } from "./ejes";
import { COLOR, COLOR_ETAPA, ETAPA_AYUDA, ETAPA_ETIQUETA, etiquetaPeriodo, formatoEje } from "./formato";

interface Props {
  periodos: PeriodoCiclo[];
  alto?: number;
  /** Ancho fijo (vista del comité e impresión). Sin él, se adapta al contenedor. */
  ancho?: number;
}

/** Utilidad neta mensual esperada (p50) con su banda p10–p90 y las etapas sombreadas. */
export default function GraficoCiclo({ periodos, alto = 260, ancho }: Props) {
  const n = periodos.length;
  const filas = periodos.map((p, i) => ({ i, p50: p.un_p50, banda: [p.un_p10, p.un_p90] as [number, number] }));
  const { dominio, ticks } = escalaRedonda(
    Math.min(...periodos.map((p) => p.un_p10)),
    Math.max(...periodos.map((p) => p.un_p90)),
  );
  const etiquetas = periodos.map((p) => p.periodo);

  const grafico = (
    <ComposedChart data={filas} margin={{ top: 8, right: 16, left: 0, bottom: 4 }} width={ancho} height={alto}>
      {tramosDeEtapa(periodos.map((p) => p.etapa)).map((t) => (
        <ReferenceArea key={t.desde} x1={t.desde - 0.5} x2={t.hasta + 0.5} fill={COLOR_ETAPA[t.etapa]} fillOpacity={1} stroke="none" ifOverflow="hidden" />
      ))}
      <CartesianGrid stroke={COLOR.rejilla} vertical={false} />
      <XAxis
        dataKey="i"
        type="number"
        domain={[-0.5, n - 0.5]}
        ticks={filas.map((f) => f.i)}
        interval={0}
        tick={<TickMes periodos={etiquetas} />}
        tickLine={false}
        axisLine={{ stroke: "#C9CED4" }}
        height={34}
      />
      <YAxis domain={dominio} ticks={ticks} tickFormatter={formatoEje(ticks)} width={56} fontSize={11} tickLine={false} axisLine={false} stroke={COLOR.eje} />
      <ReferenceLine y={0} stroke={COLOR.eje} strokeWidth={1} />
      <Area dataKey="banda" stroke="none" fill={COLOR.banda} fillOpacity={0.13} isAnimationActive={false} activeDot={false} />
      <Line
        dataKey="p50"
        stroke={COLOR.un}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
        dot={{ r: 3.5, fill: COLOR.un, stroke: "#fff", strokeWidth: 2 }}
        activeDot={{ r: 5, fill: COLOR.un, stroke: "#fff", strokeWidth: 2 }}
        isAnimationActive={false}
      />
      <Tooltip
        cursor={{ stroke: "#8C959F", strokeWidth: 1 }}
        isAnimationActive={false}
        content={({ active, label }) => {
          const p = active && label != null ? periodos[Math.round(Number(label))] : undefined;
          if (!p) return null;
          return (
            <CajaTooltip
              titulo={`${etiquetaPeriodo(p.periodo)} · ${ETAPA_ETIQUETA[p.etapa]} (${ETAPA_AYUDA[p.etapa]})`}
              filas={[
                { color: COLOR.un, linea: true, k: "UN esperada (p50)", v: fmtS0(p.un_p50) },
                { k: "Rango p10–p90", v: `${fmtS0(p.un_p10)} a ${fmtS0(p.un_p90)}` },
                { k: "Ventas esperadas", v: fmtS0(p.ventas_p50) },
              ]}
            />
          );
        }}
      />
    </ComposedChart>
  );

  return (
    <figure className="pl-grafico" aria-label={`Ciclo estimado: utilidad neta mensual esperada en ${n} meses, con su rango p10–p90`}>
      <Leyenda>
        <ItemLinea color={COLOR.un} texto="UN esperada (p50)" />
        <ItemBanda texto="Rango p10–p90" />
        <ItemEtapa etapa="cima" />
        <ItemEtapa etapa="normal" />
        <ItemEtapa etapa="valle" />
      </Leyenda>
      {ancho ? grafico : <ResponsiveContainer width="100%" height={alto}>{grafico}</ResponsiveContainer>}
    </figure>
  );
}
