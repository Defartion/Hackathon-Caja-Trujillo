// Llamadas de la fase 4 (lote C): ciclo (lote B), plan (lote A) y explicación del agente (lote D).
// Con VITE_MOCK=1 responde con los JSON de src/mocks/ (copia de tests/fixtures/contratos/, caso Rosa),
// así la app no depende de que los otros lotes estén listos. Los mocks se cargan en un trozo aparte
// del bundle, solo en modo mock.
import { API_URL } from "./api";
import type {
  CatalogoCiclo,
  CicloRespuesta,
  CicloSolicitud,
  PeriodoCiclo,
  PlanRespuesta,
  PlanSolicitud,
} from "./contratos";

export const MODO_MOCK = String(import.meta.env.VITE_MOCK ?? "") === "1";

/** Monto máximo factible del mock: por encima responde "no factible" (salvo plazo ≥ 30). */
export const MOCK_MONTO_MAXIMO = 7000;
const MOCK_PLAZO_MINIMO = 30;
const LATENCIA_MOCK_MS = 150;

const ETIQUETAS_CAMPO: Record<string, string> = {
  cliente_id: "Código del cliente",
  sector: "Sector",
  actividad: "Actividad",
  zona: "Zona",
  provincia: "Provincia",
  fecha_inicio: "Fecha de desembolso",
  fecha_desembolso: "Fecha de desembolso",
  meses: "Plazo",
  plazo_meses: "Plazo",
  ventas_mes_alto: "Ventas en mes alto",
  ventas_mes_normal: "Ventas en mes normal",
  ventas_mes_bajo: "Ventas en mes bajo",
  meses_altos: "Meses altos",
  meses_bajos: "Meses bajos",
  costo_ventas_pct: "Costo de ventas",
  gastos_operativos: "Gastos operativos",
  gastos_tributarios: "Gastos tributarios",
  carga_familiar: "Carga familiar",
  otras_deudas_cuota: "Otras deudas",
  evidencias: "Evidencias",
  monto: "Monto",
  tea: "TEA",
  factor: "Factor",
};

/** Convierte el `detail` de FastAPI (texto o lista de errores de validación) en un mensaje legible. */
function detalleLegible(detalle: unknown): string {
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle)) {
    return detalle
      .map((e: { loc?: unknown[]; msg?: string }) => {
        const campos = (e.loc ?? []).filter((x) => x !== "body" && typeof x === "string") as string[];
        const campo = campos.length ? ETIQUETAS_CAMPO[campos[campos.length - 1]] ?? campos[campos.length - 1] : "";
        const msg = String(e.msg ?? "dato inválido").replace(/^Value error, /, "");
        return campo ? `${campo}: ${msg}` : msg;
      })
      .join(" · ");
  }
  return JSON.stringify(detalle);
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
      detalle = detalleLegible(j.detail ?? j);
    } catch {
      /* respuesta sin JSON */
    }
    if (r.status === 404) throw new Error(`La API todavía no expone ${ruta} (Error 404).`);
    throw new Error(`Error ${r.status}: ${detalle}`);
  }
  return r.json() as Promise<T>;
}

const post = <T,>(ruta: string, cuerpo: unknown) => pedir<T>(ruta, { method: "POST", body: JSON.stringify(cuerpo) });

// ---------------------------------------------------------------------------------------------
// Modo mock
// ---------------------------------------------------------------------------------------------
const cargadores = import.meta.glob<unknown>("./mocks/*.json", { import: "default" });

async function mock<T>(nombre: string): Promise<T> {
  const cargar = cargadores[`./mocks/${nombre}.json`];
  if (!cargar) throw new Error(`Falta el mock src/mocks/${nombre}.json`);
  const [datos] = await Promise.all([cargar(), new Promise((r) => setTimeout(r, LATENCIA_MOCK_MS))]);
  return JSON.parse(JSON.stringify(datos)) as T;
}

/** "AAAA-MM" del mes k (1 = mes siguiente al desembolso). */
function periodoDesde(fechaInicio: string, k: number): string {
  const [a, m] = fechaInicio.split("-").map(Number);
  const total = a * 12 + (m - 1) + k;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
}

/** Repite el patrón anual si el horizonte pedido supera al del ejemplo. */
function ajustarLargo<T>(valores: T[], n: number): T[] {
  const out = valores.slice(0, n);
  while (out.length < n) out.push(out[out.length - 12] ?? out[out.length - 1]);
  return out;
}

async function cicloMock(sol: CicloSolicitud): Promise<CicloRespuesta> {
  const base = await mock<CicloRespuesta>("ciclo_estimar_respuesta");
  const n = sol.meses;
  const periodos: PeriodoCiclo[] = ajustarLargo(base.periodos, n).map((p, i) => ({
    ...p,
    periodo: periodoDesde(sol.fecha_inicio, i + 1),
  }));
  return {
    ...base,
    cliente_id: sol.cliente_id,
    sector: sol.sector,
    actividad: sol.actividad,
    zona: sol.zona,
    fecha_inicio: sol.fecha_inicio,
    meses: n,
    periodos,
    escenarios: base.escenarios.map((e) => ({ ...e, un: ajustarLargo(e.un, n) })),
  };
}

async function planMock(sol: PlanSolicitud): Promise<PlanRespuesta> {
  const tope = sol.producto.tope_tea;
  if (tope != null && sol.tea > tope) {
    await new Promise((r) => setTimeout(r, LATENCIA_MOCK_MS));
    throw new Error(
      `Error 422: La TEA ${(sol.tea * 100).toFixed(2)}% supera el tope del producto (${(tope * 100).toFixed(2)}%).`,
    );
  }
  const factible = sol.monto <= MOCK_MONTO_MAXIMO || sol.plazo_meses >= MOCK_PLAZO_MINIMO;
  return mock<PlanRespuesta>(factible ? "plan_proponer_respuesta" : "plan_proponer_no_factible");
}

// ---------------------------------------------------------------------------------------------
// Explicación del agente para el comité (lote D). Solo se pide si la API la publica en su OpenAPI,
// para no generar un 404 mientras el endpoint no exista.
// ---------------------------------------------------------------------------------------------
export interface ExplicacionAgente {
  texto: string;
  verificada: boolean | null;
}

let rutasApi: Promise<Record<string, Record<string, unknown>>> | null = null;

function rutasDisponibles() {
  rutasApi ??= fetch(`${API_URL}/openapi.json`)
    .then((r) => (r.ok ? r.json() : { paths: {} }))
    .then((j: { paths?: Record<string, Record<string, unknown>> }) => j.paths ?? {})
    .catch(() => ({}));
  return rutasApi;
}

function explicacionLegible(r: unknown): ExplicacionAgente | null {
  if (typeof r === "string") return r.trim() ? { texto: r, verificada: null } : null;
  if (r && typeof r === "object") {
    const o = r as Record<string, unknown>;
    const texto = [o.texto, o.explicacion, o.respuesta, o.resumen].find((x) => typeof x === "string" && x.trim());
    if (typeof texto !== "string") return null;
    const v = o.cifras_verificadas ?? o.verificada ?? o.verificado;
    return { texto, verificada: typeof v === "boolean" ? v : null };
  }
  return null;
}

export const RUTA_EXPLICACION = "/agente/explicacion-comite";

export const apiPlan = {
  catalogo: (): Promise<CatalogoCiclo> => (MODO_MOCK ? mock<CatalogoCiclo>("ciclo_catalogo") : pedir("/ciclo/catalogo")),

  estimarCiclo: (sol: CicloSolicitud): Promise<CicloRespuesta> =>
    MODO_MOCK ? cicloMock(sol) : post("/ciclo/estimar", sol),

  proponerPlan: (sol: PlanSolicitud): Promise<PlanRespuesta> =>
    MODO_MOCK ? planMock(sol) : post("/plan/proponer", sol),

  /** null = el lote D aún no expone el endpoint (la vista muestra el espacio reservado). */
  async explicacionComite(datos: {
    cliente_id: string;
    ciclo: CicloRespuesta;
    plan: PlanRespuesta;
    solicitud: Omit<PlanSolicitud, "ciclo">;
  }): Promise<ExplicacionAgente | null> {
    if (MODO_MOCK) return null;
    const ruta = (await rutasDisponibles())[RUTA_EXPLICACION];
    if (!ruta) return null;
    if ("post" in ruta) return explicacionLegible(await post<unknown>(RUTA_EXPLICACION, datos));
    if ("get" in ruta)
      return explicacionLegible(
        await pedir<unknown>(`${RUTA_EXPLICACION}?cliente_id=${encodeURIComponent(datos.cliente_id)}`),
      );
    return null;
  },
};
