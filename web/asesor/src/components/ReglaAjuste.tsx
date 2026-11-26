import { CSSProperties, useId } from "react";

// Ajuste de las ventas según la visita del asesor: de -10% a +10% en pasos de 1%.
const MIN = 0.9;
const MAX = 1.1;
const PASO = 0.01;
const MARCAS = Array.from({ length: 21 }, (_, i) => i);
const ETIQUETAS = [
  { i: 0, texto: "−10%" },
  { i: 5, texto: "−5%" },
  { i: 10, texto: "Sin ajuste" },
  { i: 15, texto: "+5%" },
  { i: 20, texto: "+10%" },
];
const redondear = (v: number) => Math.round(v * 100) / 100;

export function textoAjuste(a: number) {
  const pct = Math.round((a - 1) * 100);
  if (pct === 0) return "sin ajuste";
  return pct < 0 ? `${pct}% (más prudente)` : `+${pct}% (más optimista)`;
}

/** Deslizador con regla: marcas cada 1%, rótulos cada 5% y el tramo desde "sin ajuste" hasta el valor pintado. */
export default function ReglaAjuste({ valor, cambiar }: { valor: number; cambiar: (v: number) => void }) {
  const id = useId();
  const pct = Math.round((valor - 1) * 100);
  const tono = pct < 0 ? "prudente" : pct > 0 ? "optimista" : "neutro";
  const indice = Math.round((valor - MIN) / PASO);

  return (
    <div className={`regla regla--${tono}`} style={{ "--pos": (valor - MIN) / (MAX - MIN) } as CSSProperties}>
      <div className="regla__cab">
        <label htmlFor={id}>Ventas según tu visita</label>
        <output htmlFor={id} className="regla__valor">
          {pct === 0 ? "Sin ajuste" : `${pct > 0 ? "+" : "−"}${Math.abs(pct)}%, ${pct > 0 ? "más optimista" : "más prudente"}`}
        </output>
      </div>
      <input
        id={id}
        type="range"
        min={MIN}
        max={MAX}
        step={PASO}
        value={valor}
        aria-valuetext={textoAjuste(valor)}
        onChange={(e) => cambiar(redondear(Number(e.target.value)))}
      />
      <div className="regla__marcas" aria-hidden="true">
        {MARCAS.map((i) => (
          <span key={i} className={i % 5 === 0 ? "mayor" : undefined} style={{ "--i": i } as CSSProperties} />
        ))}
      </div>
      <div className="regla__rotulos" aria-hidden="true">
        {ETIQUETAS.map((e) => (
          <button
            key={e.i}
            type="button"
            tabIndex={-1}
            className={indice === e.i ? "activo" : undefined}
            style={{ "--i": e.i } as CSSProperties}
            onClick={() => cambiar(redondear(MIN + e.i * PASO))}
          >
            {e.texto}
          </button>
        ))}
      </div>
    </div>
  );
}
