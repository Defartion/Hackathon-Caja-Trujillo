// Expedientes que el Asesor de Negocios envía al comité y validación del Asesor de Riesgos.
// Maqueta del flujo: se guardan en localStorage (dentro de try/catch) y, si el navegador no lo
// permite, en memoria mientras dure la pestaña. Solo datos sintéticos.
import type { CicloRespuesta, CicloSolicitud, PlanRespuesta, PlanSolicitud } from "../../contratos";
import type { FormCredito, FormNegocio } from "./formularios";

/** Ajuste del motor que el asesor aplicó. Solo se informa si sigue vigente al guardar. */
export interface AjusteAplicado {
  campo: "monto" | "plazo" | "factor";
  antes: string;
  despues: string;
  texto: string;
}

export interface Expediente {
  version: 1;
  id: string;
  creado: string;
  modo: "mock" | "api";
  negocio: FormNegocio;
  credito: FormCredito;
  cicloSolicitud: CicloSolicitud;
  ciclo: CicloRespuesta;
  planSolicitud: Omit<PlanSolicitud, "ciclo">;
  plan: PlanRespuesta;
  /** Monto que pidió el cliente antes de aplicar ajustes del motor. */
  montoSolicitado: number;
  /** Ajustes sugeridos por el motor que el asesor aplicó y siguen vigentes. */
  ajustes: AjusteAplicado[];
}

export type Decision = "aprobado" | "observado" | "rechazado";

export interface Validacion {
  decision: Decision;
  comentario: string;
  nombre: string;
  fecha: string;
}

const PREFIJO = "cuotaflex.f4";
const memoria = new Map<string, string>();

function leer(clave: string): string | null {
  try {
    const v = window.localStorage.getItem(clave);
    if (v !== null) return v;
  } catch {
    /* almacenamiento bloqueado: se usa la memoria */
  }
  return memoria.get(clave) ?? null;
}

/** Devuelve true si quedó en localStorage; false si solo quedó en memoria. */
function escribir(clave: string, valor: string): boolean {
  memoria.set(clave, valor);
  try {
    window.localStorage.setItem(clave, valor);
    return true;
  } catch {
    return false;
  }
}

function borrar(clave: string) {
  memoria.delete(clave);
  try {
    window.localStorage.removeItem(clave);
  } catch {
    /* sin almacenamiento */
  }
}

function leerJson<T>(clave: string): T | null {
  const v = leer(clave);
  if (!v) return null;
  try {
    return JSON.parse(v) as T;
  } catch {
    return null;
  }
}

export const guardarExpediente = (e: Expediente) => escribir(`${PREFIJO}.expediente.${e.id}`, JSON.stringify(e));

export function leerExpediente(id: string): Expediente | null {
  const e = leerJson<Expediente>(`${PREFIJO}.expediente.${id}`);
  if (!e || e.version !== 1 || !e.plan || !e.ciclo || !e.planSolicitud) return null;
  const ajustes = Array.isArray(e.ajustes) ? e.ajustes.filter((a) => a && typeof a === "object" && typeof a.texto === "string") : [];
  return { ...e, ajustes };
}

export const guardarValidacion = (id: string, v: Validacion) =>
  escribir(`${PREFIJO}.validacion.${id}`, JSON.stringify(v));

export const leerValidacion = (id: string) => leerJson<Validacion>(`${PREFIJO}.validacion.${id}`);

export const borrarValidacion = (id: string) => borrar(`${PREFIJO}.validacion.${id}`);

export const DECISION_ETIQUETA: Record<Decision, string> = {
  aprobado: "Aprobado",
  observado: "Observado",
  rechazado: "Rechazado",
};
