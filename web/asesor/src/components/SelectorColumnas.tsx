import { useEffect, useId, useRef, useState } from "react";

export interface OpcionColumna {
  id: string;
  texto: string;
  /** No se puede ocultar (la columna que identifica la fila). */
  fija?: boolean;
}

export interface VistaColumnas {
  id: string;
  texto: string;
  columnas: string[];
}

interface Props {
  columnas: OpcionColumna[];
  visibles: string[];
  vistas: VistaColumnas[];
  porDefecto: string[];
  densidad: "comoda" | "compacta";
  onColumnas: (ids: string[]) => void;
  onDensidad: (d: "comoda" | "compacta") => void;
}

const mismas = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

/** Botón "Columnas": vistas rápidas, una casilla por columna y la altura de las filas. */
export default function SelectorColumnas({ columnas, visibles, vistas, porDefecto, densidad, onColumnas, onDensidad }: Props) {
  const [abierto, setAbierto] = useState(false);
  const caja = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!abierto) return;
    panel.current?.querySelector<HTMLElement>("button, input:not(:disabled)")?.focus();
    const fuera = (e: MouseEvent) => {
      if (!caja.current?.contains(e.target as Node)) setAbierto(false);
    };
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAbierto(false);
        boton.current?.focus();
      }
    };
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  const alternar = (col: string) => {
    const nuevas = visibles.includes(col) ? visibles.filter((c) => c !== col) : [...visibles, col];
    // Se guardan en el orden de la tabla, no en el orden en que se marcaron.
    onColumnas(columnas.map((c) => c.id).filter((c) => nuevas.includes(c)));
  };
  const opcionales = columnas.filter((c) => !c.fija).length;
  const mostradas = columnas.filter((c) => !c.fija && visibles.includes(c.id)).length;

  return (
    <div className="selector-columnas" ref={caja}>
      <button
        ref={boton}
        type="button"
        className="btn"
        aria-expanded={abierto}
        aria-controls={abierto ? id : undefined}
        aria-haspopup="dialog"
        onClick={() => setAbierto(!abierto)}
      >
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"
          strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
          <rect x="3" y="4" width="18" height="16" rx="2.5" />
          <path d="M9 4v16M15 4v16" />
        </svg>
        Columnas
        <span className="selector-columnas__cuenta">{mostradas}/{opcionales}</span>
      </button>
      {abierto && (
        <div className="selector-columnas__panel" role="dialog" aria-label="Columnas de la tabla" id={id} ref={panel}>
          <div className="selector-columnas__bloque">
            <span className="selector-columnas__titulo" id={`${id}-vistas`}>Vistas rápidas</span>
            <div className="selector-columnas__vistas" role="group" aria-labelledby={`${id}-vistas`}>
              {vistas.map((v) => (
                <button
                  key={v.id}
                  type="button"
                  className="chip"
                  aria-pressed={mismas(v.columnas, visibles)}
                  onClick={() => onColumnas(v.columnas)}
                >
                  {v.texto}
                </button>
              ))}
            </div>
          </div>
          <fieldset className="selector-columnas__bloque selector-columnas__lista">
            <legend className="selector-columnas__titulo">Columnas visibles</legend>
            <div className="selector-columnas__casillas">
              {columnas.map((c) => (
                <label key={c.id} className={c.fija ? "fija" : undefined}>
                  <input
                    type="checkbox"
                    checked={c.fija || visibles.includes(c.id)}
                    disabled={c.fija}
                    onChange={() => alternar(c.id)}
                  />
                  {c.texto}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="selector-columnas__bloque">
            <span className="selector-columnas__titulo" id={`${id}-filas`}>Filas</span>
            <div className="segmentos" role="radiogroup" aria-labelledby={`${id}-filas`}>
              {([["comoda", "Cómodas"], ["compacta", "Compactas"]] as const).map(([valor, texto]) => (
                <button key={valor} type="button" role="radio" aria-checked={densidad === valor} onClick={() => onDensidad(valor)}>
                  {texto}
                </button>
              ))}
            </div>
          </div>
          <div className="selector-columnas__pie">
            <button
              type="button"
              className="btn-enlace"
              disabled={mismas(porDefecto, visibles) && densidad === "comoda"}
              onClick={() => {
                onColumnas(porDefecto);
                onDensidad("comoda");
              }}
            >
              Restablecer
            </button>
            <button type="button" className="btn" onClick={() => { setAbierto(false); boton.current?.focus(); }}>
              Listo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
