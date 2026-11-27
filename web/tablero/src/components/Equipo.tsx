import { FormEvent, useCallback, useEffect, useState } from 'react';
import { pedir } from '../api';
import { usuarioSesion } from '../sesion';

type Rol = 'asesor' | 'supervisor';

interface Persona {
  usuario: string;
  nombre: string;
  rol: Rol;
  activo: boolean;
  creado: string | null;
  creado_por: string | null;
  actualizado: string | null;
}

interface RespuestaEquipo {
  almacen: { tipo: string; duradero: boolean };
  pin_general: boolean;
  personas: Persona[];
}

interface LlaveNueva {
  persona: Persona;
  pin: string;
  motivo: 'creada' | 'pin';
}

const json = (cuerpo: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(cuerpo),
});

const ROL_TEXTO: Record<Rol, string> = { asesor: 'Asesor', supervisor: 'Supervisor' };

/** Dónde entra cada rol: en el despliegue, la app del mismo sitio; en local, su puerto de Vite. */
function enlaceApp(rol: Rol): string {
  if (import.meta.env.BASE_URL !== '/') return `${window.location.origin}/${rol === 'asesor' ? 'asesor' : 'tablero'}/`;
  return rol === 'asesor' ? 'http://localhost:5173/' : 'http://localhost:5175/';
}

const fecha = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';

/**
 * Fase 4: cada asesor y supervisor tiene su propia llave (usuario + PIN de 6 dígitos).
 * El supervisor la crea aquí, la entrega una sola vez y puede cambiar el PIN o desactivar a la persona;
 * eso corta sus sesiones abiertas sin tocar a nadie más.
 */
export default function Equipo() {
  const [datos, setDatos] = useState<RespuestaEquipo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nombre, setNombre] = useState('');
  const [rol, setRol] = useState<Rol>('asesor');
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [nueva, setNueva] = useState<LlaveNueva | null>(null);
  const [confirmar, setConfirmar] = useState<{ usuario: string; accion: 'pin' | 'desactivar' } | null>(null);
  const [copiado, setCopiado] = useState(false);
  const yo = usuarioSesion('supervisor')?.usuario ?? null;

  const cargar = useCallback(async () => {
    try {
      setDatos(await pedir<RespuestaEquipo>('/equipo'));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo leer el equipo.');
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function ejecutar(clave: string, fn: () => Promise<void>) {
    setOcupado(clave);
    setError(null);
    try {
      await fn();
      await cargar();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'La acción falló.');
    } finally {
      setOcupado(null);
      setConfirmar(null);
    }
  }

  function agregar(e: FormEvent) {
    e.preventDefault();
    if (nombre.trim().length < 3) {
      setError('Escribe el nombre completo de la persona.');
      return;
    }
    void ejecutar('crear', async () => {
      const r = await pedir<{ persona: Persona; pin: string }>('/equipo', json({ nombre: nombre.trim(), rol }));
      setNueva({ ...r, motivo: 'creada' });
      setNombre('');
    });
  }

  const nuevoPin = (p: Persona) =>
    ejecutar(`pin:${p.usuario}`, async () => {
      const r = await pedir<{ persona: Persona; pin: string }>(`/equipo/${encodeURIComponent(p.usuario)}/pin`, {
        method: 'POST',
      });
      setNueva({ ...r, motivo: 'pin' });
    });

  const cambiarEstado = (p: Persona, activo: boolean) =>
    ejecutar(`estado:${p.usuario}`, async () => {
      await pedir(`/equipo/${encodeURIComponent(p.usuario)}/estado`, json({ activo }));
    });

  const mensaje = nueva
    ? `Hola ${nueva.persona.nombre.split(/\s+/)[0]}: tu acceso a Thinku como ${ROL_TEXTO[nueva.persona.rol].toLowerCase()} ` +
      `es usuario ${nueva.persona.usuario} y PIN ${nueva.pin}. Entra en ${enlaceApp(nueva.persona.rol)} ` +
      'con "Entrar con mi usuario y PIN". No lo compartas.'
    : '';

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(mensaje);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setCopiado(false);
    }
  };

  const activos = datos?.personas.filter((p) => p.activo).length ?? 0;

  return (
    <div className="vista">
      <div className="vista-cab">
        <div>
          <h1>Equipo</h1>
          <p className="vista-ayuda">
            Cada asesor y supervisor entra con su propio usuario y PIN. Si alguien deja el equipo, lo desactivas aquí
            sin cambiar la llave de nadie más.
          </p>
        </div>
      </div>

      {datos && !datos.almacen.duradero && (
        <div className="banner-aviso" role="status">
          <strong>Las llaves aún no son permanentes.</strong> Se guardan en un almacenamiento temporal y se borran cuando
          el servidor se reinicia. Para que duren, conecta Upstash Redis (gratis) en Vercel → Storage.
        </div>
      )}
      {error && (
        <div className="banner-error" role="alert">
          <p>{error}</p>
        </div>
      )}

      {nueva && (
        <section className="tarjeta-v llave-nueva" aria-labelledby="llave-nueva-titulo">
          <h2 id="llave-nueva-titulo" className="seccion-titulo">
            {nueva.motivo === 'creada' ? `Llave de ${nueva.persona.nombre}` : `PIN nuevo de ${nueva.persona.nombre}`}
          </h2>
          <div className="llave-nueva__datos">
            <div>
              <span>Usuario</span>
              <b>{nueva.persona.usuario}</b>
            </div>
            <div>
              <span>PIN</span>
              <b className="llave-nueva__pin">{`${nueva.pin.slice(0, 3)} ${nueva.pin.slice(3)}`}</b>
            </div>
            <div>
              <span>Entra en</span>
              <b>App de {ROL_TEXTO[nueva.persona.rol].toLowerCase()}</b>
            </div>
          </div>
          <p className="vista-ayuda">
            Entrégaselo ahora: por seguridad, el PIN no se vuelve a mostrar. Si lo pierde, genera uno nuevo.
          </p>
          <div className="acciones-v">
            <a className="btn-primario" href={`https://wa.me/?text=${encodeURIComponent(mensaje)}`} target="_blank" rel="noreferrer">
              Enviar por WhatsApp
            </a>
            <button type="button" className="btn-sec" onClick={copiar}>
              {copiado ? '✓ Copiado' : 'Copiar mensaje'}
            </button>
            <button type="button" className="btn-sec" onClick={() => setNueva(null)}>
              Listo, ya lo entregué
            </button>
          </div>
        </section>
      )}

      <section className="tarjeta-v" aria-labelledby="equipo-agregar">
        <h2 id="equipo-agregar" className="seccion-titulo">Agregar a una persona</h2>
        <form className="equipo-form" onSubmit={agregar} noValidate>
          <label className="equipo-campo">
            Nombre completo
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej.: Ana Torres Rojas…"
              autoComplete="off"
            />
          </label>
          <fieldset className="equipo-rol">
            <legend>Rol</legend>
            {(['asesor', 'supervisor'] as Rol[]).map((r) => (
              <label key={r}>
                <input type="radio" name="rol" value={r} checked={rol === r} onChange={() => setRol(r)} />
                {ROL_TEXTO[r]}
              </label>
            ))}
          </fieldset>
          <button type="submit" className="btn-primario" disabled={ocupado === 'crear'}>
            {ocupado === 'crear' ? 'Creando…' : 'Crear su llave'}
          </button>
        </form>
      </section>

      <section className="tarjeta-v" aria-labelledby="equipo-lista">
        <h2 id="equipo-lista" className="seccion-titulo">
          Personas con llave {datos && <span className="vista-ayuda">· {activos} activas</span>}
        </h2>
        {!datos ? (
          <p className="vista-ayuda">Cargando…</p>
        ) : datos.personas.length === 0 ? (
          <p className="vista-ayuda">
            Todavía nadie tiene llave personal. Agrega a tu primer asesor o supervisor arriba.
          </p>
        ) : (
          <table className="tabla-v">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Desde</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {datos.personas.map((p) => {
                const pide = confirmar?.usuario === p.usuario ? confirmar.accion : null;
                return (
                  <tr key={p.usuario} className={p.activo ? '' : 'inactiva'}>
                    <td>{p.nombre}</td>
                    <td>
                      <code>{p.usuario}</code>
                      {p.usuario === yo && <span className="vista-ayuda"> (tú)</span>}
                    </td>
                    <td>{ROL_TEXTO[p.rol]}</td>
                    <td>
                      <span className={`chip-estado ${p.activo ? 'ok' : 'pend'}`}>{p.activo ? 'Activo' : 'Desactivado'}</span>
                    </td>
                    <td>{fecha(p.creado)}</td>
                    <td className="equipo-acciones">
                      {pide ? (
                        <span className="confirmar-linea">
                          {pide === 'pin' ? 'El PIN actual dejará de servir.' : 'Perderá el acceso al momento.'}
                          <button
                            type="button"
                            className="btn-peligro"
                            disabled={ocupado !== null}
                            onClick={() => (pide === 'pin' ? void nuevoPin(p) : void cambiarEstado(p, false))}
                          >
                            {pide === 'pin' ? 'Sí, cambiar PIN' : 'Sí, desactivar'}
                          </button>
                          <button type="button" className="btn-texto" onClick={() => setConfirmar(null)}>
                            Cancelar
                          </button>
                        </span>
                      ) : (
                        <>
                          {p.activo && (
                            <button type="button" className="btn-sec" disabled={ocupado !== null} onClick={() => setConfirmar({ usuario: p.usuario, accion: 'pin' })}>
                              Nuevo PIN
                            </button>
                          )}
                          {p.activo ? (
                            p.usuario !== yo && (
                              <button type="button" className="btn-sec" disabled={ocupado !== null} onClick={() => setConfirmar({ usuario: p.usuario, accion: 'desactivar' })}>
                                Desactivar
                              </button>
                            )
                          ) : (
                            <button type="button" className="btn-sec" disabled={ocupado !== null} onClick={() => void cambiarEstado(p, true)}>
                              Activar
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {datos?.pin_general && (
        <p className="vista-ayuda">
          El PIN general de cada rol sigue activo para la demostración. Cuando todo el equipo tenga su llave, se puede
          apagar con la variable CUOTAFLEX_PIN_GENERAL=0 en Vercel.
        </p>
      )}
    </div>
  );
}
