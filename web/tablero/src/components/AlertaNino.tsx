import { useCallback, useEffect, useState } from 'react';
import { pedir } from '../api';
import { infoRubro } from '../colores';
import { entero, solesExacto } from '../formato';

interface Estado {
  modo: 'oficial' | 'demo';
  estado: string;
  etiqueta: string;
  activo: boolean;
  magnitud: string | null;
  titulo: string | null;
  fecha: string | null;
  fuente: string;
}
interface Resumen {
  prestamos: number;
  saldo: number;
  cuotasAlivio: number;
}
interface Impacto {
  alivioHabilitado: boolean;
  mesesAlivio: number;
  rubrosExpuestos: string[];
  cartera: Resumen;
  total: Resumen;
  porRubro: (Resumen & { rubro: string })[];
}

const OPCIONES_DEMO: { estado: string; magnitud?: string; texto: string; ayuda: string }[] = [
  { estado: 'NO_ACTIVO', texto: 'Sin alerta', ayuda: 'Los clientes pagan su cuota normal.' },
  { estado: 'VIGILANCIA_NINO', texto: 'Vigilancia', ayuda: 'Aviso preventivo, todavía sin alivio.' },
  { estado: 'ALERTA_NINO', magnitud: 'moderada', texto: 'Alerta El Niño', ayuda: 'Se habilita el alivio de cuota.' },
];

const json = { method: 'POST', headers: { 'Content-Type': 'application/json' } };

/** Vista del supervisor: estado del ENFEN, qué cartera se afecta y (en demo) encender o apagar la alerta. */
export default function AlertaNino() {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [impacto, setImpacto] = useState<Impacto | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const [e, i] = await Promise.all([pedir<Estado>('/alertas/enfen'), pedir<Impacto>('/alertas/impacto')]);
      setEstado(e);
      setImpacto(i);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo leer el estado del ENFEN.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const accion = async (fn: () => Promise<unknown>) => {
    setOcupado(true);
    try {
      await fn();
      window.dispatchEvent(new Event('cuotaflex-enfen'));
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'La acción falló.');
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="vista">
      <div className="vista-cab">
        <div>
          <h1>Alerta El Niño</h1>
          <p className="vista-ayuda">Estado del comunicado ENFEN y préstamos que pueden pedir alivio de cuota.</p>
        </div>
      </div>
      {error && (
        <div className="banner-error" role="alert">
          <p>{error}</p>
        </div>
      )}

      {estado && (
        <section className="tarjeta-v">
          <div className="fila-v">
            <span className={`punto-estado ${estado.activo ? 'on' : estado.estado.startsWith('VIGILANCIA') ? 'vig' : ''}`} />
            <div>
              <div className="dato-grande">{estado.etiqueta}</div>
              <div className="vista-ayuda">
                {estado.modo === 'demo' ? 'Modo demo (fijado a mano)' : `Fuente: ${estado.fuente}`}
                {estado.fecha ? ` · ${estado.fecha}` : ''}
              </div>
            </div>
          </div>
          {estado.modo === 'demo' ? (
            <div className="opciones-estado" role="radiogroup" aria-label="Cambiar estado de la alerta (demo)">
              {OPCIONES_DEMO.map((o) => (
                <button
                  key={o.estado}
                  type="button"
                  role="radio"
                  aria-checked={estado.estado === o.estado}
                  disabled={ocupado}
                  onClick={() =>
                    void accion(() =>
                      pedir('/alertas/enfen/demo', { ...json, body: JSON.stringify({ estado: o.estado, magnitud: o.magnitud ?? null }) }),
                    )
                  }
                >
                  <b>{o.texto}</b>
                  <span>{o.ayuda}</span>
                </button>
              ))}
            </div>
          ) : (
            <button type="button" className="btn-primario" disabled={ocupado} onClick={() => void accion(() => pedir('/alertas/enfen/revisar', { method: 'POST' }))}>
              {ocupado ? 'Revisando…' : 'Revisar el comunicado oficial'}
            </button>
          )}
        </section>
      )}

      {impacto && (
        <section className="tarjeta-v">
          <h2 className="seccion-titulo">Impacto en la cartera</h2>
          <p className="vista-ayuda">
            {impacto.alivioHabilitado
              ? `Alivio habilitado: los clientes con cláusula pueden pagar la cuota mínima hasta ${impacto.mesesAlivio} veces.`
              : 'Sin alivio vigente. Esto es lo que se habilitaría si se declara la alerta.'}
          </p>
          <div className="kpis-v">
            <div>
              <span>Préstamos con cláusula</span>
              <b>
                {entero(impacto.total.prestamos)} de {entero(impacto.cartera.prestamos)}
              </b>
            </div>
            <div>
              <span>Saldo expuesto</span>
              <b>{solesExacto(impacto.total.saldo)}</b>
            </div>
            <div>
              <span>Cuotas de alivio disponibles</span>
              <b>{entero(impacto.total.cuotasAlivio)}</b>
            </div>
          </div>
          {impacto.porRubro.length > 0 && (
            <table className="tabla-v">
              <thead>
                <tr>
                  <th>Rubro</th>
                  <th className="num">Préstamos</th>
                  <th className="num">Saldo</th>
                  <th className="num">Cuotas de alivio</th>
                </tr>
              </thead>
              <tbody>
                {impacto.porRubro.map((r) => (
                  <tr key={r.rubro}>
                    <td>{infoRubro(r.rubro).nombre}</td>
                    <td className="num">{entero(r.prestamos)}</td>
                    <td className="num">{solesExacto(r.saldo)}</td>
                    <td className="num">{entero(r.cuotasAlivio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
