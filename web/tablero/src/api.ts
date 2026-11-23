export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000';

export const TIMEOUT_MS = 30_000;
export const SEMILLA = 2026;

export type FormatoParam = 'entero' | 'pct' | 'mult' | 'pp' | 'dias' | 'meses';

export interface ParametroEditable {
  ruta: string;
  grupo: string;
  etiqueta: string;
  minimo: number;
  maximo: number;
  paso: number;
  formato: FormatoParam;
  ayuda: string;
  rango_valido: [number, number];
  valor: number;
}

export interface Escenario {
  id: string;
  nombre: string;
  descripcion: string;
  cambios: Record<string, number>;
}

export interface Estrategia {
  mora30_pct: number;
  default_pct: number;
  margen_neto_total: number;
  cartera: number;
  margen_sobre_cartera_pct: number;
}

export interface RubroResumen {
  mora30_fija: number;
  mora30_cuotaflex: number;
  vpn_fija: number;
  vpn_cuotaflex: number;
}

export interface Resumen {
  fija: Estrategia;
  cuotaflex: Estrategia;
  delta: {
    mora30_relativa_pct: number | null;
    default_relativo_pct: number | null;
    margen_neto_dif: number;
  };
  por_rubro: Record<string, RubroResumen>;
  mix_productos: { fija?: number; aplazamiento?: number; estacional?: number };
}

export interface HistogramaVpn {
  bordes: number[];
  fija: number[];
  cuotaflex: number[];
}

export interface PuntoDispersion {
  cliente_id: string;
  rubro: string;
  producto: string;
  mora_fija: number;
  mora_flex: number;
}

export interface RespuestaCorrer {
  resumen: Resumen;
  histograma_vpn: HistogramaVpn;
  dispersion: PuntoDispersion[];
  duracion_s: number;
  desde_cache: boolean;
  parametros_usados?: Record<string, number>;
  consulta?: Record<string, unknown>;
}

export type TamanoId = 'rapido' | 'estandar' | 'completo';

export const TAMANOS: Record<TamanoId, { nombre: string; n_clientes: number; n_escenarios: number }> = {
  rapido: { nombre: 'Rápido', n_clientes: 150, n_escenarios: 80 },
  estandar: { nombre: 'Estándar', n_clientes: 300, n_escenarios: 150 },
  completo: { nombre: 'Completo', n_clientes: 600, n_escenarios: 200 },
};

/** Segundos esperados por tamaño; se reemplazan por la última duración real medida. */
export const ESPERADO_S: Record<TamanoId, number> = { rapido: 4, estandar: 6, completo: 12 };

export class ErrorApi extends Error {
  tipo: 'timeout' | 'red' | 'http';
  constructor(tipo: 'timeout' | 'red' | 'http', mensaje: string) {
    super(mensaje);
    this.tipo = tipo;
  }
}

function mensajeDetalle(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join('; ');
  }
  return 'Solicitud no válida.';
}

async function pedir<T>(ruta: string, init?: RequestInit, timeoutMs = TIMEOUT_MS): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  let resp: Response;
  try {
    resp = await fetch(`${API_URL}${ruta}`, { ...init, signal: ctl.signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ErrorApi(
        'timeout',
        ruta === '/simulacion/correr'
          ? `La simulación tardó más de ${timeoutMs / 1000} s y se canceló. El servidor puede seguir calculando: vuelve a intentarlo en unos segundos (el resultado quedará en caché) o elige un tamaño menor.`
          : `La API no respondió en ${timeoutMs / 1000} s (${API_URL}).`,
      );
    }
    throw new ErrorApi('red', `No se pudo conectar con la API (${API_URL}). ¿Está corriendo uvicorn?`);
  } finally {
    clearTimeout(t);
  }
  if (!resp.ok) {
    let msg = `La API respondió con error ${resp.status}.`;
    try {
      const j = (await resp.json()) as { detail?: unknown };
      if (j.detail !== undefined) msg = `${msg} ${mensajeDetalle(j.detail)}`;
    } catch {
      /* sin cuerpo JSON */
    }
    throw new ErrorApi('http', msg);
  }
  return (await resp.json()) as T;
}

export const obtenerParametros = () =>
  pedir<ParametroEditable[]>('/simulacion/parametros-editables', undefined, 10_000);
export const obtenerEscenarios = () => pedir<Escenario[]>('/simulacion/escenarios', undefined, 10_000);

export interface CuerpoCorrer {
  n_clientes: number;
  n_escenarios: number;
  semilla: number;
  replanificar: boolean;
  cambios: Record<string, number>;
}

export const correr = (cuerpo: CuerpoCorrer) =>
  pedir<RespuestaCorrer>('/simulacion/correr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  });
