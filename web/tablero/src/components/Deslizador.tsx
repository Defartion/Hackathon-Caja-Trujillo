import { useId } from 'react';
import type { ParametroEditable } from '../api';
import { formatearValor, redondearAPaso } from '../formato';

interface Props {
  param: ParametroEditable;
  valor: number;
  deshabilitado: boolean;
  onCambio: (ruta: string, valor: number) => void;
}

export default function Deslizador({ param, valor, deshabilitado, onCambio }: Props) {
  const id = useId();
  const base = param.valor;
  const cambiado = Math.abs(valor - base) > 1e-9;
  // Si un escenario fija un valor fuera del rango del control, el rango se amplía
  // para que la posición del deslizador nunca sea engañosa.
  const min = Math.min(param.minimo, valor, base);
  const max = Math.max(param.maximo, valor, base);

  return (
    <div className="fila-param">
      <div className="fila-param-cab">
        {cambiado && <span className="punto-cambio" aria-hidden="true" />}
        <label className="etiqueta-param" htmlFor={id}>
          {param.etiqueta}
        </label>
        <span className="ayuda-icono" tabIndex={0} role="img" aria-label={`Ayuda: ${param.ayuda}`}>
          ⓘ
        </span>
        <span className="tooltip-ayuda" role="tooltip">
          {param.ayuda}
        </span>
        {cambiado && <span className="base-param">base {formatearValor(param.formato, base)}</span>}
        <span className={`valor-param ${cambiado ? '' : 'solo'}`}>{formatearValor(param.formato, valor)}</span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={param.paso}
        value={valor}
        disabled={deshabilitado}
        onChange={(e) => onCambio(param.ruta, redondearAPaso(Number(e.target.value), param.paso))}
      />
    </div>
  );
}
