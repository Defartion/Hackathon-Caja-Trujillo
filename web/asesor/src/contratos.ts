// Tipos del contrato de la fase 4 (docs/fases/fase-4/CONTRATOS.md).
// §1 POST /ciclo/estimar (lote B) · §2 POST /plan/proponer (lote A). Los JSON de ejemplo
// viven en tests/fixtures/contratos/ y su copia en src/mocks/.

export type Etapa = "cima" | "normal" | "valle";

export interface Zona {
  departamento: string;
  provincia: string;
  distrito: string | null;
}

export interface Evidencia {
  tipo: "yape" | "boleta" | "boletas";
  meses: number;
  monto_promedio_mensual: number;
}

/** Lo que levanta el Asesor de Negocios en campo. Los meses van de 1 (enero) a 12 (diciembre). */
export interface Captura {
  ventas_mes_alto: number;
  ventas_mes_normal: number;
  ventas_mes_bajo: number;
  meses_altos: number[];
  meses_bajos: number[];
  costo_ventas_pct: number;
  gastos_operativos: number;
  gastos_tributarios: number;
  carga_familiar: number;
  otras_deudas_cuota: number;
  evidencias: Evidencia[];
}

export interface CicloSolicitud {
  cliente_id: string;
  sector: string;
  actividad: string;
  zona: Zona;
  /** Fecha prevista de desembolso (AAAA-MM-DD). */
  fecha_inicio: string;
  /** Horizonte en meses: igual al plazo del crédito. */
  meses: number;
  captura: Captura;
}

export interface PeriodoCiclo {
  /** "AAAA-MM", desde el mes siguiente al desembolso. */
  periodo: string;
  etapa: Etapa;
  ventas_p50: number;
  /** UN = utilidad neta mensual (ya descontados costos, gastos, otras deudas y carga familiar). */
  un_p10: number;
  un_p50: number;
  un_p90: number;
}

export interface Escenario {
  id: string;
  nombre: string;
  un: number[];
}

export interface Fuente {
  nombre: string;
  uso: string;
  url?: string | null;
}

export interface CicloRespuesta {
  cliente_id: string;
  sector: string;
  actividad: string;
  zona: Zona;
  fecha_inicio: string;
  meses: number;
  periodos: PeriodoCiclo[];
  escenarios: Escenario[];
  supuestos: string[];
  fuentes: Fuente[];
  calidad: { metodo: string; cobertura_p10_p90_backtest: number };
  _ilustrativo?: boolean;
}

export interface ActividadCatalogo {
  sector: string;
  actividad: string;
  zonas: Zona[];
}

/** GET /ciclo/catalogo */
export interface CatalogoCiclo {
  actividades: ActividadCatalogo[];
}

export interface Producto {
  nombre: string;
  /** Tope de Cuota/UN en cada etapa (siempre < 1). */
  factor: number;
  tope_tea?: number | null;
  max_meses_gracia: number;
  permite_solo_interes: boolean;
}

export interface Seguros {
  desgravamen: { activo: boolean; tasa_mensual: number };
  multirriesgo: { activo: boolean; tasa_mensual: number; valor_asegurable: number };
}

export interface PlanSolicitud {
  monto: number;
  tea: number;
  fecha_desembolso: string;
  plazo_meses: number;
  producto: Producto;
  seguros: Seguros;
  /** La respuesta completa de POST /ciclo/estimar. */
  ciclo: CicloRespuesta;
  comparar_cuota_fija: boolean;
}

export type TipoPeriodo = "amortizacion" | "solo_interes" | "gracia";

export interface PeriodoPlan {
  n: number;
  fecha_vencimiento: string;
  dias: number;
  etapa: Etapa;
  cuota: number;
  seguro_desgravamen: number;
  seguro_multirriesgo: number;
  interes: number;
  pago_seguros: number;
  pago_interes: number;
  capital: number;
  pendiente_seguros: number;
  pendiente_interes: number;
  saldo_capital: number;
  saldo_deuda: number;
  un_esperada: number;
  /** null si la UN es ≤ 0. */
  ratio_cuota_un: number | null;
  tipo: TipoPeriodo;
}

export interface ResumenPlan {
  cuotas: number;
  total_pagado: number;
  interes_total: number;
  seguros_total: number;
  ted: number;
  tcea: number;
  ratio_max: number | null;
  etapas_sobre_factor: number;
  cumple_factor: boolean;
  meses_gracia: number;
  meses_solo_interes: number;
}

export interface Plan {
  periodos: PeriodoPlan[];
  resumen: ResumenPlan;
}

export interface EstresPlan {
  etapas_sobre_factor: number;
  /** El lote A usa 99 cuando hay una cuota con UN ≤ 0 en el escenario. */
  ratio_max: number | null;
  monto_sobre_capacidad: number;
}

export interface EstresEscenario {
  escenario: string;
  nombre: string;
  /** null cuando no hay plan adaptado factible. */
  adaptado: EstresPlan | null;
  fija: EstresPlan | null;
}

export type TipoAjuste = "reducir_monto" | "ampliar_plazo" | "bajar_factor";

/** "con su valor": el lote A usa `monto_maximo` y `plazo_minimo`; se acepta también `valor`. */
export interface AjusteSugerido {
  tipo: TipoAjuste | string;
  valor?: number;
  monto_maximo?: number;
  plazo_minimo?: number;
  factor?: number;
  [clave: string]: unknown;
}

export interface PasoBitacoraPlan {
  paso: string;
  [clave: string]: unknown;
}

export interface PlanRespuesta {
  factible: boolean;
  /** null cuando no es factible. */
  plan: Plan | null;
  plan_cuota_fija: Plan | null;
  estres: EstresEscenario[];
  ajustes_sugeridos: AjusteSugerido[];
  supuestos: string[];
  bitacora?: PasoBitacoraPlan[];
  _ilustrativo?: boolean;
}

/** Ratio que usa el motor cuando hay cuota con UN ≤ 0 (no hay capacidad de pago). */
export const RATIO_SIN_CAPACIDAD = 99;

/** El valor numérico de un ajuste sugerido, venga en `valor` o en la clave propia del tipo. */
export function valorAjuste(a: AjusteSugerido): number | null {
  const candidatos = [a.valor, a.monto_maximo, a.plazo_minimo, a.factor, a.factor_maximo, a.monto, a.plazo];
  const v = candidatos.find((x) => typeof x === "number" && Number.isFinite(x));
  return typeof v === "number" ? v : null;
}
