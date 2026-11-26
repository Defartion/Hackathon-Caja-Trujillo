import { useState } from 'react';
import { pedir } from '../api';
import { BotonTema } from '../apariencia';
import { cerrarSesion, iniciales, usuarioSesion } from '../sesion';

export type Vista = 'simular' | 'alerta' | 'avisos';

const ICONOS: Record<string, string> = {
  simular: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  alerta: 'M12 3l10 18H2zM12 10v5M12 18v.5',
  avisos: 'M4 5h16v11H8l-4 4z',
};

// Fase 4 (FAQ del NEG-01): el alivio de El Niño en un crédito vigente es reprogramación, fuera del alcance.
// El Niño se evalúa como escenario adverso al diseñar el plan; la vista queda oculta sin borrar el código.
const MOSTRAR_CREDITO_VIGENTE = false;

const OPCIONES: { id: Vista; texto: string; ayuda: string }[] = [
  { id: 'simular', texto: 'Simular cartera', ayuda: 'Cuota fija vs. CuotaFlex' },
  ...(MOSTRAR_CREDITO_VIGENTE ? [{ id: 'alerta' as Vista, texto: 'Alerta El Niño', ayuda: 'Estado y alivio de cuotas' }] : []),
  { id: 'avisos', texto: 'Avisos a clientes', ayuda: 'Recordatorios de pago' },
];


/** Menú del supervisor: lo que puede hacer este rol, a la izquierda. */
export default function NavSupervisor({ vista, onVista }: { vista: Vista; onVista: (v: Vista) => void }) {
  const [confirmar, setConfirmar] = useState(false);
  const [estado, setEstado] = useState<string | null>(null);

  const reiniciar = async () => {
    setEstado('Reiniciando…');
    try {
      const r = await pedir<{ prestamos: number }>('/admin/reset?sembrar=true', { method: 'POST' });
      setEstado(`Listo: demo con ${r.prestamos} préstamos.`);
    } catch (e) {
      setEstado(e instanceof Error ? e.message : 'No se pudo reiniciar.');
    } finally {
      setConfirmar(false);
    }
  };

  const usuario = usuarioSesion('supervisor');

  return (
    <nav className="nav-sup" aria-label="Menú del supervisor">
      <div className="nav-rol">Supervisor</div>
      <ul>
        {OPCIONES.map((o) => (
          <li key={o.id}>
            <button type="button" className={`nav-op ${vista === o.id ? 'activa' : ''}`} aria-current={vista === o.id ? 'page' : undefined} onClick={() => onVista(o.id)}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d={ICONOS[o.id]} />
              </svg>
              <span className="nav-textos">
                <span className="t">{o.texto}</span>
                <span className="a">{o.ayuda}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="nav-pie">
        {usuario && (
          <div className="nav-usuario">
            <span className={`nav-usuario__avatar ${usuario.nombre ? '' : 'pin'}`} aria-hidden="true">
              {iniciales(usuario.nombre)}
            </span>
            <span className="nav-usuario__datos">
              <b>{usuario.nombre ?? 'Sesión con PIN'}</b>
              <span>Supervisor</span>
            </span>
          </div>
        )}
        <BotonTema className="nav-sec" texto />
        {confirmar ? (
          <div className="confirmar">
            <span>¿Borrar lo registrado y volver a los datos de demo?</span>
            <div>
              <button type="button" className="btn-peligro" onClick={() => void reiniciar()}>
                Sí, reiniciar
              </button>
              <button type="button" className="btn-texto" onClick={() => setConfirmar(false)}>
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="nav-sec" onClick={() => setConfirmar(true)}>
            Reiniciar demo
          </button>
        )}
        {estado && <div className="nav-estado" role="status">{estado}</div>}
        {import.meta.env.BASE_URL !== '/' && (
          <a className="nav-sec" href="/">
            Cambiar de rol
          </a>
        )}
        {usuario && (
          <button type="button" className="nav-sec" onClick={() => cerrarSesion('supervisor')}>
            Salir
          </button>
        )}
      </div>
    </nav>
  );
}
