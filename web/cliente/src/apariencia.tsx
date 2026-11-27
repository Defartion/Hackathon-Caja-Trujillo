// Tema claro u oscuro, común a las tres apps (copia idéntica; tests/test_web_tema.py lo verifica).
// La elección se guarda en localStorage ("cuotaflex.tema": "claro" | "oscuro"); sin elección se sigue al
// sistema. Un script en línea de cada index.html aplica el tema antes de pintar para que la página no parpadee,
// y al imprimir se usa siempre el tema claro.
import { ReactNode, useCallback, useEffect, useState } from "react";

export type Preferencia = "claro" | "oscuro" | "sistema";
export type Tema = "claro" | "oscuro";

const CLAVE = "cuotaflex.tema";
const EVENTO = "cuotaflex-tema";
const CONSULTA = "(prefers-color-scheme: dark)";
const COLOR_BARRA: Record<Tema, string> = { claro: "#F2F4F7", oscuro: "#0D121C" };

function delSistema(): Tema {
  try {
    return window.matchMedia(CONSULTA).matches ? "oscuro" : "claro";
  } catch {
    return "claro";
  }
}

export function leerPreferencia(): Preferencia {
  try {
    const valor = localStorage.getItem(CLAVE);
    return valor === "claro" || valor === "oscuro" ? valor : "sistema";
  } catch {
    return "sistema";
  }
}

const resolver = (p: Preferencia): Tema => (p === "sistema" ? delSistema() : p);

function aplicar(tema: Tema) {
  const raiz = document.documentElement;
  raiz.dataset.tema = tema;
  raiz.style.colorScheme = tema === "oscuro" ? "dark" : "light";
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", COLOR_BARRA[tema]);
}

export function cambiarTema(p: Preferencia) {
  try {
    if (p === "sistema") localStorage.removeItem(CLAVE);
    else localStorage.setItem(CLAVE, p);
  } catch {
    /* sin almacenamiento: el tema dura lo que la pestaña */
  }
  aplicar(resolver(p));
  window.dispatchEvent(new Event(EVENTO));
}

if (typeof window !== "undefined") {
  aplicar(resolver(leerPreferencia()));
  // El papel no tiene modo oscuro: se imprime (o se guarda en PDF) con el tema claro.
  window.addEventListener("beforeprint", () => aplicar("claro"));
  window.addEventListener("afterprint", () => aplicar(resolver(leerPreferencia())));
}

/** Preferencia guardada y tema que se ve; se actualiza si cambia en otra pestaña o en el sistema. */
export function useTema(): { preferencia: Preferencia; tema: Tema } {
  const [preferencia, setPreferencia] = useState<Preferencia>(leerPreferencia);
  const [sistema, setSistema] = useState<Tema>(delSistema);

  useEffect(() => {
    const consulta = window.matchMedia(CONSULTA);
    const alSistema = () => {
      setSistema(consulta.matches ? "oscuro" : "claro");
      if (leerPreferencia() === "sistema") aplicar(consulta.matches ? "oscuro" : "claro");
    };
    const alCambiar = () => {
      const p = leerPreferencia();
      setPreferencia(p);
      aplicar(resolver(p));
    };
    const alAlmacenar = (e: StorageEvent) => {
      if (e.key === CLAVE || e.key === null) alCambiar();
    };
    consulta.addEventListener("change", alSistema);
    window.addEventListener(EVENTO, alCambiar);
    window.addEventListener("storage", alAlmacenar);
    return () => {
      consulta.removeEventListener("change", alSistema);
      window.removeEventListener(EVENTO, alCambiar);
      window.removeEventListener("storage", alAlmacenar);
    };
  }, []);

  return { preferencia, tema: preferencia === "sistema" ? sistema : preferencia };
}

/**
 * Preferencia de pantalla guardada en localStorage (menú plegado, columnas visibles, densidad…).
 * `validos` descarta valores viejos o ajenos que hubiera en el almacenamiento.
 */
export function useGuardado<T extends string>(clave: string, inicial: T, validos?: readonly T[]): [T, (valor: T) => void] {
  const [valor, setValor] = useState<T>(() => {
    try {
      const guardado = localStorage.getItem(clave);
      return guardado !== null && (!validos || (validos as readonly string[]).includes(guardado)) ? (guardado as T) : inicial;
    } catch {
      return inicial;
    }
  });
  const guardar = useCallback((nuevo: T) => {
    setValor(nuevo);
    try {
      localStorage.setItem(clave, nuevo);
    } catch {
      /* sin almacenamiento: dura lo que la pestaña */
    }
  }, [clave]);
  return [valor, guardar];
}

/** Icono de los botones que pliegan o despliegan una columna (menú lateral, panel de controles). */
export function IconoPanel({ abierto }: { abierto: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <rect x="3" y="4" width="18" height="16" rx="2.5" />
      <path d="M9.5 4v16" />
      <path d={abierto ? "M16 10l-2 2 2 2" : "M14 10l2 2-2 2"} />
    </svg>
  );
}

// Colores de datos que tema.css cambia en el tema oscuro (ver las reglas :is(.recharts-wrapper, .cf-graf)).
// colorTema() devuelve la variable equivalente para usarla en estilos en línea (muestras de leyendas en HTML);
// en el tema claro la variable vale lo mismo que el color original.
const VARIABLE_DE_COLOR: Record<string, string> = {
  "#0B5CAD": "var(--cf-graf-flex)",
  "#8792A6": "var(--cf-graf-fija)",
  "#B7791F": "var(--cf-ambar)",
  "#C8102E": "var(--cf-graf-tope)",
  "#8E0B20": "var(--cf-graf-supera)",
  "#E1ECF8": "var(--cf-graf-cima)",
  "#FBE6D4": "var(--cf-graf-valle)",
  "#FFFFFF": "var(--cf-superficie)",
  "#6250D6": "var(--cf-graf-violeta)",
  "#57606A": "var(--cf-graf-gris)",
  "#172033": "var(--cf-tinta)",
};

export function colorTema(color: string): string {
  return VARIABLE_DE_COLOR[color.toUpperCase()] ?? color;
}

const SOL = (
  <>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
  </>
);
const LUNA = <path d="M20.5 14.1A8.5 8.5 0 1 1 9.9 3.5a6.6 6.6 0 0 0 10.6 10.6Z" />;
const PANTALLA = (
  <>
    <rect x="3" y="4" width="18" height="12" rx="2" />
    <path d="M8 20h8M12 16v4" />
  </>
);

function Icono({ children, tam = 18 }: { children: ReactNode; tam?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {children}
    </svg>
  );
}

/**
 * Interruptor de un toque entre claro y oscuro (guarda la elección).
 * `rol="menuitemcheckbox"` para usarlo dentro de un menú; `texto` muestra la etiqueta junto al icono.
 */
export function BotonTema({
  className = "cf-tema-boton", texto = false, rol = "switch",
}: { className?: string; texto?: boolean; rol?: "switch" | "menuitemcheckbox" }) {
  const { tema } = useTema();
  const oscuro = tema === "oscuro";
  return (
    <button
      type="button"
      className={className}
      role={rol}
      aria-checked={oscuro}
      aria-label={texto ? undefined : "Tema oscuro"}
      title={texto ? undefined : oscuro ? "Usar el tema claro" : "Usar el tema oscuro"}
      onClick={() => cambiarTema(oscuro ? "claro" : "oscuro")}
    >
      <Icono>{oscuro ? LUNA : SOL}</Icono>
      {texto && <span className="cf-tema-boton__texto">Tema oscuro</span>}
      {texto && <span className="cf-interruptor" aria-hidden="true"><span /></span>}
    </button>
  );
}

const OPCIONES: [Preferencia, string, ReactNode][] = [
  ["claro", "Claro", SOL],
  ["oscuro", "Oscuro", LUNA],
  ["sistema", "Automático", PANTALLA],
];

/** Tres opciones para una pantalla de ajustes: claro, oscuro o el del sistema. */
export function SelectorTema() {
  const { preferencia } = useTema();
  return (
    <div className="cf-tema-selector" role="radiogroup" aria-label="Tema de la app">
      {OPCIONES.map(([valor, nombre, icono]) => (
        <label key={valor} className="cf-tema-selector__opcion">
          <input type="radio" name="cf-tema" value={valor} checked={preferencia === valor}
            onChange={() => cambiarTema(valor)} />
          <Icono tam={20}>{icono}</Icono>
          <span>{nombre}</span>
        </label>
      ))}
    </div>
  );
}
