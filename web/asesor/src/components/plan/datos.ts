// Alinea el ciclo y los dos planes por mes para los gráficos y las tablas.
import type { CicloRespuesta, PlanRespuesta } from "../../contratos";
import type { FilaGraficoPlan } from "./GraficoPlan";

export function filasGraficoPlan(ciclo: CicloRespuesta, r: PlanRespuesta, factor: number): FilaGraficoPlan[] {
  const adaptado = r.plan?.periodos ?? [];
  const fija = r.plan_cuota_fija?.periodos ?? [];
  const n = Math.max(ciclo.periodos.length, adaptado.length, fija.length);
  return Array.from({ length: n }, (_, i) => {
    const pc = ciclo.periodos[i];
    const pa = adaptado[i];
    const pf = fija[i];
    const un = pa?.un_esperada ?? pf?.un_esperada ?? pc?.un_p50 ?? 0;
    return {
      i,
      periodo: pc?.periodo ?? (pa ?? pf)?.fecha_vencimiento.slice(0, 7) ?? "",
      etapa: pc?.etapa ?? (pa ?? pf)?.etapa ?? "normal",
      // Si el plan adaptado termina antes del horizonte, los meses siguientes no tienen cuota.
      adaptado: r.plan ? (pa ? pa.cuota : 0) : null,
      fija: r.plan_cuota_fija ? (pf ? pf.cuota : 0) : null,
      tope: factor * Math.max(un, 0),
      un,
    };
  });
}

/** Cuotas con pago (> 0) de un plan. */
export const cuotasConPago = (periodos: { cuota: number }[]) => periodos.filter((p) => p.cuota > 0.005).length;

export const cuotaMaxima = (periodos: { cuota: number }[]) => periodos.reduce((m, p) => Math.max(m, p.cuota), 0);
