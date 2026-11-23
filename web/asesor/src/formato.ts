export const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];

const soles = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const enteros = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export const fmtS = (v: number) => `S/ ${soles.format(v)}`;
export const fmtS0 = (v: number) => `S/ ${enteros.format(v)}`;
export const fmtPct = (v: number, dec = 1) => `${(v * 100).toFixed(dec)}%`;

export const RUBRO_ETIQUETA: Record<string, string> = {
  agricultura: "Agricultura",
  pesca: "Pesca",
  comercio_campana: "Comercio de campaña",
  calzado: "Calzado",
  bodega: "Bodega",
  servicios: "Servicios",
};

export function nivelEstacionalidad(ie = 0): { texto: string; clase: string } {
  if (ie >= 0.25) return { texto: "Alta", clase: "alta" };
  if (ie >= 0.15) return { texto: "Media", clase: "media" };
  return { texto: "Baja", clase: "baja" };
}

/** Etiqueta del mes para un desplazamiento t respecto del primer mes de pago (t=0). */
export const mesRelativo = (mesInicio: number, t: number) => MESES[(((mesInicio + t) % 12) + 12) % 12];
