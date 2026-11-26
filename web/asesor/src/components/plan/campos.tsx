// Campos de formulario con ayuda y error en lenguaje de campo.
import { ReactNode, useId } from "react";

export function Campo({
  etiqueta,
  ayuda,
  error,
  children,
  ancho,
}: {
  etiqueta: string;
  ayuda?: ReactNode;
  error?: string;
  children: (id: string, describe: string | undefined) => ReactNode;
  ancho?: number;
}) {
  const id = useId();
  const idAyuda = `${id}-ayuda`;
  const idError = `${id}-error`;
  const describe = [ayuda ? idAyuda : "", error ? idError : ""].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`pl-campo ${error ? "con-error" : ""}`} style={ancho ? { gridColumn: `span ${ancho}` } : undefined}>
      <label htmlFor={id}>
        <span className="etq">{etiqueta}</span>
      </label>
      {children(id, describe)}
      {ayuda && (
        <span className="pl-ayuda" id={idAyuda}>
          {ayuda}
        </span>
      )}
      {error && (
        <span className="pl-error" id={idError} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

/** Entrada numérica con prefijo (S/) o sufijo (%, meses). */
export function EntradaNumero({
  id,
  describe,
  valor,
  cambiar,
  prefijo,
  sufijo,
  paso = "any",
  min = 0,
  max,
  placeholder,
  deshabilitada,
}: {
  id: string;
  describe?: string;
  valor: string;
  cambiar: (v: string) => void;
  prefijo?: string;
  sufijo?: string;
  paso?: string;
  min?: number;
  max?: number;
  placeholder?: string;
  deshabilitada?: boolean;
}) {
  return (
    <div className="pl-prefijo">
      {prefijo && <span>{prefijo}</span>}
      <input
        id={id}
        type="number"
        inputMode="decimal"
        step={paso}
        min={min}
        max={max}
        value={valor}
        placeholder={placeholder}
        disabled={deshabilitada}
        aria-describedby={describe}
        onChange={(e) => cambiar(e.target.value)}
      />
      {sufijo && <span className="suf">{sufijo}</span>}
    </div>
  );
}
