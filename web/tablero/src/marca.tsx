// Marca de CuotaFlex y "ritmo de cuotas" (copia idéntica en las 3 apps; ver tests/test_web_tema.py).
// El símbolo son cuotas que suben y bajan con la temporada: la idea central del producto.

// Ejemplo ilustrativo: un productor de arroz en Chepén, con cosecha en junio y julio.
const RITMO = [0.32, 0.27, 0.34, 0.46, 0.64, 0.94, 1, 0.72, 0.5, 0.4, 0.36, 0.42];
const CUOTA_FIJA = 0.56;
const INICIALES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

export function Simbolo({ tam = 30, invertido = false }: { tam?: number; invertido?: boolean }) {
  const fondo = invertido ? "#FFFFFF" : "#C8102E";
  const barra = invertido ? "#C8102E" : "#FFFFFF";
  return (
    <svg className="cf-marca__simbolo" width={tam} height={tam} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="9" fill={fondo} />
      <rect x="6.4" y="17.5" width="3.8" height="7.5" rx="1.7" fill={barra} fillOpacity="0.7" />
      <rect x="11.6" y="12" width="3.8" height="13" rx="1.7" fill={barra} />
      <rect x="16.8" y="7" width="3.8" height="18" rx="1.7" fill={barra} />
      <rect x="22" y="14.5" width="3.8" height="10.5" rx="1.7" fill={barra} fillOpacity="0.7" />
    </svg>
  );
}

export default function Marca({ invertida = false, tam = 30 }: { invertida?: boolean; tam?: number }) {
  return (
    <span className={`cf-marca ${invertida ? "cf-marca--invertida" : ""}`} translate="no">
      <Simbolo tam={tam} invertido={invertida} />
      <span className="cf-marca__nombre">
        Cuota<span className="cf-marca__flex">Flex</span>
      </span>
    </span>
  );
}

/** Barras de un año de cuotas que siguen la temporada, frente a la línea de una cuota fija. */
export function Ritmo() {
  return (
    <figure className="cf-ritmo" aria-labelledby="cf-ritmo-desc">
      <figcaption id="cf-ritmo-desc" className="cf-ritmo__leyenda">
        <span><i className="barra" aria-hidden="true" /> Cuotas CuotaFlex de un arrocero de Chepén, de enero a diciembre</span>
        <span><i className="linea" aria-hidden="true" /> Cuota fija</span>
      </figcaption>
      <div className="cf-ritmo__lienzo" aria-hidden="true">
        {RITMO.map((h, i) => (
          <span
            key={i}
            className={`cf-ritmo__barra ${h < CUOTA_FIJA ? "baja" : ""}`}
            style={{ "--h": h, "--i": i } as React.CSSProperties}
          >
            {INICIALES[i]}
          </span>
        ))}
        <span className="cf-ritmo__fija" style={{ "--fija": CUOTA_FIJA } as React.CSSProperties} />
      </div>
    </figure>
  );
}
