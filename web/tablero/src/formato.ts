import type { FormatoParam } from './api';

const nf0 = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nfOpc1 = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 0, maximumFractionDigits: 1 });

const MENOS = '−';

export const entero = (v: number) => nf0.format(v);
export const decimal1 = (v: number) => nf1.format(v);
export const pct1 = (v: number) => `${nf1.format(v)}%`;

/** Soles compactos: S/ 1.38 M, S/ 206 k, S/ 950. */
export function soles(v: number): string {
  const a = Math.abs(v);
  const s = v < 0 ? MENOS : '';
  if (a >= 1e6) return `${s}S/ ${nf2.format(a / 1e6)} M`;
  if (a >= 1e3) return `${s}S/ ${nf0.format(a / 1e3)} k`;
  return `${s}S/ ${nf0.format(a)}`;
}

/** Soles exactos para tablas y rangos de tooltip. */
export const solesExacto = (v: number) => `${v < 0 ? MENOS : ''}S/ ${nf0.format(Math.abs(v))}`;

/** Etiqueta de eje: S/ -2 k, S/ 0, S/ 500. */
export function solesEje(v: number): string {
  if (v === 0) return 'S/ 0';
  if (Math.abs(v) >= 1000) return `S/ ${nfOpc1.format(v / 1000)} k`;
  return `S/ ${nf0.format(v)}`;
}

export function decimalesDePaso(paso: number): number {
  const s = String(paso);
  const i = s.indexOf('.');
  return i < 0 ? 0 : s.length - i - 1;
}

export function redondearAPaso(v: number, paso: number): number {
  return Number(v.toFixed(decimalesDePaso(paso)));
}

export function formatearValor(formato: FormatoParam, v: number): string {
  switch (formato) {
    case 'entero':
      return String(Math.round(v));
    case 'pct':
      return `${nfOpc1.format(v * 100)}%`;
    case 'mult':
      return `${nfOpc1.format(v)}×`;
    case 'pp':
      return `${v >= 0 ? '+' : MENOS}${nf1.format(Math.abs(v) * 100)} pp`;
    case 'dias':
      return `${Math.round(v)} ${Math.round(v) === 1 ? 'día' : 'días'}`;
    case 'meses':
      return `${Math.round(v)} ${Math.round(v) === 1 ? 'mes' : 'meses'}`;
  }
}

export type Tono = 'bueno' | 'malo' | 'neutro';
export interface DeltaInfo {
  tono: Tono;
  flecha: '▼' | '▲' | '';
  texto: string;
}

const SIN_CAMBIO: DeltaInfo = { tono: 'neutro', flecha: '', texto: 'Sin cambio' };

function relativo(base: number, nuevo: number): string {
  if (base === 0) return '';
  const r = ((nuevo - base) / Math.abs(base)) * 100;
  return `${r < 0 ? MENOS : '+'}${nf0.format(Math.abs(r))}%`;
}

/** Delta de una métrica en %: diferencia en pp + cambio relativo. */
export function deltaPct(fija: number, flex: number, menorEsMejor: boolean): DeltaInfo {
  const d = flex - fija;
  if (Math.abs(d) < 0.05) return SIN_CAMBIO;
  const rel = relativo(fija, flex);
  const mejor = menorEsMejor ? d < 0 : d > 0;
  return {
    tono: mejor ? 'bueno' : 'malo',
    flecha: d < 0 ? '▼' : '▲',
    texto: `${nf1.format(Math.abs(d))} pp${rel ? ` (${rel})` : ''}`,
  };
}

/** Delta en soles: diferencia compacta + cambio relativo. */
export function deltaSoles(fija: number, flex: number, masEsMejor: boolean): DeltaInfo {
  const d = flex - fija;
  if (Math.abs(d) < 0.5) return SIN_CAMBIO;
  const rel = relativo(fija, flex);
  const mejor = masEsMejor ? d > 0 : d < 0;
  return {
    tono: mejor ? 'bueno' : 'malo',
    flecha: d < 0 ? '▼' : '▲',
    texto: `${soles(Math.abs(d))}${rel ? ` (${rel})` : ''}`,
  };
}

/** Solo el cambio relativo (historial). */
export function deltaRelativo(fija: number, flex: number, masEsMejor: boolean): DeltaInfo {
  const d = flex - fija;
  if (Math.abs(d) < 0.5 || fija === 0) return SIN_CAMBIO;
  const mejor = masEsMejor ? d > 0 : d < 0;
  return { tono: mejor ? 'bueno' : 'malo', flecha: d < 0 ? '▼' : '▲', texto: relativo(fija, flex) };
}
