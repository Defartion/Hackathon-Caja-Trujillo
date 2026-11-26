import type { Plan } from "../../contratos";
import { fmtS, fmtS0, MESES } from "../../formato";
import { ETAPA_ETIQUETA, fmtFecha, partesPeriodo, pendientesDe, segurosDe, semaforo, SIN_UN, TIPO_ETIQUETA } from "./formato";

interface Props {
  plan: Plan;
  factor: number;
  /** compacta: menos columnas y letra menor para la vista del comité impresa. */
  variante?: "completa" | "compacta";
  titulo?: string;
}

export function PildoraSemaforo({ cuota, un, ratio, factor }: { cuota: number; un: number; ratio: number | null; factor: number }) {
  const s = semaforo(cuota, un, ratio, factor);
  return (
    <span className={`pl-semaforo ${s.nivel}`} title={s.titulo}>
      <span aria-hidden="true">{s.icono}</span> {s.texto}
    </span>
  );
}

export function LeyendaSemaforo({ factor }: { factor: number }) {
  return (
    <div className="pl-leyenda pl-leyenda-semaforo">
      <span className="pl-semaforo ok"><span aria-hidden="true">✓</span> holgado</span>
      <span className="pl-semaforo limite"><span aria-hidden="true">!</span> al límite (más de {(factor * 0.9).toFixed(2)})</span>
      <span className="pl-semaforo supera"><span aria-hidden="true">✕</span> supera el factor {factor.toFixed(2)} o {SIN_UN}</span>
      <span className="pl-semaforo neutro"><span aria-hidden="true">·</span> sin cuota</span>
    </div>
  );
}

const mesCorto = (fecha: string) => {
  const { mes, anio } = partesPeriodo(fecha.slice(0, 7));
  return `${MESES[mes]} ${String(anio).slice(2)}`;
};

/** Cronograma por periodo: cuota, seguros, interés, capital, pendientes, saldo y Cuota/UN con semáforo. */
export default function TablaPlan({ plan, factor, variante = "completa", titulo }: Props) {
  const p = plan.periodos;
  const total = (f: (x: (typeof p)[number]) => number) => p.reduce((s, x) => s + f(x), 0);
  const compacta = variante === "compacta";
  return (
    <div className={`pl-tabla-envoltura ${compacta ? "compacta" : ""}`}>
      <table className={`pl-tabla ${compacta ? "compacta" : ""}`} aria-label={titulo ?? "Cronograma por periodo"}>
        <thead>
          <tr>
            <th className="num">N°</th>
            <th>{compacta ? "Mes" : "Vence"}</th>
            {!compacta && <th className="num">Días</th>}
            <th>Etapa</th>
            <th className="num">Cuota</th>
            <th className="num">Seguros</th>
            <th className="num">Interés</th>
            <th className="num">Capital</th>
            <th className="num" title="Seguros e interés que no alcanzó a cubrir la cuota: no generan interés">Pendiente</th>
            {!compacta && <th className="num">Saldo capital</th>}
            <th className="num">{compacta ? "Saldo deuda" : "Saldo deuda"}</th>
            <th className="num">UN esperada</th>
            <th>Cuota/UN</th>
            <th>Tipo</th>
          </tr>
        </thead>
        <tbody>
          {p.map((x) => (
            <tr key={x.n} className={`etapa-${x.etapa}`}>
              <td className="num">{x.n}</td>
              <td>{compacta ? mesCorto(x.fecha_vencimiento) : fmtFecha(x.fecha_vencimiento)}</td>
              {!compacta && <td className="num">{x.dias}</td>}
              <td>
                <span className={`pl-etapa ${x.etapa}`}>{ETAPA_ETIQUETA[x.etapa]}</span>
              </td>
              <td
                className="num fuerte"
                title={`Paga seguros ${fmtS(x.pago_seguros)} · interés ${fmtS(x.pago_interes)} · capital ${fmtS(x.capital)}`}
              >
                {fmtS(x.cuota)}
              </td>
              <td className="num">{fmtS(segurosDe(x))}</td>
              <td className="num">{fmtS(x.interes)}</td>
              <td className="num">{fmtS(x.capital)}</td>
              <td className="num">{pendientesDe(x) > 0.005 ? fmtS(pendientesDe(x)) : "—"}</td>
              {!compacta && <td className="num">{fmtS(x.saldo_capital)}</td>}
              <td className="num">{fmtS(x.saldo_deuda)}</td>
              <td className={`num ${x.un_esperada <= 0 ? "negativo" : ""}`}>{fmtS0(x.un_esperada)}</td>
              <td>
                <PildoraSemaforo cuota={x.cuota} un={x.un_esperada} ratio={x.ratio_cuota_un} factor={factor} />
              </td>
              <td>{x.tipo === "amortizacion" ? <span className="pl-tipo">{TIPO_ETIQUETA[x.tipo]}</span> : <span className={`pl-tipo ${x.tipo}`}>{TIPO_ETIQUETA[x.tipo]}</span>}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={compacta ? 3 : 4}>Total</td>
            <td className="num fuerte">{fmtS(total((x) => x.cuota))}</td>
            <td className="num">{fmtS(total(segurosDe))}</td>
            <td className="num">{fmtS(total((x) => x.interes))}</td>
            <td className="num">{fmtS(total((x) => x.capital))}</td>
            <td colSpan={compacta ? 5 : 6} />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
