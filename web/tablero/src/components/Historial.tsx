import type { KeyboardEvent } from 'react';
import { ETIQUETA_CORTA_PARAM } from '../colores';
import { TAMANOS } from '../api';
import type { ParametroEditable, RespuestaCorrer, TamanoId } from '../api';
import { decimal1, deltaPct, deltaRelativo, formatearValor } from '../formato';
import type { DeltaInfo } from '../formato';

export interface Corrida {
  num: number;
  escenario: string;
  cambios: Record<string, number>;
  tamano: TamanoId;
  replanificar: boolean;
  resp: RespuestaCorrer;
}

interface Props {
  corridas: Corrida[];
  mostrada: number | null;
  parametros: ParametroEditable[];
  onElegir: (num: number) => void;
}

function Mini({ d }: { d: DeltaInfo }) {
  return (
    <span className={`hist-delta ${d.tono}`}>
      {d.flecha && <span aria-hidden="true">{d.flecha} </span>}
      {d.texto}
    </span>
  );
}

export default function Historial({ corridas, mostrada, parametros, onElegir }: Props) {
  const fmt = (ruta: string, v: number) => {
    const p = parametros.find((x) => x.ruta === ruta);
    return p ? formatearValor(p.formato, v) : String(v);
  };
  const corto = (ruta: string) => ETIQUETA_CORTA_PARAM[ruta] ?? parametros.find((x) => x.ruta === ruta)?.etiqueta ?? ruta;

  const tecla = (e: KeyboardEvent, num: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onElegir(num);
    }
  };

  return (
    <section className="tarjeta ancho2" aria-label="Historial de corridas">
      <div className="tarjeta-cab">
        <div>
          <h3 className="tarjeta-titulo">Historial de corridas</h3>
          <p className="tarjeta-sub">Las últimas 5 corridas; elige una fila para ver sus resultados</p>
        </div>
      </div>
      <div className="tabla-scroll">
        <table className="tabla">
          <thead>
            <tr>
              <th>#</th>
              <th>Escenario</th>
              <th>Tamaño</th>
              <th>Modo</th>
              <th>Atraso &gt; 30 d</th>
              <th>Default</th>
              <th>Margen / cartera</th>
              <th>Cartera</th>
              <th>Tiempo</th>
            </tr>
          </thead>
          <tbody>
            {corridas.map((c) => {
              const f = c.resp.resumen.fija;
              const x = c.resp.resumen.cuotaflex;
              const claves = Object.keys(c.cambios);
              return (
                <tr
                  key={c.num}
                  className="fila-hist"
                  tabIndex={0}
                  aria-selected={c.num === mostrada}
                  onClick={() => onElegir(c.num)}
                  onKeyDown={(e) => tecla(e, c.num)}
                >
                  <td>{c.num}</td>
                  <td>
                    {c.escenario}
                    <div className="chips">
                      {claves.length === 0 ? (
                        <span className="chip">Sin cambios</span>
                      ) : (
                        claves.map((k) => (
                          <span key={k} className="chip">
                            {corto(k)} {fmt(k, c.cambios[k])}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td>
                    {TAMANOS[c.tamano].n_clientes}×{TAMANOS[c.tamano].n_escenarios}
                  </td>
                  <td>{c.replanificar ? 'Completo' : 'Solo cronograma'}</td>
                  <td>
                    {decimal1(f.mora30_pct)} → {decimal1(x.mora30_pct)}
                    <Mini d={deltaPct(f.mora30_pct, x.mora30_pct, true)} />
                  </td>
                  <td>
                    {decimal1(f.default_pct)} → {decimal1(x.default_pct)}
                    <Mini d={deltaPct(f.default_pct, x.default_pct, true)} />
                  </td>
                  <td>
                    {decimal1(f.margen_sobre_cartera_pct)} → {decimal1(x.margen_sobre_cartera_pct)}
                    <Mini d={deltaPct(f.margen_sobre_cartera_pct, x.margen_sobre_cartera_pct, false)} />
                  </td>
                  <td>
                    <Mini d={deltaRelativo(f.cartera, x.cartera, true)} />
                  </td>
                  <td>{c.resp.desde_cache ? 'caché' : `${decimal1(c.resp.duracion_s)} s`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
