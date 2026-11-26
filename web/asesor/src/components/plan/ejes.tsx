// Piezas comunes de los gráficos del ciclo y del plan: eje de meses, escala "redonda" y leyenda.
import type { ReactNode } from "react";
import type { Etapa } from "../../contratos";
import { MESES } from "../../formato";
import { COLOR, COLOR_ETAPA, ETAPA_ETIQUETA, partesPeriodo } from "./formato";
import { colorTema } from "../../apariencia";

/** Tick de dos líneas: mes y, en enero o en el primer mes, el año. */
export function TickMes(props: { x?: number; y?: number; payload?: { value: number }; periodos: string[] }) {
  const { x = 0, y = 0, payload, periodos } = props;
  const i = Math.round(payload?.value ?? -1);
  const periodo = periodos[i];
  if (!periodo) return null;
  const { mes, anio } = partesPeriodo(periodo);
  const paso = periodos.length > 26 ? 2 : 1;
  const conAnio = i === 0 || mes === 0;
  if (!conAnio && i % paso !== 0) return null;
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fontSize={11} fill={COLOR.eje} dy={12}>
        {MESES[mes]}
      </text>
      {conAnio && (
        <text textAnchor="middle" fontSize={10} fill="#5A6478" dy={25}>
          {anio}
        </text>
      )}
    </g>
  );
}

/** Tramos consecutivos de una misma etapa (cima o valle), para sombrearlos sin costuras. */
export function tramosDeEtapa(etapas: Etapa[]): { desde: number; hasta: number; etapa: Etapa }[] {
  const tramos: { desde: number; hasta: number; etapa: Etapa }[] = [];
  etapas.forEach((etapa, i) => {
    const ultimo = tramos[tramos.length - 1];
    if (ultimo && ultimo.etapa === etapa && ultimo.hasta === i - 1) ultimo.hasta = i;
    else tramos.push({ desde: i, hasta: i, etapa });
  });
  return tramos.filter((t) => t.etapa !== "normal");
}

/** Escala del eje Y con pasos redondos (incluye siempre el 0). */
export function escalaRedonda(min: number, max: number, maxTicks = 6): { dominio: [number, number]; ticks: number[] } {
  const lo = Math.min(0, min);
  const hi = Math.max(0, max);
  const rango = hi - lo || 1;
  const pasos = [50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000, 100000];
  const paso = pasos.find((p) => rango / p <= maxTicks - 1) ?? pasos[pasos.length - 1];
  const a = Math.floor(lo / paso) * paso;
  const b = Math.ceil((hi * 1.04) / paso) * paso;
  const ticks: number[] = [];
  for (let v = a; v <= b + 1e-9; v += paso) ticks.push(v);
  return { dominio: [a, b], ticks };
}

export function Leyenda({ children }: { children: ReactNode }) {
  return <div className="pl-leyenda">{children}</div>;
}

export function ItemEtapa({ etapa }: { etapa: Etapa }) {
  return (
    <span className="pl-leyenda-item">
      <span className="pl-muestra pl-muestra-etapa" style={{ background: colorTema(COLOR_ETAPA[etapa]) }} />
      {ETAPA_ETIQUETA[etapa]}
    </span>
  );
}

export function ItemBarra({ color, texto }: { color: string; texto: string }) {
  return (
    <span className="pl-leyenda-item">
      <span className="pl-muestra" style={{ background: colorTema(color) }} />
      {texto}
    </span>
  );
}

export function ItemLinea({ color, texto }: { color: string; texto: string }) {
  return (
    <span className="pl-leyenda-item">
      <span className="pl-muestra-linea" style={{ background: colorTema(color) }} />
      {texto}
    </span>
  );
}

export function ItemBanda({ texto }: { texto: string }) {
  return (
    <span className="pl-leyenda-item">
      <span className="pl-muestra pl-muestra-banda" />
      {texto}
    </span>
  );
}

/** Contenedor común del tooltip (valores primero, etiquetas después). */
export function CajaTooltip({ titulo, filas }: { titulo: string; filas: { color?: string; linea?: boolean; k: string; v: string }[] }) {
  return (
    <div className="pl-tooltip">
      <div className="pl-tooltip-titulo">{titulo}</div>
      {filas.map((f) => (
        <div key={f.k} className="pl-tooltip-fila">
          {f.color ? (
            <span className={f.linea ? "pl-muestra-linea" : "pl-muestra"} style={{ background: colorTema(f.color) }} />
          ) : (
            <span className="pl-muestra-vacia" />
          )}
          <strong>{f.v}</strong>
          <span>{f.k}</span>
        </div>
      ))}
    </div>
  );
}
