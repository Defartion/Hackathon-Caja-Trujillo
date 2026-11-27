// Cliente HTTP y tipos de la API de CuotaFlex.
export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000";
const BASE = "/fineract-provider/api/v1";

export interface Cliente {
  cliente_id: string;
  rubro: string;
  region?: string | null;
  ventas_medias: number;
  margen: number;
  gasto_familiar: number;
  otras_cuotas: number;
  dias_atraso_max: number;
  creditos_previos?: number | null;
  pct_cobros_yape?: number | null;
  antiguedad_negocio_anios?: number | null;
  ajuste_asesor: number;
  principal: number;
  plazo: number;
  tea: number;
  mes_desembolso: number;
  historial_ventas?: number[];
  indice_estacionalidad?: number;
}

export interface FilaCronograma {
  numero: number;
  cuota: number;
  interes: number;
  capital: number;
  saldo: number;
  mes: string;
  excedente_p25: number;
  excedente_p50: number;
}

export interface PasoBitacora {
  paso: string;
  [k: string]: unknown;
}

export interface Propuesta {
  cliente_id: string;
  producto: "fija" | "aplazamiento" | "estacional";
  descripcion_producto: string;
  principal_solicitado: number;
  principal_aprobado: number;
  plazo: number;
  tea: number;
  cuota_fija_referencia: number;
  clausula_el_nino: boolean;
  aplazamientos_disponibles: number;
  cronograma: FilaCronograma[];
  valido: boolean;
  bitacora: PasoBitacora[];
  explicacion: string;
}

export interface Riesgo {
  mora30: number;
  default: number;
  vpn_medio: number;
  vpn_p5: number;
  cuotas: number[];
}

export interface RespuestaPropuesta {
  propuesta: Propuesta;
  historial_ventas: number[];
  pronostico: { p10: number[]; p25: number[]; p50: number[]; p90: number[] };
  capacidad: number[];
  comparativa: { fija: Riesgo; cuotaflex: Riesgo; n_escenarios: number };
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(API_URL + ruta, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new Error(`No se pudo conectar con la API (${API_URL}). ¿Está corriendo uvicorn?`);
  }
  if (!r.ok) {
    let detalle = r.statusText;
    try {
      const j = await r.json();
      detalle = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(`Error ${r.status}: ${detalle}`);
  }
  return r.json() as Promise<T>;
}

const post = <T,>(ruta: string, body?: unknown) =>
  pedir<T>(ruta, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  cartera: (n = 30, semilla = 7) => pedir<Cliente[]>(`/motor/cartera-demo?n=${n}&semilla=${semilla}`),
  propuesta: (c: Cliente) => post<RespuestaPropuesta>("/motor/propuesta", c),
  crearCliente: (c: Cliente) =>
    post<{ clientId: number }>(`${BASE}/clients`, {
      nombre: `Cliente ${c.cliente_id}`,
      rubro: c.rubro,
      ventas_medias: c.ventas_medias,
      margen: c.margen,
      gasto_familiar: c.gasto_familiar,
      otras_cuotas: c.otras_cuotas,
      dias_atraso_max: c.dias_atraso_max,
      ajuste_asesor: c.ajuste_asesor,
      historial_ventas: c.historial_ventas,
    }),
  crearPrestamo: (clientId: number, c: Cliente) =>
    post<{ loanId: number; producto: string }>(`${BASE}/loans`, {
      clientId,
      principal: c.principal,
      numberOfRepayments: c.plazo,
      tea: c.tea,
      mesPrimeraCuota: c.mes_desembolso,
    }),
  prestamo: (id: number) => pedir<Prestamo>(`${BASE}/loans/${id}?associations=repaymentSchedule`),
  variaciones: (id: number, cuotas: number[]) =>
    post<unknown>(`${BASE}/loans/${id}/schedule?command=addVariations`, { cuotas }),
  comando: (id: number, command: "approve" | "disburse") =>
    post<{ status: { value: string } }>(`${BASE}/loans/${id}?command=${command}`),
  prestamos: () => pedir<PrestamoListado[]>("/motor/prestamos"),
  /** Fase 4: código de 6 dígitos con el que el cliente entra a ver su préstamo. */
  llave: (id: number) => pedir<LlaveCliente>(`/motor/prestamos/${id}/llave`),
  regenerarLlave: (id: number) => post<LlaveCliente>(`/motor/prestamos/${id}/llave/regenerar`),
  detallePrestamo: (id: number) => pedir<DetallePrestamo>(`/motor/prestamos/${id}`),
};

export interface CuotaDetalle {
  numero: number;
  mes: string;
  cuota: number;
  interes: number;
  capital: number;
  saldo: number;
  /** Vencimiento (último día del mes), AAAA-MM-DD. */
  fecha: string;
  estado: "pagada" | "proxima" | "pendiente";
  fechaPago: string | null;
}

export interface CuotaResumida {
  numero: number;
  mes: string;
  monto: number;
  fecha: string;
}

/** GET /motor/prestamos/{id}: todo lo del préstamo registrado en una sola respuesta. */
export interface DetallePrestamo {
  id: number;
  clientId: number;
  estado: string;
  producto: string | null;
  descripcionProducto: string;
  principal: number;
  principalSolicitado: number | null;
  plazo: number;
  tea: number;
  fechaDesembolso: string | null;
  cuotaMinima: number;
  cuotaMaxima: number;
  cuotaFijaReferencia: number | null;
  aplazamientosRestantes: number;
  clausulaElNino: boolean;
  cumplePoliticas: boolean | null;
  explicacion: string;
  cliente: {
    nombre: string | null;
    rubro: string | null;
    region: string | null;
    ventas_medias: number | null;
    margen: number | null;
    gasto_familiar: number | null;
    otras_cuotas: number | null;
    dias_atraso_max: number | null;
    ajuste_asesor: number | null;
  };
  cuotasPagadas: number;
  totalCuotas: number;
  pagos: { fecha: string | null; monto: number | null; cuota: number | null }[];
  resumen: {
    totalAPagar: number;
    totalPagado: number;
    porPagar: number;
    saldoCapital: number;
    interesesTotales: number;
    cuotasPendientes: number;
    cuotaMayor: CuotaResumida | null;
    cuotaMenor: CuotaResumida | null;
    proximoVencimiento: string | null;
    diasParaVencer: number | null;
  };
  cronograma: CuotaDetalle[];
}

export interface PrestamoListado {
  id: number;
  clientId: number;
  cliente: string;
  rubro: string | null;
  estado: string;
  principal: number;
  plazo: number;
  producto: string | null;
  cuota_min: number;
  cuota_max: number;
  aplazamientos_restantes: number;
}

export interface Prestamo {
  id: number;
  status: { value: string };
  principal: number;
  numberOfRepayments: number;
  tea: number;
  producto: string;
  repaymentSchedule?: {
    periods: {
      period: number;
      totalDueForPeriod: number;
      principalDue: number;
      interestDue: number;
      principalLoanBalanceOutstanding: number;
    }[];
  };
}

export interface LlaveCliente {
  prestamo: number;
  codigo: string;
  version: number;
  estado: string;
  cliente: string | null;
}
