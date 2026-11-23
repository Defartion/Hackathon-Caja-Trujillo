import { TAMANOS } from '../api';
import type { Escenario, ParametroEditable, TamanoId } from '../api';
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
}

export default function PanelControles(p: Props) {
  const grupos: string[] = [];
  for (const x of p.parametros) if (!grupos.includes(x.grupo)) grupos.push(x.grupo);
  const activo = p.escenarios.find((e) => e.id === p.escenarioActivo);

  return (
    <aside className="panel" aria-label="Controles de la simulación">
      <div className="panel-scroll">
        <section className="seccion">
          <div className="seccion-cab">
            <h2 className="seccion-titulo">Escenarios</h2>
          </div>
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
        </section>

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
      </div>

      <div className="panel-fijo">
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

        <button type="button" className="btn-simular" disabled={p.corriendo} onClick={p.onSimular}>
          {p.corriendo ? `Simulando… ${p.segundos.toFixed(1)} s` : 'Simular'}
          {p.corriendo && <span className="progreso" style={{ width: `${p.progreso}%` }} />}
        </button>
      </div>
    </aside>
  );
}
