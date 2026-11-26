// Formatos y reglas de lectura del ciclo y del plan (fase 4). Sin dependencias de React.
import type { Etapa, PeriodoPlan, PlanRespuesta, TipoPeriodo } from "../../contratos";
import { RATIO_SIN_CAPACIDAD } from "../../contratos";
import { fmtS0, MESES } from "../../formato";

export const MESES_LARGOS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre",
];

export const ETAPA_ETIQUETA: Record<Etapa, string> = { cima: "Cima", normal: "Normal", valle: "Valle" };
export const ETAPA_AYUDA: Record<Etapa, string> = {
  cima: "temporada alta",
  normal: "meses regulares",
  valle: "temporada baja",
};

export const TIPO_ETIQUETA: Record<TipoPeriodo, string> = {
  amortizacion: "Amortiza",
  solo_interes: "Solo interés",
  gracia: "Gracia",
};

/** Colores de las etapas: cima fría, valle cálida y normal neutra (divergente con punto medio gris). */
export const COLOR_ETAPA: Record<Etapa, string> = { cima: "#E1ECF8", normal: "#FFFFFF", valle: "#FBE6D4" };
export const COLOR = {
  adaptado: "#0B5CAD",
  fija: "#8C959F",
  tope: "#C8102E",
  un: "#0B5CAD",
  banda: "#0B5CAD",
  supera: "#8E0B20",
  eje: "#57606A",
  rejilla: "#E5E7EB",
};

/** "2027-01" → { mes: 0, anio: 2027 }. */
export function partesPeriodo(periodo: string): { mes: number; anio: number } {
  const [a, m] = periodo.split("-").map(Number);
  return { mes: (m || 1) - 1, anio: a || 0 };
}

/** "2027-01" → "ene 2027". */
export const etiquetaPeriodo = (periodo: string) => {
  const { mes, anio } = partesPeriodo(periodo);
  return `${MESES[mes]} ${anio}`;
};

/** "2027-01-15" → "15/01/2027" (sin pasar por Date, para no correr la fecha por la zona horaria). */
export function fmtFecha(iso: string): string {
  const [a, m, d] = iso.slice(0, 10).split("-");
  return d && m && a ? `${d}/${m}/${a}` : iso;
}

export function fmtFechaHora(iso: string): string {
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return iso;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(f.getDate())}/${p(f.getMonth() + 1)}/${f.getFullYear()} ${p(f.getHours())}:${p(f.getMinutes())}`;
}

/** Fecha local de hoy en AAAA-MM-DD. */
export function hoyIso(): string {
  const f = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${f.getFullYear()}-${p(f.getMonth() + 1)}-${p(f.getDate())}`;
}

/** Primer día del mes siguiente, en AAAA-MM-DD. */
export function primeroDelMesSiguiente(): string {
  const f = new Date();
  const a = f.getMonth() === 11 ? f.getFullYear() + 1 : f.getFullYear();
  const m = (f.getMonth() + 1) % 12;
  return `${a}-${String(m + 1).padStart(2, "0")}-01`;
}

/** "UN ≤ 0" con espacios que no se parten al final de una línea. */
export const SIN_UN = "UN\u00a0≤\u00a00";

export const fmtTasa = (v: number, dec = 2) => `${(v * 100).toFixed(dec)}%`;
export const fmtNum = (v: number, dec = 2) => v.toFixed(dec);

/** Ratio Cuota/UN legible: 99 (o más) es el marcador del motor para "cuota con UN ≤ 0". */
export function fmtRatio(r: number | null | undefined): string {
  if (r == null) return "—";
  if (r >= RATIO_SIN_CAPACIDAD) return SIN_UN;
  return r.toFixed(2);
}

/**
 * Formato del eje Y en soles con un solo estilo por eje: completo si el eje no llega a 10 000
 * (0 / 2,000 / 4,000) y compacto si llega (0 / 5K / 10K).
 */
export function formatoEje(ticks: number[]): (v: number) => string {
  const compacto = ticks.some((t) => Math.abs(t) >= 10000);
  const entero = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  return (v: number) => {
    const a = Math.abs(v);
    const signo = v < 0 ? "−" : "";
    if (a === 0) return "0";
    if (!compacto) return `${signo}${entero.format(a)}`;
    return `${signo}${(a / 1000).toFixed(a % 1000 === 0 ? 0 : 1)}K`;
  };
}

export type NivelSemaforo = "ok" | "limite" | "supera" | "neutro";

export interface Semaforo {
  nivel: NivelSemaforo;
  icono: string;
  texto: string;
  titulo: string;
}

/**
 * Semáforo de Cuota/UN de un periodo:
 * - neutro: sin cuota (gracia total);
 * - supera: cuota > factor × UN, o cuota con UN ≤ 0;
 * - límite: dentro del factor pero con menos de 10% de holgura;
 * - ok: holgado.
 */
export function semaforo(cuota: number, un: number, ratio: number | null, factor: number): Semaforo {
  if (cuota <= 0.005) return { nivel: "neutro", icono: "·", texto: "sin cuota", titulo: "Sin cuota en este periodo" };
  if (un <= 0) return { nivel: "supera", icono: "✕", texto: SIN_UN, titulo: "Cuota en un mes sin utilidad neta" };
  const r = ratio ?? cuota / un;
  if (r > factor + 0.0005)
    return { nivel: "supera", icono: "✕", texto: r.toFixed(2), titulo: `Supera el factor ${factor.toFixed(2)}` };
  if (r > factor * 0.9)
    return { nivel: "limite", icono: "!", texto: r.toFixed(2), titulo: `Al límite del factor ${factor.toFixed(2)}` };
  return { nivel: "ok", icono: "✓", texto: r.toFixed(2), titulo: `Dentro del factor ${factor.toFixed(2)}` };
}

/** Factor del producto que se usó en la solicitud. */
export const factorDe = (sol: { producto: { factor: number } }) => sol.producto.factor;

/** Seguros de un periodo (desgravamen + multirriesgo generados). */
export const segurosDe = (p: PeriodoPlan) => p.seguro_desgravamen + p.seguro_multirriesgo;
export const pendientesDe = (p: PeriodoPlan) => p.pendiente_seguros + p.pendiente_interes;

export interface ResumenEtapa {
  etapa: Etapa;
  meses: number;
  /** Máximo Cuota/UN en meses con cuota y UN > 0 (null si no hubo). */
  ratioMax: number | null;
  /** Meses con cuota sobre el factor (incluye cuotas con UN ≤ 0). */
  sobreFactor: number;
  /** Meses con cuota > 0 y UN ≤ 0. */
  sinCapacidad: number;
  cuotaMedia: number;
}

/** Cuota/UN agrupado por etapa (cima, normal y valle) para un plan. */
export function resumenPorEtapa(periodos: PeriodoPlan[], factor: number): ResumenEtapa[] {
  const etapas: Etapa[] = ["cima", "normal", "valle"];
  return etapas.map((etapa) => {
    const ps = periodos.filter((p) => p.etapa === etapa);
    let ratioMax: number | null = null;
    let sobreFactor = 0;
    let sinCapacidad = 0;
    for (const p of ps) {
      if (p.cuota <= 0.005) continue;
      if (p.un_esperada <= 0) {
        sobreFactor += 1;
        sinCapacidad += 1;
        continue;
      }
      const r = p.ratio_cuota_un ?? p.cuota / p.un_esperada;
      ratioMax = ratioMax == null ? r : Math.max(ratioMax, r);
      if (r > factor + 0.0005) sobreFactor += 1;
    }
    const cuotaMedia = ps.length ? ps.reduce((s, p) => s + p.cuota, 0) / ps.length : 0;
    return { etapa, meses: ps.length, ratioMax, sobreFactor, sinCapacidad, cuotaMedia };
  });
}

/** Meses con cuota > 0 y UN ≤ 0 en un plan. */
export const mesesSinCapacidad = (periodos: PeriodoPlan[]) =>
  periodos.filter((p) => p.cuota > 0.005 && p.un_esperada <= 0).length;

/** Texto corto del estado del plan para encabezados. */
export function estadoPlan(r: PlanRespuesta, factor: number): { ok: boolean; texto: string } {
  if (!r.factible || !r.plan) return { ok: false, texto: "Sin plan factible con Cuota/UN ≤ factor" };
  const rm = r.plan.resumen.ratio_max;
  return {
    ok: r.plan.resumen.etapas_sobre_factor === 0,
    texto: `Plan factible · Cuota/UN máx. ${fmtRatio(rm)} ≤ factor ${factor.toFixed(2)}`,
  };
}

/** Descripción de un ajuste sugerido por el motor. */
export function textoAjuste(tipo: string, valor: number | null): string {
  if (tipo === "reducir_monto") return valor != null ? `Reducir el monto a ${fmtS0(valor)}` : "Reducir el monto";
  if (tipo === "ampliar_plazo") return valor != null ? `Ampliar el plazo a ${valor} meses` : "Ampliar el plazo";
  if (tipo === "bajar_factor") return valor != null ? `Usar un factor de ${valor.toFixed(2)}` : "Bajar el factor";
  return valor != null ? `${tipo.replace(/_/g, " ")}: ${valor}` : tipo.replace(/_/g, " ");
}
