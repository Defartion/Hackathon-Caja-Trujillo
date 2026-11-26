// Resultados de una corrida del tablero listos para exportar (PDF, Excel, CSV, JSON o texto).
import { TAMANOS } from './api';
import type { Corrida } from './components/Historial';
import { infoRubro, NOMBRE_PRODUCTO } from './colores';
import type { Documento } from './exportar';

const pct = (v: number | null | undefined) => (v === null || v === undefined ? null : v / 100);

export function documentoCorrida(c: Corrida): Documento {
  const { resumen, dispersion, histograma_vpn: h } = c.resp;
  const t = TAMANOS[c.tamano];
  const f = resumen.fija;
  const x = resumen.cuotaflex;
  return {
    archivo: `simulacion-corrida-${c.num}`,
    titulo: `Simulación, corrida #${c.num}: ${c.escenario}`,
    subtitulo: `${t.n_clientes} créditos por ${t.n_escenarios} escenarios, ${c.replanificar ? 'modo completo' : 'solo cronograma'}. Cuota fija frente a CuotaFlex.`,
    resumen: [
      { etiqueta: 'Mora >30 días, cuota fija', valor: pct(f.mora30_pct), tipo: 'porcentaje' },
      { etiqueta: 'Mora >30 días, CuotaFlex', valor: pct(x.mora30_pct), tipo: 'porcentaje' },
      { etiqueta: 'Cambio relativo en mora', valor: pct(resumen.delta.mora30_relativa_pct), tipo: 'porcentaje' },
      { etiqueta: 'Default, cuota fija', valor: pct(f.default_pct), tipo: 'porcentaje' },
      { etiqueta: 'Default, CuotaFlex', valor: pct(x.default_pct), tipo: 'porcentaje' },
      { etiqueta: 'Cambio relativo en default', valor: pct(resumen.delta.default_relativo_pct), tipo: 'porcentaje' },
      { etiqueta: 'Margen neto, cuota fija', valor: f.margen_neto_total, tipo: 'moneda' },
      { etiqueta: 'Margen neto, CuotaFlex', valor: x.margen_neto_total, tipo: 'moneda' },
      { etiqueta: 'Diferencia de margen neto', valor: resumen.delta.margen_neto_dif, tipo: 'moneda' },
      { etiqueta: 'Duración (s)', valor: c.resp.duracion_s, tipo: 'decimal' },
    ],
    tablas: [
      {
        titulo: 'Por estrategia',
        columnas: [
          { clave: 'estrategia', titulo: 'Estrategia' },
          { clave: 'mora', titulo: 'Mora >30 días', tipo: 'porcentaje' },
          { clave: 'default', titulo: 'Default', tipo: 'porcentaje' },
          { clave: 'margen', titulo: 'Margen neto', tipo: 'moneda' },
          { clave: 'cartera', titulo: 'Cartera', tipo: 'moneda' },
          { clave: 'margenCartera', titulo: 'Margen sobre cartera', tipo: 'porcentaje' },
        ],
        filas: [
          ['Cuota fija', f],
          ['CuotaFlex', x],
        ].map(([nombre, e]) => {
          const est = e as typeof f;
          return {
            estrategia: nombre,
            mora: pct(est.mora30_pct),
            default: pct(est.default_pct),
            margen: est.margen_neto_total,
            cartera: est.cartera,
            margenCartera: pct(est.margen_sobre_cartera_pct),
          };
        }),
      },
      {
        titulo: 'Por rubro',
        columnas: [
          { clave: 'rubro', titulo: 'Rubro' },
          { clave: 'moraFija', titulo: 'Mora fija', tipo: 'porcentaje' },
          { clave: 'moraFlex', titulo: 'Mora CuotaFlex', tipo: 'porcentaje' },
          { clave: 'vpnFija', titulo: 'VPN fija', tipo: 'moneda' },
          { clave: 'vpnFlex', titulo: 'VPN CuotaFlex', tipo: 'moneda' },
        ],
        filas: Object.entries(resumen.por_rubro).map(([id, r]) => ({
          rubro: infoRubro(id).nombre,
          moraFija: pct(r.mora30_fija),
          moraFlex: pct(r.mora30_cuotaflex),
          vpnFija: r.vpn_fija,
          vpnFlex: r.vpn_cuotaflex,
        })),
      },
      {
        titulo: 'Productos asignados',
        columnas: [
          { clave: 'producto', titulo: 'Producto' },
          { clave: 'creditos', titulo: 'Créditos', tipo: 'entero' },
        ],
        filas: Object.entries(resumen.mix_productos).map(([id, n]) => ({ producto: NOMBRE_PRODUCTO[id] ?? id, creditos: n })),
      },
      {
        titulo: 'VPN por crédito',
        columnas: [
          { clave: 'desde', titulo: 'VPN desde', tipo: 'moneda' },
          { clave: 'hasta', titulo: 'VPN hasta', tipo: 'moneda' },
          { clave: 'fija', titulo: 'Créditos, fija', tipo: 'entero' },
          { clave: 'flex', titulo: 'Créditos, CuotaFlex', tipo: 'entero' },
        ],
        filas: h.fija.map((n, i) => ({ desde: h.bordes[i], hasta: h.bordes[i + 1], fija: n, flex: h.cuotaflex[i] })),
      },
      {
        titulo: 'Créditos simulados',
        columnas: [
          { clave: 'cliente_id', titulo: 'Cliente' },
          { clave: 'rubro', titulo: 'Rubro' },
          { clave: 'producto', titulo: 'Producto' },
          { clave: 'mora_fija', titulo: 'Mora con cuota fija', tipo: 'porcentaje' },
          { clave: 'mora_flex', titulo: 'Mora con CuotaFlex', tipo: 'porcentaje' },
        ],
        filas: dispersion.map((d) => ({
          ...d,
          rubro: infoRubro(d.rubro).nombre,
          producto: NOMBRE_PRODUCTO[d.producto] ?? d.producto,
        })),
      },
    ],
    notas: ['Datos 100% sintéticos. Parámetros referenciales a calibrar con Caja Trujillo.'],
  };
}
