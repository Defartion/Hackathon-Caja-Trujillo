// Estado de los formularios del asistente, validación en lenguaje de campo y armado de las
// solicitudes del contrato (CicloSolicitud y PlanSolicitud).
import type { CicloRespuesta, CicloSolicitud, Evidencia, PlanSolicitud, Producto, Zona } from "../../contratos";
import { fmtS0 } from "../../formato";
import { primeroDelMesSiguiente } from "./formato";

export type EstadoMes = "normal" | "alto" | "bajo";

export interface EvidenciaForm {
  tipo: "yape" | "boletas";
  meses: string;
  monto: string;
}

export interface FormNegocio {
  cliente_id: string;
  /** Referencia para el comité (no se envía a la API). */
  nombre: string;
  sector: string;
  actividad: string;
  zona: Zona | null;
  fecha_inicio: string;
  meses: string;
  ventas_mes_alto: string;
  ventas_mes_normal: string;
  ventas_mes_bajo: string;
  /** Un estado por mes calendario: índice 0 = enero. */
  meses_estado: EstadoMes[];
  /** En porcentaje (0–99), como lo dice el cliente. */
  costo_ventas_pct: string;
  gastos_operativos: string;
  gastos_tributarios: string;
  carga_familiar: string;
  otras_deudas_cuota: string;
  evidencias: EvidenciaForm[];
}

export type IdProducto = "microempresa" | "inclusion";

export interface FormCredito {
  monto: string;
  tea_pct: string;
  plazo: string;
  producto: IdProducto;
  factor: string;
  desgravamen: boolean;
  /** % mensual sobre el saldo de capital. */
  desgravamen_pct: string;
  multirriesgo: boolean;
  /** % mensual sobre el valor asegurable. */
  multirriesgo_pct: string;
  valor_asegurable: string;
}

/** Tope referencial de TEA (BCRP) del contrato de ejemplo; la Caja confirma el vigente. */
export const TOPE_TEA_REFERENCIAL = 0.83;
export const PLAZO_MIN = 3;
export const PLAZO_MAX = 36;

export const PRODUCTOS: Record<IdProducto, Producto> = {
  microempresa: {
    nombre: "Microempresa",
    factor: 0.85,
    tope_tea: TOPE_TEA_REFERENCIAL,
    max_meses_gracia: 4,
    permite_solo_interes: true,
  },
  inclusion: {
    nombre: "Inclusión financiera",
    factor: 0.65,
    tope_tea: TOPE_TEA_REFERENCIAL,
    max_meses_gracia: 4,
    permite_solo_interes: true,
  },
};

export function negocioVacio(): FormNegocio {
  return {
    cliente_id: "",
    nombre: "",
    sector: "",
    actividad: "",
    zona: null,
    fecha_inicio: primeroDelMesSiguiente(),
    meses: "12",
    ventas_mes_alto: "",
    ventas_mes_normal: "",
    ventas_mes_bajo: "",
    meses_estado: Array<EstadoMes>(12).fill("normal"),
    costo_ventas_pct: "",
    gastos_operativos: "",
    gastos_tributarios: "",
    carga_familiar: "",
    otras_deudas_cuota: "0",
    evidencias: [],
  };
}

export function creditoPorDefecto(plazo = "12"): FormCredito {
  return {
    monto: "",
    tea_pct: "45",
    plazo,
    producto: "microempresa",
    factor: "0.85",
    desgravamen: true,
    desgravamen_pct: "0.077",
    multirriesgo: false,
    multirriesgo_pct: "0.03",
    valor_asegurable: "0",
  };
}

/** Número de un campo de texto, o null si está vacío o no es válido. */
export function numero(s: string): number | null {
  const t = s.trim().replace(/\s/g, "");
  if (!t) return null;
  const v = Number(t);
  return Number.isFinite(v) ? v : null;
}

export const esEntero = (v: number | null): v is number => v != null && Number.isInteger(v);

export type Errores = Partial<Record<string, string>>;

/** UN mensual estimada por tipo de mes con la captura (misma fórmula del contrato). */
export function utilidadPorTipoMes(f: FormNegocio): { alto: number; normal: number; bajo: number } | null {
  const v = [f.ventas_mes_alto, f.ventas_mes_normal, f.ventas_mes_bajo].map(numero);
  const c = numero(f.costo_ventas_pct);
  if (v.some((x) => x == null) || c == null) return null;
  const fijos = [f.gastos_operativos, f.gastos_tributarios, f.carga_familiar, f.otras_deudas_cuota]
    .map((x) => numero(x) ?? 0)
    .reduce((a, b) => a + b, 0);
  const un = (ventas: number) => ventas * (1 - c / 100) - fijos;
  return { alto: un(v[0]!), normal: un(v[1]!), bajo: un(v[2]!) };
}

export function validarNegocio(f: FormNegocio): { errores: Errores; avisos: string[]; solicitud: CicloSolicitud | null } {
  const e: Errores = {};
  const avisos: string[] = [];
  if (!f.cliente_id.trim()) e.cliente_id = "Escribe un código para la solicitud (por ejemplo, C-0457).";
  if (!f.sector) e.sector = "Elige el sector del negocio.";
  if (!f.actividad) e.actividad = "Elige la actividad.";
  if (!f.zona) e.zona = "Elige la provincia donde trabaja el negocio.";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.fecha_inicio)) e.fecha_inicio = "Indica la fecha prevista de desembolso.";
  const meses = numero(f.meses);
  if (!esEntero(meses) || meses < PLAZO_MIN || meses > PLAZO_MAX)
    e.meses = `El plazo va de ${PLAZO_MIN} a ${PLAZO_MAX} meses, en meses enteros.`;

  const alto = numero(f.ventas_mes_alto);
  const normal = numero(f.ventas_mes_normal);
  const bajo = numero(f.ventas_mes_bajo);
  if (alto == null || alto < 0) e.ventas_mes_alto = "Anota cuánto vende en un buen mes (S/).";
  if (normal == null || normal < 0) e.ventas_mes_normal = "Anota cuánto vende en un mes regular (S/).";
  if (bajo == null || bajo < 0) e.ventas_mes_bajo = "Anota cuánto vende en su peor mes (S/). Puede ser 0.";
  if (alto != null && normal != null && !e.ventas_mes_alto && !e.ventas_mes_normal && alto < normal)
    e.ventas_mes_alto = "Un mes alto debe vender al menos lo de un mes normal.";
  if (normal != null && bajo != null && !e.ventas_mes_normal && !e.ventas_mes_bajo && normal < bajo)
    e.ventas_mes_bajo = "Un mes bajo no puede vender más que un mes normal.";

  const costo = numero(f.costo_ventas_pct);
  if (costo == null || costo < 0 || costo >= 100)
    e.costo_ventas_pct = "De cada S/ 100 vendidos, ¿cuánto se va en mercadería o insumos? Va de 0 a 99.";
  const montos: [keyof FormNegocio, string][] = [
    ["gastos_operativos", "los gastos operativos"],
    ["gastos_tributarios", "los gastos tributarios"],
    ["carga_familiar", "la carga familiar"],
    ["otras_deudas_cuota", "las cuotas de otras deudas"],
  ];
  for (const [campo, nombre] of montos) {
    const v = numero(f[campo] as string);
    if (v == null || v < 0) e[campo] = `Anota ${nombre} del mes (S/). Si no hay, escribe 0.`;
  }

  const evidencias: Evidencia[] = [];
  f.evidencias.forEach((ev, i) => {
    const m = numero(ev.meses);
    const monto = numero(ev.monto);
    if (!esEntero(m) || m <= 0) e[`evidencia_${i}`] = "Indica cuántos meses cubre la evidencia (entero mayor que 0).";
    else if (monto == null || monto < 0) e[`evidencia_${i}`] = "Indica el monto promedio mensual (S/).";
    else evidencias.push({ tipo: ev.tipo, meses: m, monto_promedio_mensual: monto });
  });

  const meses_altos = f.meses_estado.flatMap((s, i) => (s === "alto" ? [i + 1] : []));
  const meses_bajos = f.meses_estado.flatMap((s, i) => (s === "bajo" ? [i + 1] : []));
  if (!meses_altos.length && !meses_bajos.length)
    avisos.push("No marcaste meses altos ni bajos: el ciclo usará el patrón del sector y la zona.");

  const un = utilidadPorTipoMes(f);
  if (un && un.alto <= 0)
    avisos.push("Con estos datos el negocio no deja utilidad ni en su mejor mes: revisa costos y gastos.");

  if (Object.keys(e).length) return { errores: e, avisos, solicitud: null };
  return {
    errores: e,
    avisos,
    solicitud: {
      cliente_id: f.cliente_id.trim(),
      sector: f.sector,
      actividad: f.actividad,
      zona: f.zona!,
      fecha_inicio: f.fecha_inicio,
      meses: meses!,
      captura: {
        ventas_mes_alto: alto!,
        ventas_mes_normal: normal!,
        ventas_mes_bajo: bajo!,
        meses_altos,
        meses_bajos,
        costo_ventas_pct: Math.round(costo! * 100) / 10000,
        gastos_operativos: numero(f.gastos_operativos)!,
        gastos_tributarios: numero(f.gastos_tributarios)!,
        carga_familiar: numero(f.carga_familiar)!,
        otras_deudas_cuota: numero(f.otras_deudas_cuota)!,
        evidencias,
      },
    },
  };
}

export interface CreditoValidado {
  errores: Errores;
  /** Aviso de TEA sobre el tope: bloquea la propuesta. */
  sobreTope: boolean;
  solicitud: Omit<PlanSolicitud, "ciclo"> | null;
}

export function validarCredito(c: FormCredito, fechaDesembolso: string): CreditoValidado {
  const e: Errores = {};
  const prod = PRODUCTOS[c.producto];
  const monto = numero(c.monto);
  if (monto == null || monto <= 0) e.monto = "Anota el monto a desembolsar (S/).";
  const tea = numero(c.tea_pct);
  let sobreTope = false;
  if (tea == null || tea <= 0 || tea >= 200) e.tea_pct = "Anota la TEA en porcentaje, por ejemplo 45.";
  else if (prod.tope_tea != null && tea / 100 > prod.tope_tea + 1e-9) {
    sobreTope = true;
    e.tea_pct = `Supera el tope de ${(prod.tope_tea * 100).toFixed(2)}% del producto. Baja la TEA para proponer el plan.`;
  }
  const plazo = numero(c.plazo);
  if (!esEntero(plazo) || plazo < PLAZO_MIN || plazo > PLAZO_MAX)
    e.plazo = `El plazo va de ${PLAZO_MIN} a ${PLAZO_MAX} meses.`;
  const factor = numero(c.factor);
  if (factor == null || factor <= 0.1) e.factor = "El factor debe ser mayor que 0.10.";
  else if (factor > prod.factor + 1e-9)
    e.factor = `Solo puedes bajar el factor del producto (máximo ${prod.factor.toFixed(2)}).`;
  const desg = numero(c.desgravamen_pct);
  if (c.desgravamen && (desg == null || desg < 0 || desg > 1))
    e.desgravamen_pct = "Tasa mensual en %, por ejemplo 0.077.";
  const multi = numero(c.multirriesgo_pct);
  const valor = numero(c.valor_asegurable);
  if (c.multirriesgo) {
    if (multi == null || multi < 0 || multi > 1) e.multirriesgo_pct = "Tasa mensual en %, por ejemplo 0.03.";
    if (valor == null || valor <= 0) e.valor_asegurable = "Anota el valor asegurable (S/) del bien.";
  }
  if (Object.keys(e).length) return { errores: e, sobreTope, solicitud: null };
  return {
    errores: e,
    sobreTope,
    solicitud: {
      monto: monto!,
      tea: Math.round(tea! * 100) / 10000,
      fecha_desembolso: fechaDesembolso,
      plazo_meses: plazo!,
      producto: { ...prod, factor: factor! },
      seguros: {
        desgravamen: { activo: c.desgravamen, tasa_mensual: c.desgravamen ? desg! / 100 : 0.00077 },
        multirriesgo: {
          activo: c.multirriesgo,
          tasa_mensual: c.multirriesgo ? multi! / 100 : 0.0003,
          valor_asegurable: c.multirriesgo ? valor! : 0,
        },
      },
      comparar_cuota_fija: true,
    },
  };
}

/** Une la solicitud del crédito con el ciclo estimado. */
export const conCiclo = (s: Omit<PlanSolicitud, "ciclo">, ciclo: CicloRespuesta): PlanSolicitud => ({ ...s, ciclo });

export const textoMonto = (v: number) => fmtS0(v);
