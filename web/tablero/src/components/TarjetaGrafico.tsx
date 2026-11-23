import { useState } from 'react';
import type { ReactNode } from 'react';

interface Props {
  titulo: string;
  subtitulo: string;
  extra?: ReactNode;
  grafico: ReactNode;
  tabla: ReactNode;
  className?: string;
}

export default function TarjetaGrafico({ titulo, subtitulo, extra, grafico, tabla, className }: Props) {
  const [verTabla, setVerTabla] = useState(false);
  return (
    <section className={`tarjeta ${className ?? ''}`} aria-label={titulo}>
      <div className="tarjeta-cab">
        <div>
          <h3 className="tarjeta-titulo">{titulo}</h3>
          <p className="tarjeta-sub">{subtitulo}</p>
          {extra && <div className="tarjeta-extra">{extra}</div>}
        </div>
        <button type="button" className="btn-vista" onClick={() => setVerTabla((v) => !v)}>
          {verTabla ? 'Ver gráfico' : 'Ver tabla'}
        </button>
      </div>
      {verTabla ? <div className="tabla-scroll">{tabla}</div> : <div className="cuerpo-grafico">{grafico}</div>}
    </section>
  );
}
