import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { API_URL } from '../api';
import { infoRubro } from '../colores';
import { entero, pct1, solesExacto } from '../formato';

/** Distintivo del ENFEN en la cabecera (fase 2 · lote C). Al hacer clic muestra el impacto en la cartera. */

type CodigoEstado = 'NO_ACTIVO' | 'VIGILANCIA_NINO' | 'ALERTA_NINO' | 'VIGILANCIA_NINA' | 'ALERTA_NINA';

interface EstadoApi {
  modo: 'oficial' | 'demo';
  estado: CodigoEstado;
  etiqueta: string;
  activo: boolean;
  magnitud: string | null;
  numero: string | null;
  titulo: string | null;
  fecha: string | null;
  fuente: string;
  url_fuente: string | null;
  obtenido_en: string | null;
  desde: string | null;
  desactualizado: boolean;
  error: string | null;
  advertencias: string[];
}

interface Resumen {
  prestamos: number;
  saldo: number;
  cuotasAlivio: number;
}

interface Impacto {
  estado: CodigoEstado | null;
  alivioHabilitado: boolean;
  mesesAlivio: number;
  cartera: Resumen;
  total: Resumen;
  grupos: (Resumen & { rubro: string; region: string })[];
}

const TONOS: Record<CodigoEstado, { texto: string; fondo: string; punto: string }> = {
  ALERTA_NINO: { texto: '#8E0B20', fondo: '#FDECEE', punto: '#C8102E' },
  VIGILANCIA_NINO: { texto: '#6B4309', fondo: '#FFF4DE', punto: '#B7791F' },
  NO_ACTIVO: { texto: '#14532D', fondo: '#E9F6EC', punto: '#1A7F37' },
  VIGILANCIA_NINA: { texto: '#0B4A8B', fondo: '#E8F1FB', punto: '#0B5CAD' },
  ALERTA_NINA: { texto: '#062F5C', fondo: '#DCE8F7', punto: '#08427E' },
};

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const INTERVALO_MS = 20_000;

/** "2026-11-13" -> "13 nov 2026", sin pasar por Date (evita el corrimiento de zona horaria). */
function fechaCorta(iso: string | null): string {
  if (!iso) return '';
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number);
  return `${d} ${MESES[m - 1]} ${a}`;
}

async function pedirJson<T>(ruta: string): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 10_000);
  try {
    const r = await fetch(`${API_URL}${ruta}`, { signal: ctl.signal });
    if (!r.ok) {
      let detalle = `La API respondió con error ${r.status}.`;
      try {
        const j = (await r.json()) as { detail?: unknown };
        if (typeof j.detail === 'string') detalle = j.detail;
      } catch {
        /* sin cuerpo JSON */
      }
      throw new Error(detalle);
    }
    return (await r.json()) as T;
  } catch (e) {
    if (e instanceof Error && e.message && e.name !== 'AbortError' && e.name !== 'TypeError') throw e;
    throw new Error(`No se pudo conectar con la API (${API_URL}).`);
  } finally {
    clearTimeout(t);
  }
}

function textoAlivio(impacto: Impacto): string {
  if (impacto.alivioHabilitado)
    return `Alivio habilitado: los clientes con cláusula pueden pagar la cuota mínima (hasta ${impacto.mesesAlivio} veces).`;
  if (impacto.estado === 'VIGILANCIA_NINO') return 'Vigilancia: aviso preventivo a los clientes, todavía sin alivio.';
  return 'Sin alerta de El Niño Costero: el alivio no está habilitado.';
}

export default function EstadoEnfen() {
  const [estado, setEstado] = useState<EstadoApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [impacto, setImpacto] = useState<Impacto | null>(null);
  const [errorImpacto, setErrorImpacto] = useState<string | null>(null);
  const contenedor = useRef<HTMLDivElement>(null);
  const idPanel = useId();

  const cargarEstado = useCallback(async () => {
    try {
      setEstado(await pedirJson<EstadoApi>('/alertas/enfen'));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Sin datos del ENFEN.');
    }
  }, []);

  const cargarImpacto = useCallback(async () => {
    try {
      setImpacto(await pedirJson<Impacto>('/alertas/impacto'));
      setErrorImpacto(null);
    } catch (e) {
      setErrorImpacto(e instanceof Error ? e.message : 'No se pudo calcular el impacto.');
    }
  }, []);

  // El estado se consulta cada 20 s: en modo demo el cambio se ve casi en vivo.
  useEffect(() => {
    void cargarEstado();
    const id = setInterval(() => void cargarEstado(), INTERVALO_MS);
    // La vista "Alerta El Niño" avisa cuando cambia el estado para no esperar al siguiente sondeo.
    const alCambiar = () => void cargarEstado();
    window.addEventListener('cuotaflex-enfen', alCambiar);
    return () => {
      clearInterval(id);
      window.removeEventListener('cuotaflex-enfen', alCambiar);
    };
  }, [cargarEstado]);

  useEffect(() => {
    if (!abierto) return;
    void cargarImpacto();
    const id = setInterval(() => void cargarImpacto(), INTERVALO_MS);
    return () => clearInterval(id);
  }, [abierto, cargarImpacto, estado?.estado]);

  useEffect(() => {
    if (!abierto) return;
    const alTeclear = (e: KeyboardEvent) => e.key === 'Escape' && setAbierto(false);
    const alClic = (e: MouseEvent) => {
      if (contenedor.current && !contenedor.current.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener('keydown', alTeclear);
    document.addEventListener('mousedown', alClic);
    return () => {
      document.removeEventListener('keydown', alTeclear);
      document.removeEventListener('mousedown', alClic);
    };
  }, [abierto]);

  const tono = estado ? TONOS[estado.estado] : null;
  let detalle = error ? 'Sin datos: revisa la API' : 'Consultando el comunicado oficial…';
  if (estado) {
    detalle =
      estado.modo === 'demo'
        ? `Modo demo · fijado el ${fechaCorta(estado.desde)}`
        : `Comunicado N° ${estado.numero}, ${fechaCorta(estado.fecha)}`;
    if (estado.magnitud) detalle += ` · magnitud ${estado.magnitud}`;
  }
  const pctSaldo = impacto && impacto.cartera.saldo > 0 ? (impacto.total.saldo / impacto.cartera.saldo) * 100 : 0;

  return (
    <div className="enfen" ref={contenedor}>
      <style>{CSS}</style>
      <div
        className={`enfen-distintivo ${estado?.activo ? 'activo' : ''}`}
        style={tono ? { background: tono.fondo, color: tono.texto, borderColor: tono.punto } : undefined}
      >
        <button
          type="button"
          className="enfen-boton"
          aria-expanded={abierto}
          aria-controls={idPanel}
          disabled={!estado}
          title={estado ? 'Ver el impacto en la cartera' : (error ?? undefined)}
          onClick={() => setAbierto((v) => !v)}
        >
          <span className="enfen-punto" style={{ background: tono?.punto ?? '#9AA1A9' }} aria-hidden="true" />
          <span className="enfen-textos">
            <span className="enfen-etiqueta">{estado ? estado.etiqueta : 'ENFEN'}</span>
            <span className="enfen-detalle">{detalle}</span>
          </span>
          {estado?.desactualizado && (
            <span className="enfen-chip" title={estado.error ?? 'No se pudo actualizar la lectura.'}>
              desactualizado
            </span>
          )}
          {estado?.modo === 'demo' && <span className="enfen-chip">demo</span>}
        </button>
        {estado?.url_fuente && (
          <a className="enfen-fuente" href={estado.url_fuente} target="_blank" rel="noreferrer">
            Fuente ↗
          </a>
        )}
      </div>

      {abierto && estado && (
        <div id={idPanel} className="enfen-panel" role="region" aria-label="Impacto de la alerta en la cartera">
          <div className="enfen-panel-cab">
            <h2>Impacto en la cartera</h2>
            <button type="button" aria-label="Cerrar" onClick={() => setAbierto(false)}>
              ×
            </button>
          </div>
          {errorImpacto && <p className="enfen-aviso error">{errorImpacto}</p>}
          {impacto && (
            <>
              <p className={`enfen-aviso ${impacto.alivioHabilitado ? 'alivio' : ''}`}>{textoAlivio(impacto)}</p>
              <div className="enfen-kpis">
                <div>
                  <span>Préstamos con cláusula</span>
                  <b className="tab">
                    {entero(impacto.total.prestamos)} <small>de {entero(impacto.cartera.prestamos)}</small>
                  </b>
                </div>
                <div>
                  <span>Saldo cubierto</span>
                  <b className="tab">
                    {solesExacto(impacto.total.saldo)} <small>{pct1(pctSaldo)} de la cartera</small>
                  </b>
                </div>
                <div>
                  <span>Cuotas de alivio disponibles</span>
                  <b className="tab">{entero(impacto.total.cuotasAlivio)}</b>
                </div>
              </div>
              {impacto.grupos.length > 0 ? (
                <div className="enfen-tabla">
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Rubro</th>
                        <th scope="col">Región</th>
                        <th scope="col">Préstamos</th>
                        <th scope="col">Saldo</th>
                        <th scope="col">Cuotas de alivio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {impacto.grupos.map((g) => (
                        <tr key={`${g.rubro}|${g.region}`}>
                          <td>
                            <span className="enfen-rubro" style={{ background: infoRubro(g.rubro).color }} aria-hidden="true" />
                            {infoRubro(g.rubro).nombre}
                          </td>
                          <td>{g.region}</td>
                          <td className="tab">{entero(g.prestamos)}</td>
                          <td className="tab">{solesExacto(g.saldo)}</td>
                          <td className="tab">{entero(g.cuotasAlivio)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="enfen-vacio">
                  No hay préstamos activos con cláusula El Niño en el core. Regístralos desde la app del asesor o con{' '}
                  <code>POST /alertas/demo/cartera</code>.
                </p>
              )}
            </>
          )}
          <p className="enfen-pie">
            {estado.modo === 'demo'
              ? 'Modo demo: el estado lo fija POST /alertas/enfen/demo.'
              : `${estado.titulo} · ${estado.fuente} · leído ${fechaCorta(estado.obtenido_en)}`}
            {estado.advertencias.map((a) => (
              <span key={a} className="enfen-advertencia">
                {a}
              </span>
            ))}
          </p>
        </div>
      )}
    </div>
  );
}

const CSS = `
.enfen { position: relative; flex: none; }
.enfen-distintivo {
  display: flex; align-items: center; gap: 6px; border: 1px solid var(--cf-gris-200);
  border-radius: 999px; padding: 2px 12px 2px 2px; background: #fff;
}
.enfen-boton {
  display: flex; align-items: center; gap: 8px; background: none; border: none; color: inherit;
  padding: 3px 6px; border-radius: 999px; cursor: pointer; text-align: left;
}
.enfen-boton:disabled { cursor: default; }
.enfen-boton:hover:not(:disabled) .enfen-etiqueta { text-decoration: underline; }
.enfen-punto { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.enfen-distintivo.activo .enfen-punto { animation: enfen-pulso 1.8s ease-out infinite; }
@keyframes enfen-pulso {
  0% { box-shadow: 0 0 0 0 rgba(200, 16, 46, 0.55); }
  70% { box-shadow: 0 0 0 8px rgba(200, 16, 46, 0); }
  100% { box-shadow: 0 0 0 0 rgba(200, 16, 46, 0); }
}
@media (prefers-reduced-motion: reduce) { .enfen-distintivo.activo .enfen-punto { animation: none; } }
.enfen-textos { display: flex; flex-direction: column; line-height: 1.2; }
.enfen-etiqueta { font-size: 13px; font-weight: 700; white-space: nowrap; }
.enfen-detalle { font-size: 11.5px; opacity: 0.9; white-space: nowrap; }
.enfen-chip {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  border: 1px solid currentColor; border-radius: 999px; padding: 1px 6px; background: rgba(255, 255, 255, 0.65);
}
.enfen-fuente { font-size: 12px; font-weight: 600; color: inherit; white-space: nowrap; }
.enfen-panel {
  position: absolute; right: 0; top: calc(100% + 8px); z-index: 40; width: min(600px, 92vw);
  background: #fff; color: var(--cf-gris-900); border: 1px solid var(--cf-gris-200);
  border-radius: var(--cf-radio); box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16); padding: 14px 16px;
}
.enfen-panel-cab { display: flex; align-items: center; justify-content: space-between; }
.enfen-panel-cab h2 { margin: 0; font-size: 15px; }
.enfen-panel-cab button {
  background: none; border: none; font-size: 20px; line-height: 1; cursor: pointer; color: var(--cf-gris-600);
  padding: 0 4px; border-radius: 4px;
}
.enfen-aviso { margin: 8px 0 10px; font-size: 13px; color: var(--cf-gris-600); }
.enfen-aviso.alivio { color: #8E0B20; font-weight: 600; }
.enfen-aviso.error { color: var(--cf-rojo-osc); font-weight: 600; }
.enfen-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }
.enfen-kpis > div { border: 1px solid var(--cf-gris-200); border-radius: 8px; padding: 8px 10px; }
.enfen-kpis span { display: block; font-size: 11.5px; color: var(--cf-gris-600); }
.enfen-kpis b { font-size: 18px; }
.enfen-kpis small { display: block; font-size: 11.5px; font-weight: 500; color: var(--cf-gris-600); }
.enfen-tabla { max-height: 260px; overflow-y: auto; border: 1px solid var(--cf-gris-200); border-radius: 8px; }
.enfen-tabla table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.enfen-tabla th {
  position: sticky; top: 0; background: var(--cf-fondo); text-align: left; font-weight: 700;
  font-size: 11.5px; color: var(--cf-gris-600); padding: 6px 8px; border-bottom: 1px solid var(--cf-gris-200);
}
.enfen-tabla td { padding: 5px 8px; border-bottom: 1px solid var(--cf-gris-200); white-space: nowrap; }
.enfen-tabla tr:last-child td { border-bottom: none; }
.enfen-tabla th:nth-child(n + 3), .enfen-tabla td:nth-child(n + 3) { text-align: right; }
.enfen-rubro { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.enfen-vacio { font-size: 13px; color: var(--cf-gris-600); margin: 4px 0; }
.enfen-pie { margin: 10px 0 0; font-size: 11.5px; color: var(--cf-gris-600); }
.enfen-advertencia { display: block; margin-top: 4px; color: #6B4309; }
`;
