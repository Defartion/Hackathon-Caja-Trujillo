// Cuota fija en pizarra clara y Thinku en azul: el par pasa el control de distinción para todo
// tipo de visión (ΔE 21 en OKLab; el gris anterior, #57606A, quedaba en 12.8).
export const COLOR_FIJA = '#8792A6';
export const COLOR_FLEX = '#0B5CAD';
export const COLOR_GRID = '#E8EBF0';
export const COLOR_EJE = '#CDD3DD';
export const COLOR_TEXTO_EJE = '#5A6478';

export const COLOR_PRODUCTO: Record<string, string> = {
  fija: '#57606A',
  aplazamiento: '#86b6ef',
  estacional: '#0B5CAD',
};
export const NOMBRE_PRODUCTO: Record<string, string> = {
  fija: 'Cuota fija',
  aplazamiento: 'Aplazamiento',
  estacional: 'Estacional',
};

export type Simbolo = 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'star';

export interface InfoRubro {
  id: string;
  nombre: string;
  corto: string;
  color: string;
  simbolo: Simbolo;
}

export const RUBROS: InfoRubro[] = [
  { id: 'agricultura', nombre: 'Agricultura', corto: 'Agricultura', color: '#eb6834', simbolo: 'circle' },
  { id: 'pesca', nombre: 'Pesca', corto: 'Pesca', color: '#1baf7a', simbolo: 'square' },
  { id: 'comercio_campana', nombre: 'Comercio de campaña', corto: 'Comercio', color: '#eda100', simbolo: 'triangle' },
  { id: 'calzado', nombre: 'Calzado', corto: 'Calzado', color: '#e87ba4', simbolo: 'diamond' },
  { id: 'bodega', nombre: 'Bodega', corto: 'Bodega', color: '#008300', simbolo: 'cross' },
  { id: 'servicios', nombre: 'Servicios', corto: 'Servicios', color: '#6250d6', simbolo: 'star' },
];

export const infoRubro = (id: string): InfoRubro =>
  RUBROS.find((r) => r.id === id) ?? { id, nombre: id, corto: id, color: '#57606A', simbolo: 'circle' };

export const ETIQUETA_CORTA_PARAM: Record<string, string> = {
  'flexibilidad.max_aplazamientos': 'Aplazamientos',
  'flexibilidad.cuota_minima_pct': 'Cuota mín.',
  'flexibilidad.cuota_maxima_mult': 'Cuota máx.',
  'flexibilidad.recargo_spread_tea': 'Recargo',
  'flexibilidad.requisito_dias_atraso_max': 'Atraso máx.',
  'capacidad_pago.ratio_cuota_excedente_max': 'Cuota/excedente',
  'capacidad_pago.ratio_deuda_total_max': 'Deuda total',
  'el_nino.probabilidad_anual': 'El Niño',
  'el_nino.meses_alivio': 'Alivio',
  'simulacion.fuga_caja_mensual': 'Gasto sobrante',
};
