import { Bar, CartesianGrid, ComposedChart, LabelList, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Etapa } from "../../contratos";
import { fmtS, fmtS0 } from "../../formato";
import { CajaTooltip, escalaRedonda, ItemBarra, ItemEtapa, ItemLinea, Leyenda, TickMes, tramosDeEtapa } from "./ejes";
import { COLOR, COLOR_ETAPA, ETAPA_ETIQUETA, etiquetaPeriodo, formatoEje } from "./formato";

export interface FilaGraficoPlan {
  i: number;
  periodo: string;
  etapa: Etapa;
  adaptado: number | null;
  fija: number | null;
  /** factor × UN esperada (0 si la UN es ≤ 0). */
  tope: number;
  un: number;
}

interface Props {
  filas: FilaGraficoPlan[];
  factor: number;
  alto?: number;
  ancho?: number;
}

const HOLGURA = 0.5;
const supera = (cuota: number | null, tope: number) => cuota != null && cuota > HOLGURA && cuota > tope + HOLGURA;

/** Marca ▲ sobre las barras que superan el tope de capacidad (estado, no identidad). */
function marcaSupera(filas: FilaGraficoPlan[], clave: "adaptado" | "fija") {
  return function Marca(props: { x?: number | string; y?: number | string; width?: number | string; index?: number }) {
    const f = props.index != null ? filas[props.index] : undefined;
    if (!f || !supera(f[clave], f.tope)) return null;
    const x = Number(props.x) + Number(props.width) / 2;
    const y = Number(props.y) - 4;
    return <path d={`M${x - 4},${y} L${x + 4},${y} L${x},${y - 6} Z`} fill={COLOR.supera} />;
  };
}

/** Cuotas del plan adaptado frente a la cuota fija, sobre el tope factor × UN de cada mes. */
export default function GraficoPlan({ filas, factor, alto = 270, ancho }: Props) {
  const n = filas.length;
  const hayAdaptado = filas.some((f) => f.adaptado != null);
  const maximo = Math.max(...filas.flatMap((f) => [f.adaptado ?? 0, f.fija ?? 0, f.tope]));
  const { dominio, ticks } = escalaRedonda(0, maximo);
  const etiquetas = filas.map((f) => f.periodo);

  const grafico = (
    <ComposedChart data={filas} margin={{ top: 14, right: 16, left: 0, bottom: 4 }} width={ancho} height={alto} barGap={2} barCategoryGap="26%">
      {tramosDeEtapa(filas.map((f) => f.etapa)).map((t) => (
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
        axisLine={{ stroke: "#CDD3DD" }}
        height={34}
      />
      <YAxis domain={dominio} ticks={ticks} tickFormatter={formatoEje(ticks)} width={56} fontSize={11} tickLine={false} axisLine={false} stroke={COLOR.eje} />
      {hayAdaptado && (
        <Bar dataKey="adaptado" name="Plan adaptado" fill={COLOR.adaptado} maxBarSize={18} radius={[3, 3, 0, 0]} isAnimationActive={false}>
          <LabelList dataKey="adaptado" content={marcaSupera(filas, "adaptado")} />
        </Bar>
      )}
      <Bar dataKey="fija" name="Cuota fija" fill={COLOR.fija} maxBarSize={18} radius={[3, 3, 0, 0]} isAnimationActive={false}>
        <LabelList dataKey="fija" content={marcaSupera(filas, "fija")} />
      </Bar>
      {filas.map((f) => (
        <ReferenceLine
          key={`h${f.i}`}
          segment={[{ x: f.i - 0.5, y: f.tope }, { x: f.i + 0.5, y: f.tope }]}
          stroke={COLOR.tope}
          strokeWidth={2}
          ifOverflow="hidden"
        />
      ))}
      {filas.slice(1).map((f, k) =>
        Math.abs(f.tope - filas[k].tope) < 0.01 ? null : (
          <ReferenceLine
            key={`v${f.i}`}
            segment={[{ x: f.i - 0.5, y: filas[k].tope }, { x: f.i - 0.5, y: f.tope }]}
            stroke={COLOR.tope}
            strokeWidth={2}
            ifOverflow="hidden"
          />
        ),
      )}
      <Tooltip
        cursor={{ fill: "rgba(31,35,40,0.06)" }}
        isAnimationActive={false}
        content={({ active, label }) => {
          const f = active && label != null ? filas[Math.round(Number(label))] : undefined;
          if (!f) return null;
          const lineas = [
            ...(hayAdaptado ? [{ color: COLOR.adaptado, k: "Plan adaptado", v: f.adaptado == null ? "—" : fmtS(f.adaptado) }] : []),
            { color: COLOR.fija, k: "Cuota fija", v: f.fija == null ? "—" : fmtS(f.fija) },
            { color: COLOR.tope, linea: true, k: `Tope (${factor.toFixed(2)} × UN)`, v: fmtS0(f.tope) },
            { k: "UN esperada", v: fmtS0(f.un) },
          ];
          return <CajaTooltip titulo={`${etiquetaPeriodo(f.periodo)} · ${ETAPA_ETIQUETA[f.etapa]}`} filas={lineas} />;
        }}
      />
    </ComposedChart>
  );

  return (
    <figure className="pl-grafico" aria-label="Cuotas del plan adaptado frente a la cuota fija, sobre el tope factor por UN esperada">
      <Leyenda>
        {hayAdaptado && <ItemBarra color={COLOR.adaptado} texto="Plan adaptado" />}
        <ItemBarra color={COLOR.fija} texto="Cuota fija" />
        <ItemLinea color={COLOR.tope} texto={`Tope: ${factor.toFixed(2)} × UN esperada`} />
        <span className="pl-leyenda-item">
          <svg width="10" height="8" aria-hidden="true">
            <path d="M1,7 L9,7 L5,1 Z" fill={COLOR.supera} />
          </svg>
          supera el tope
        </span>
        <ItemEtapa etapa="cima" />
        <ItemEtapa etapa="valle" />
      </Leyenda>
      {ancho ? grafico : <ResponsiveContainer width="100%" height={alto}>{grafico}</ResponsiveContainer>}
    </figure>
  );
}
