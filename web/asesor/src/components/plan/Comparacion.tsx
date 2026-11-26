// Resumen comparado (adaptado frente a fija), indicadores, Cuota/UN por etapa y estrés.
import type { EstresEscenario, EstresPlan, Plan, PlanRespuesta } from "../../contratos";
import { RATIO_SIN_CAPACIDAD } from "../../contratos";
import { fmtS, fmtS0 } from "../../formato";
import { cuotaMaxima, cuotasConPago } from "./datos";
import { ETAPA_AYUDA, ETAPA_ETIQUETA, fmtRatio, fmtTasa, mesesSinCapacidad, resumenPorEtapa, SIN_UN } from "./formato";

type Fila = {
  k: string;
  a: number | null;
  f: number | null;
  fmt: (v: number) => string;
  /** true: menos es mejor; false: más es mejor; null: no se juzga. */
  menos: boolean | null;
  prueba?: string;
};

function Delta({ a, f, fmt, menos }: Pick<Fila, "a" | "f" | "fmt" | "menos">) {
  if (a == null || f == null) return <span className="pl-gris">—</span>;
  const d = a - f;
  if (Math.abs(d) < 1e-6) return <span className="pl-gris">igual</span>;
  const mejor = menos == null ? null : menos ? d < 0 : d > 0;
  return (
    <span className={mejor == null ? "" : mejor ? "mejor" : "peor"}>
      {d > 0 ? "+" : "−"}
      {fmt(Math.abs(d))}
    </span>
  );
}

/** Tabla de costos y capacidad: plan adaptado, cuota fija y diferencia. */
export function ResumenComparado({ r }: { r: PlanRespuesta }) {
  const a = r.plan;
  const f = r.plan_cuota_fija;
  const ra = a?.resumen;
  const rf = f?.resumen;
  const entero = (v: number) => String(Math.round(v));
  const filas: Fila[] = [
    { k: "Cuotas con pago", a: a ? cuotasConPago(a.periodos) : null, f: f ? cuotasConPago(f.periodos) : null, fmt: entero, menos: null },
    { k: "Cuota más alta", a: a ? cuotaMaxima(a.periodos) : null, f: f ? cuotaMaxima(f.periodos) : null, fmt: fmtS0, menos: null },
    { k: "Total pagado", a: ra?.total_pagado ?? null, f: rf?.total_pagado ?? null, fmt: fmtS, menos: true, prueba: "total" },
    { k: "Interés", a: ra?.interes_total ?? null, f: rf?.interes_total ?? null, fmt: fmtS, menos: true, prueba: "interes" },
    { k: "Seguros", a: ra?.seguros_total ?? null, f: rf?.seguros_total ?? null, fmt: fmtS, menos: true },
    { k: "TCEA", a: ra?.tcea ?? null, f: rf?.tcea ?? null, fmt: (v) => fmtTasa(v), menos: true, prueba: "tcea" },
    { k: "Meses de gracia", a: ra?.meses_gracia ?? null, f: rf?.meses_gracia ?? null, fmt: entero, menos: null },
    { k: "Meses solo interés", a: ra?.meses_solo_interes ?? null, f: rf?.meses_solo_interes ?? null, fmt: entero, menos: null },
    { k: "Etapas sobre el factor", a: ra?.etapas_sobre_factor ?? null, f: rf?.etapas_sobre_factor ?? null, fmt: entero, menos: true, prueba: "etapas" },
  ];
  return (
    <div className="pl-tabla-envoltura">
    <table className="pl-tabla pl-resumen" aria-label="Resumen comparado">
      <thead>
        <tr>
          <th />
          <th className="num">Plan adaptado</th>
          <th className="num">Cuota fija</th>
          <th className="num">Diferencia</th>
        </tr>
      </thead>
      <tbody>
        {filas.map((x) => (
          <tr key={x.k}>
            <th scope="row">{x.k}</th>
            <td className="num fuerte" data-testid={x.prueba ? `resumen-${x.prueba}-adaptado` : undefined}>
              {x.a == null ? "—" : x.fmt(x.a)}
            </td>
            <td className="num" data-testid={x.prueba ? `resumen-${x.prueba}-fija` : undefined}>
              {x.f == null ? "—" : x.fmt(x.f)}
            </td>
            <td className="num">
              <Delta a={x.a} f={x.f} fmt={x.fmt} menos={x.menos} />
            </td>
          </tr>
        ))}
        <tr>
          <th scope="row">Cuota/UN máximo</th>
          <td className="num fuerte">{fmtRatio(ra?.ratio_max)}</td>
          <td className="num">
            {fmtRatio(rf?.ratio_max)}
            {f && mesesSinCapacidad(f.periodos) > 0 && (
              <span className="pl-nota-celda"> y {mesesSinCapacidad(f.periodos)} con {SIN_UN}</span>
            )}
          </td>
          <td />
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={4}>
            TED base 360: {ra ? fmtTasa(ra.ted, 4) : rf ? fmtTasa(rf.ted, 4) : "—"} diaria, aplicada por los días exactos de cada
            periodo. La TCEA iguala el monto desembolsado con las cuotas en sus fechas.
          </td>
        </tr>
      </tfoot>
    </table>
    </div>
  );
}

/** Indicadores principales: capacidad, etapas sobre el factor, TCEA e interés. */
export function Indicadores({ r, factor }: { r: PlanRespuesta; factor: number }) {
  const ra = r.plan?.resumen;
  const rf = r.plan_cuota_fija?.resumen;
  const sinCapFija = r.plan_cuota_fija ? mesesSinCapacidad(r.plan_cuota_fija.periodos) : 0;
  const cumple = !!ra && ra.etapas_sobre_factor === 0;
  return (
    <div className="pl-indicadores">
      <div className={`pl-indicador ${ra ? (cumple ? "bien" : "mal") : "mal"}`}>
        <div className="k">Cuota/UN máximo · plan adaptado</div>
        <div className="v" data-testid="ratio-max-adaptado">
          {ra ? fmtRatio(ra.ratio_max) : "sin plan"}
        </div>
        <div className="d">
          {ra ? (
            <>
              <span aria-hidden="true">{cumple ? "✓" : "✕"}</span> {cumple ? "dentro del" : "supera el"} factor {factor.toFixed(2)}
            </>
          ) : (
            "no hay plan factible"
          )}
        </div>
        <div className="c">
          Cuota fija: {fmtRatio(rf?.ratio_max)}
          {sinCapFija > 0 ? ` y ${sinCapFija} ${sinCapFija === 1 ? "cuota" : "cuotas"} con ${SIN_UN}` : ""}
        </div>
      </div>
      <div className={`pl-indicador ${ra ? (cumple ? "bien" : "mal") : "mal"}`}>
        <div className="k">Etapas sobre el factor</div>
        <div className="v" data-testid="etapas-sobre-factor-adaptado">
          {ra ? ra.etapas_sobre_factor : "—"}
        </div>
        <div className="d">plan adaptado</div>
        <div className="c">
          Cuota fija: <strong data-testid="etapas-sobre-factor-fija">{rf ? rf.etapas_sobre_factor : "—"}</strong>
        </div>
      </div>
      <div className="pl-indicador">
        <div className="k">TCEA</div>
        <div className="v">{ra ? fmtTasa(ra.tcea) : "—"}</div>
        <div className="d">plan adaptado</div>
        <div className="c">Cuota fija: {rf ? fmtTasa(rf.tcea) : "—"}</div>
      </div>
      <div className="pl-indicador">
        <div className="k">Interés y seguros</div>
        <div className="v">{ra ? fmtS0(ra.interes_total + ra.seguros_total) : "—"}</div>
        <div className="d">plan adaptado</div>
        <div className="c">Cuota fija: {rf ? fmtS0(rf.interes_total + rf.seguros_total) : "—"}</div>
      </div>
    </div>
  );
}

/** Cuota/UN agrupado por etapa: máximo y meses sobre el factor, adaptado frente a fija. */
export function CuotaUnPorEtapa({ adaptado, fija, factor }: { adaptado: Plan | null; fija: Plan | null; factor: number }) {
  const ra = adaptado ? resumenPorEtapa(adaptado.periodos, factor) : null;
  const rf = fija ? resumenPorEtapa(fija.periodos, factor) : null;
  const etapas = (ra ?? rf ?? []).filter((e, i) => e.meses > 0 || (rf?.[i]?.meses ?? 0) > 0);
  const celda = (e: ReturnType<typeof resumenPorEtapa>[number] | undefined) => {
    if (!e) return <td className="num" colSpan={3}>—</td>;
    const sobre = e.sobreFactor > 0;
    return (
      <>
        <td className="num">{fmtS0(e.cuotaMedia)}</td>
        <td className="num">{e.ratioMax == null ? (e.sinCapacidad ? SIN_UN : "—") : e.ratioMax.toFixed(2)}</td>
        <td className="num">
          <span className={`pl-semaforo ${sobre ? "supera" : "ok"}`}>
            <span aria-hidden="true">{sobre ? "✕" : "✓"}</span> {e.sobreFactor}
          </span>
        </td>
      </>
    );
  };
  return (
    <div className="pl-tabla-envoltura">
    <table className="pl-tabla pl-por-etapa" aria-label="Cuota/UN por etapa">
      <thead>
        <tr>
          <th rowSpan={2}>Etapa</th>
          <th rowSpan={2} className="num">Meses</th>
          <th colSpan={3} className="centro">Plan adaptado</th>
          <th colSpan={3} className="centro">Cuota fija</th>
        </tr>
        <tr>
          <th className="num">Cuota prom.</th>
          <th className="num">Cuota/UN máx.</th>
          <th className="num">Sobre factor</th>
          <th className="num">Cuota prom.</th>
          <th className="num">Cuota/UN máx.</th>
          <th className="num">Sobre factor</th>
        </tr>
      </thead>
      <tbody>
        {etapas.map((e) => {
          const ea = ra?.find((x) => x.etapa === e.etapa);
          const ef = rf?.find((x) => x.etapa === e.etapa);
          return (
            <tr key={e.etapa}>
              <th scope="row" title={ETAPA_AYUDA[e.etapa]}>
                <span className={`pl-etapa ${e.etapa}`}>{ETAPA_ETIQUETA[e.etapa]}</span>
              </th>
              <td className="num">{(ef ?? ea)?.meses ?? 0}</td>
              {adaptado ? celda(ea) : <td className="num pl-gris" colSpan={3}>sin plan factible</td>}
              {celda(ef)}
            </tr>
          );
        })}
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={8}>
            Factor del producto: {factor.toFixed(2)}. Una cuota en un mes con {SIN_UN} cuenta como sobre el factor: en esos meses
            la cuota debe ser 0 (gracia).
          </td>
        </tr>
      </tfoot>
    </table>
    </div>
  );
}

const fmtExceso = (v: number) => (v > 0.005 ? fmtS0(v) : "S/ 0");

function CeldasEstres({ e, otro, prueba }: { e: EstresPlan | null; otro: EstresPlan | null; prueba?: string }) {
  if (!e) return <td colSpan={3} className="num pl-gris">sin plan factible</td>;
  const mejor = (a: number, b: number | undefined) => (b == null ? "" : a < b - 1e-9 ? "mejor" : a > b + 1e-9 ? "peor" : "");
  return (
    <>
      <td className={`num ${mejor(e.etapas_sobre_factor, otro?.etapas_sobre_factor)}`} data-testid={prueba}>
        {e.etapas_sobre_factor}
      </td>
      <td className="num">{e.ratio_max != null && e.ratio_max >= RATIO_SIN_CAPACIDAD ? SIN_UN : fmtRatio(e.ratio_max)}</td>
      <td className={`num ${mejor(e.monto_sobre_capacidad, otro?.monto_sobre_capacidad)}`}>{fmtExceso(e.monto_sobre_capacidad)}</td>
    </>
  );
}

/** Estrés: cómo le iría a cada plan si el ciclo sale como en cada escenario adverso. */
export function TablaEstres({ estres }: { estres: EstresEscenario[] }) {
  return (
    <div className="pl-tabla-envoltura">
    <table className="pl-tabla pl-estres" aria-label="Escenarios adversos">
      <thead>
        <tr>
          <th rowSpan={2}>Escenario</th>
          <th colSpan={3} className="centro">Plan adaptado</th>
          <th colSpan={3} className="centro">Cuota fija</th>
        </tr>
        <tr>
          <th className="num">Etapas sobre factor</th>
          <th className="num">Cuota/UN máx.</th>
          <th className="num">S/ sobre capacidad</th>
          <th className="num">Etapas sobre factor</th>
          <th className="num">Cuota/UN máx.</th>
          <th className="num">S/ sobre capacidad</th>
        </tr>
      </thead>
      <tbody>
        {estres.map((x) => (
          <tr key={x.escenario}>
            <th scope="row">{x.nombre}</th>
            <CeldasEstres e={x.adaptado} otro={x.fija} prueba={`estres-${x.escenario}-adaptado`} />
            <CeldasEstres e={x.fija} otro={x.adaptado} prueba={`estres-${x.escenario}-fija`} />
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={7}>
            Cada plan se evalúa contra la UN del escenario. «Sobre el factor» cuenta los meses en que la cuota supera factor × UN
            (o hay cuota con {SIN_UN}); «S/ sobre la capacidad» suma ese exceso en todo el plazo.
          </td>
        </tr>
      </tfoot>
    </table>
    </div>
  );
}
