import { useCallback, useEffect, useState } from 'react';
import { pedir } from '../api';

interface Aviso {
  id: number;
  canal: string;
  destinatario: number;
  plantilla: string;
  texto: string;
  fecha: string;
  estado: string;
}

const PLANTILLA: Record<string, string> = {
  recordatorio_cuota: 'Recordatorio de cuota',
  temporada_baja: 'Temporada baja',
  aplazamiento_confirmado: 'Aplazamiento confirmado',
};

/** Vista del supervisor: avisos a clientes (SMS o WhatsApp simulados; no sale ningún mensaje real). */
export default function Avisos() {
  const [avisos, setAvisos] = useState<Aviso[] | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setAvisos((await pedir<Aviso[]>('/alertas/notificaciones')).slice().reverse());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron leer los avisos.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const accion = async (fn: () => Promise<string>) => {
    setOcupado(true);
    setMensaje(null);
    try {
      setMensaje(await fn());
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'La acción falló.');
    } finally {
      setOcupado(false);
    }
  };

  const pendientes = (avisos ?? []).filter((a) => a.estado === 'pendiente').length;

  return (
    <div className="vista">
      <div className="vista-cab">
        <div>
          <h1>Avisos a clientes</h1>
          <p className="vista-ayuda">Recordatorios de pago y avisos de temporada baja. El envío es simulado.</p>
        </div>
        <div className="acciones-v">
          <button
            type="button"
            className="btn-sec"
            disabled={ocupado}
            onClick={() =>
              void accion(async () => {
                const r = await pedir<{ generadas: unknown[] }>('/alertas/notificaciones/generar-recordatorios', { method: 'POST' });
                return r.generadas.length ? `Se prepararon ${r.generadas.length} avisos nuevos.` : 'No hay avisos nuevos para hoy.';
              })
            }
          >
            1. Preparar avisos de hoy
          </button>
          <button
            type="button"
            className="btn-primario"
            disabled={ocupado || pendientes === 0}
            onClick={() =>
              void accion(async () => {
                const r = await pedir<{ enviadas: number }>('/alertas/notificaciones/enviar', { method: 'POST' });
                return `Se enviaron ${r.enviadas} avisos (simulado).`;
              })
            }
          >
            2. Enviar {pendientes > 0 ? `${pendientes} pendientes` : 'pendientes'}
          </button>
        </div>
      </div>
      {mensaje && <div className="banner-ok" role="status">{mensaje}</div>}
      {error && (
        <div className="banner-error" role="alert">
          <p>{error}</p>
        </div>
      )}
      <section className="tarjeta-v">
        {!avisos ? (
          <p className="vista-ayuda">Cargando…</p>
        ) : avisos.length === 0 ? (
          <p className="vista-ayuda">Todavía no hay avisos. Pulsa "Preparar avisos de hoy".</p>
        ) : (
          <table className="tabla-v">
            <thead>
              <tr>
                <th>Préstamo</th>
                <th>Tipo</th>
                <th>Mensaje</th>
                <th>Canal</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {avisos.map((a) => (
                <tr key={a.id}>
                  <td>#{a.destinatario}</td>
                  <td>{PLANTILLA[a.plantilla] ?? a.plantilla}</td>
                  <td className="texto-aviso">{a.texto}</td>
                  <td>{a.canal === 'whatsapp' ? 'WhatsApp' : 'SMS'}</td>
                  <td>
                    <span className={`chip-estado ${a.estado === 'pendiente' ? 'pend' : 'ok'}`}>
                      {a.estado === 'pendiente' ? 'Pendiente' : 'Enviado'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
