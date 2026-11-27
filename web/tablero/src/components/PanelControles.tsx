import { ReactNode, useState } from 'react';
import { TAMANOS } from '../api';
import type { Escenario, ParametroEditable, TamanoId } from '../api';
import { IconoPanel, useGuardado } from '../apariencia';
import Deslizador from './Deslizador';

interface Props {
  parametros: ParametroEditable[];
  escenarios: Escenario[];
  valores: Record<string, number>;
  escenarioActivo: string | null;
  personalizado: boolean;
  replanificar: boolean;
  tamano: TamanoId;
  corriendo: boolean;
  segundos: number;
  progreso: number;
  onEscenario: (e: Escenario) => void;
  onCambio: (ruta: string, valor: number) => void;
  onRestablecer: () => void;
  onModo: (replanificar: boolean) => void;
  onTamano: (t: TamanoId) => void;
  onSimular: () => void;
  /** Panel reducido a una columna angosta para dar más espacio a los resultados. */
  plegado: boolean;
  onPlegar: () => void;
}

/** Título de una sección que se abre y se cierra; cerrada, muestra un resumen a la derecha. */
function Acordeon({ abierto, onClick, resumen, children }: {
  abierto: boolean; onClick: () => void; resumen?: string; children: ReactNode;
}) {
  return (
    <button type="button" className="panel-acordeon" aria-expanded={abierto} onClick={onClick}>
      <svg className="panel-acordeon__flecha" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M6 9l6 6 6-6" />
      </svg>
      <span className="panel-acordeon__titulo">{children}</span>
      {!abierto && resumen && <span className="panel-acordeon__resumen">{resumen}</span>}
    </button>
  );
}

function BotonPlegar({ plegado, onPlegar }: { plegado: boolean; onPlegar: () => void }) {
  const texto = plegado ? 'Mostrar los controles' : 'Plegar los controles';
  return (
    <button type="button" className="panel-plegar" aria-expanded={!plegado} aria-label={texto} title={texto} onClick={onPlegar}>
      <IconoPanel abierto={!plegado} />
    </button>
  );
}

export default function PanelControles(p: Props) {
  const grupos: string[] = [];
  for (const x of p.parametros) if (!grupos.includes(x.grupo)) grupos.push(x.grupo);
  const activo = p.escenarios.find((e) => e.id === p.escenarioActivo);
  const [avanzado, setAvanzado] = useState(false);
  const abierto = avanzado || p.personalizado;
  const [escenarios, setEscenarios] = useGuardado('cuotaflex.tablero.escenarios', 'abierto', ['abierto', 'cerrado'] as const);
  const verEscenarios = escenarios === 'abierto';
  const nombreActual = activo ? activo.nombre : p.personalizado ? 'Personalizado' : 'Base';
  const textoSimular = p.corriendo ? `Simulando… ${p.segundos.toFixed(1)} s` : p.personalizado ? 'Simular con mis ajustes' : 'Volver a simular';

  if (p.plegado) {
    return (
      <aside className="panel panel--plegado" aria-label="Controles de la simulación">
        <BotonPlegar plegado onPlegar={p.onPlegar} />
        <button type="button" className="panel-rotulo" onClick={p.onPlegar} title="Mostrar los controles">
          <span className="panel-rotulo__texto">Escenario: {nombreActual}</span>
        </button>
        <button
          type="button"
          className="btn-simular-mini"
          disabled={p.corriendo}
          aria-label={textoSimular}
          title={textoSimular}
          onClick={p.onSimular}
        >
          {p.corriendo ? (
            <span className="btn-simular-mini__giro" aria-hidden="true" />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>
          )}
        </button>
      </aside>
    );
  }

  return (
    <aside className="panel" aria-label="Controles de la simulación">
      <div className="panel-scroll">
        <section className="seccion">
          <div className="seccion-cab panel-cab">
            <h2 className="seccion-titulo">
              <Acordeon abierto={verEscenarios} onClick={() => setEscenarios(verEscenarios ? 'cerrado' : 'abierto')} resumen={nombreActual}>
                1. Elige un escenario
              </Acordeon>
            </h2>
            <BotonPlegar plegado={false} onPlegar={p.onPlegar} />
          </div>
          {verEscenarios && (
          <>
          <p className="esc-ayuda">Cada botón simula la cartera al instante.</p>
          <div className="escenarios">
            {p.escenarios.map((e) => (
              <button
                key={e.id}
                type="button"
                className="btn-esc"
                aria-pressed={e.id === p.escenarioActivo}
                disabled={p.corriendo}
                onClick={() => p.onEscenario(e)}
              >
                {e.nombre}
              </button>
            ))}
          </div>
          <p className="esc-desc">
            {activo
              ? activo.descripcion
              : p.personalizado
                ? 'Personalizado: ajustaste parámetros respecto a la base.'
                : 'Parámetros base, sin cambios.'}
          </p>
          </>
          )}
        </section>

        <section className="seccion">
          <h2 className="seccion-titulo">
            <Acordeon abierto={abierto} onClick={() => setAvanzado(!abierto)} resumen={p.personalizado ? 'Con cambios' : 'Opcional'}>
              2. Ajustes avanzados
            </Acordeon>
          </h2>
          {!abierto && (
            <p className="esc-ayuda">
              Cambia reglas de flexibilidad, capacidad de pago, modo y tamaño de la simulación.
            </p>
          )}
        </section>

        {abierto && (
        <section className="seccion">
          <div className="seccion-cab">
            <h2 className="seccion-titulo">Parámetros</h2>
            <button type="button" className="btn-texto" disabled={p.corriendo} onClick={p.onRestablecer}>
              Restablecer
            </button>
          </div>
          {grupos.map((g) => (
            <div key={g}>
              <h3 className="grupo-titulo">{g}</h3>
              {p.parametros
                .filter((x) => x.grupo === g)
                .map((x) => (
                  <Deslizador
                    key={x.ruta}
                    param={x}
                    valor={p.valores[x.ruta] ?? x.valor}
                    deshabilitado={p.corriendo}
                    onCambio={p.onCambio}
                  />
                ))}
            </div>
          ))}
        </section>
        )}
        {abierto && (
          <section className="seccion avanzado-ejecucion">
        <div>
          <div className="etiqueta-ctrl" id="lbl-modo">
            Modo
          </div>
          <div className="segmentado" role="radiogroup" aria-labelledby="lbl-modo">
            <button
              type="button"
              role="radio"
              aria-checked={p.replanificar}
              disabled={p.corriendo}
              onClick={() => p.onModo(true)}
            >
              Completo
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={!p.replanificar}
              disabled={p.corriendo}
              onClick={() => p.onModo(false)}
            >
              Solo cronograma
            </button>
          </div>
          <div className="leyenda-ctrl">
            {p.replanificar ? 'Completo: ajusta monto y plazo' : 'Solo cronograma: mantiene monto y plazo pedidos'}
          </div>
        </div>

        <div>
          <div className="etiqueta-ctrl" id="lbl-tam">
            Tamaño
          </div>
          <div className="segmentado" role="radiogroup" aria-labelledby="lbl-tam">
            {(Object.keys(TAMANOS) as TamanoId[]).map((t) => (
              <button
                key={t}
                type="button"
                role="radio"
                aria-checked={p.tamano === t}
                disabled={p.corriendo}
                onClick={() => p.onTamano(t)}
              >
                {TAMANOS[t].nombre}
              </button>
            ))}
          </div>
          <div className="leyenda-ctrl">
            {TAMANOS[p.tamano].n_clientes} créditos × {TAMANOS[p.tamano].n_escenarios} escenarios
          </div>
        </div>

          </section>
        )}
      </div>

      <div className="panel-fijo">
        <button type="button" className="btn-simular" disabled={p.corriendo} onClick={p.onSimular}>
          {textoSimular}
          {p.corriendo && <span className="progreso" style={{ width: `${p.progreso}%` }} />}
        </button>
      </div>
    </aside>
  );
}
