import { useState } from 'react';
import { pedir } from '../api';
import { BotonTema, IconoPanel } from '../apariencia';
import { cerrarSesion, iniciales, usuarioSesion } from '../sesion';

export type Vista = 'simular' | 'alerta' | 'avisos';

const ICONOS: Record<string, string> = {
  simular: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  alerta: 'M12 3l10 18H2zM12 10v5M12 18v.5',
  avisos: 'M4 5h16v11H8l-4 4z',
  reiniciar: 'M4 12a8 8 0 1 0 3-6.2M4 4v4h4',
  rol: 'M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3',
  salir: 'M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l4-4-4-4M14 12H4',
};

function Icono({ nombre }: { nombre: string }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONOS[nombre]} />
    </svg>
  );
}

// Fase 4 (FAQ del NEG-01): el alivio de El Niño en un crédito vigente es reprogramación, fuera del alcance.
// El Niño se evalúa como escenario adverso al diseñar el plan; la vista queda oculta sin borrar el código.
const MOSTRAR_CREDITO_VIGENTE = false;

const OPCIONES: { id: Vista; texto: string; ayuda: string }[] = [
  { id: 'simular', texto: 'Simular cartera', ayuda: 'Cuota fija vs. Thinku' },
  ...(MOSTRAR_CREDITO_VIGENTE ? [{ id: 'alerta' as Vista, texto: 'Alerta El Niño', ayuda: 'Estado y alivio de cuotas' }] : []),
  { id: 'avisos', texto: 'Avisos a clientes', ayuda: 'Recordatorios de pago' },
];


/** Menú del supervisor: lo que puede hacer este rol, a la izquierda. */
export default function NavSupervisor({
  vista, onVista, plegado, onPlegar,
}: { vista: Vista; onVista: (v: Vista) => void; plegado: boolean; onPlegar: () => void }) {
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
      <div className="nav-cab">
        <div className="nav-rol">Supervisor</div>
        <button
          type="button"
          className="nav-plegar"
          aria-expanded={!plegado}
          aria-label={plegado ? 'Mostrar el menú completo' : 'Plegar el menú'}
          title={plegado ? 'Mostrar el menú completo' : 'Plegar el menú'}
          onClick={onPlegar}
        >
          <IconoPanel abierto={!plegado} />
        </button>
      </div>
      <ul>
        {OPCIONES.map((o) => (
          <li key={o.id}>
            <button
              type="button"
              className={`nav-op ${vista === o.id ? 'activa' : ''}`}
              aria-current={vista === o.id ? 'page' : undefined}
              title={plegado ? o.texto : undefined}
              onClick={() => onVista(o.id)}
            >
              <Icono nombre={o.id} />
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
          <div className="nav-usuario" title={plegado ? usuario.nombre ?? 'Sesión con PIN' : undefined}>
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
          <button
            type="button"
            className="nav-sec"
            title={plegado ? 'Reiniciar demo' : undefined}
            onClick={() => {
              if (plegado) onPlegar(); // la confirmación necesita el ancho completo
              setConfirmar(true);
            }}
          >
            <Icono nombre="reiniciar" /> <span className="nav-sec__texto">Reiniciar demo</span>
          </button>
        )}
        {estado && <div className="nav-estado" role="status">{estado}</div>}
        {import.meta.env.BASE_URL !== '/' && (
          <a className="nav-sec" href="/" title={plegado ? 'Cambiar de rol' : undefined}>
            <Icono nombre="rol" /> <span className="nav-sec__texto">Cambiar de rol</span>
          </a>
        )}
        {usuario && (
          <button type="button" className="nav-sec" title={plegado ? 'Salir' : undefined} onClick={() => cerrarSesion('supervisor')}>
            <Icono nombre="salir" /> <span className="nav-sec__texto">Salir</span>
          </button>
        )}
      </div>
    </nav>
  );
}
