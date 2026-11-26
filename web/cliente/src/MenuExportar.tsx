// Botón "Exportar" con los cinco formatos (copia idéntica en las tres apps; tests/test_web_tema.py lo verifica).
// El documento se arma recién al elegir el formato, con los datos que se ven en ese momento.
import { KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import { descargar, Documento, Formato, FORMATOS } from "./exportar";

interface Props {
  /** Arma el documento a exportar; devuelve null si todavía no hay datos. */
  documento: () => Documento | null;
  /** Clase del botón para que combine con los botones de cada app. */
  claseBoton?: string;
  etiqueta?: string;
  /** Hacia dónde se abre el menú. */
  alinear?: "inicio" | "fin";
  deshabilitado?: boolean;
}

export default function MenuExportar({
  documento, claseBoton = "cf-exportar__boton", etiqueta = "Exportar", alinear = "fin", deshabilitado = false,
}: Props) {
  const [abierto, setAbierto] = useState(false);
  const [aviso, setAviso] = useState("");
  const caja = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const opciones = useRef<(HTMLButtonElement | null)[]>([]);
  const id = useId();

  useEffect(() => {
    if (!abierto) return;
    opciones.current[0]?.focus();
    const fuera = (e: MouseEvent) => {
      if (!caja.current?.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  const cerrar = (devolverFoco = true) => {
    setAbierto(false);
    if (devolverFoco) boton.current?.focus();
  };

  const elegir = (formato: Formato) => {
    const doc = documento();
    cerrar();
    if (!doc) {
      setAviso("Aún no hay datos para exportar.");
      return;
    }
    try {
      setAviso(`Descargaste ${descargar(doc, formato)}.`);
    } catch {
      setAviso("No se pudo generar el archivo. Intenta de nuevo.");
    }
  };

  const teclas = (e: KeyboardEvent<HTMLDivElement>) => {
    const lista = opciones.current.filter((o): o is HTMLButtonElement => o !== null);
    const actual = lista.indexOf(document.activeElement as HTMLButtonElement);
    const ir = (i: number) => lista[(i + lista.length) % lista.length]?.focus();
    if (e.key === "ArrowDown") ir(actual + 1);
    else if (e.key === "ArrowUp") ir(actual - 1);
    else if (e.key === "Home") ir(0);
    else if (e.key === "End") ir(lista.length - 1);
    else if (e.key === "Escape") cerrar();
    else if (e.key === "Tab") cerrar(false);
    else return;
    if (e.key !== "Tab") e.preventDefault();
  };

  return (
    <div className={`cf-exportar cf-exportar--${alinear}`} ref={caja}>
      <button
        ref={boton}
        type="button"
        className={claseBoton}
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-controls={abierto ? id : undefined}
        disabled={deshabilitado}
        onClick={() => setAbierto(!abierto)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" && !abierto) {
            e.preventDefault();
            setAbierto(true);
          }
        }}
      >
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
          <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
        </svg>
        {etiqueta}
      </button>
      {abierto && (
        <div className="cf-exportar__menu" role="menu" id={id} aria-label="Formatos para exportar" onKeyDown={teclas}>
          {FORMATOS.map((f, i) => (
            <button
              key={f.formato}
              ref={(el) => {
                opciones.current[i] = el;
              }}
              type="button"
              role="menuitem"
              tabIndex={-1}
              className="cf-exportar__opcion"
              onClick={() => elegir(f.formato)}
            >
              <span className={`cf-exportar__ext cf-exportar__ext--${f.formato}`} aria-hidden="true">{f.formato}</span>
              <span className="cf-exportar__texto">
                <b>{f.nombre}</b>
                <small>{f.detalle}</small>
              </span>
            </button>
          ))}
        </div>
      )}
      <span className="cf-solo-lector" role="status">{aviso}</span>
    </div>
  );
}
