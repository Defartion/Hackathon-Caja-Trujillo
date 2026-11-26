import { useState } from "react";
import { Propuesta, Riesgo } from "../api";
import { fmtPct, fmtS0 } from "../formato";

export const PRODUCTO_ETIQUETA: Record<Propuesta["producto"], string> = {
  fija: "Cuota fija",
  aplazamiento: "Cuota fija con aplazamientos",
  estacional: "Cuotas por temporada",
};

interface Props {
  p: Propuesta;
  fija: Riesgo;
  flex: Riesgo;
  onRegistrar: () => void;
  onVerCronograma: () => void;
}

/** Lo primero que ve el asesor: qué propone el agente, por qué y qué hacer ahora. */
export default function ResumenDecision({ p, fija, flex, onRegistrar, onVerCronograma }: Props) {
  const [copiado, setCopiado] = useState(false);
  const cuotas = p.cronograma.map((f) => f.cuota);
  const min = Math.min(...cuotas);
  const max = Math.max(...cuotas);
  const reducido = p.principal_aprobado < p.principal_solicitado - 0.5;

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(p.explicacion);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setCopiado(false);
    }
  };

  return (
    <section className="tarjeta resumen" aria-label="Propuesta del agente">
      <div className="fila" style={{ marginBottom: 10, alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Propuesta del agente</h2>
        <span className={`etiqueta ${p.producto}`}>{PRODUCTO_ETIQUETA[p.producto]}</span>
        {p.valido ? (
          <span className="etiqueta baja">✓ Cumple las políticas</span>
        ) : (
          <span className="etiqueta alta">Revisar: no cumple todas las políticas</span>
        )}
      </div>

      <div className="resumen-cifras">
        <div className="dato">
          <span className="k">Monto a aprobar</span>
          <span className="v grande" style={{ color: reducido ? "var(--cf-ambar)" : undefined }}>
            {fmtS0(p.principal_aprobado)}
          </span>
          {reducido && <span className="nota">pidió {fmtS0(p.principal_solicitado)}</span>}
        </div>
        <div className="dato">
          <span className="k">Plazo</span>
          <span className="v grande">{p.plazo} meses</span>
        </div>
        <div className="dato">
          <span className="k">Cuota mensual</span>
          <span className="v grande">
            {Math.abs(max - min) < 1 ? fmtS0(min) : `${fmtS0(min)} – ${fmtS0(max)}`}
          </span>
          <span className="nota">
            {Math.abs(max - min) < 1 ? "igual todos los meses" : "según la temporada del negocio"}
          </span>
        </div>
        <div className="dato">
          <span className="k">TEA</span>
          <span className="v grande">{fmtPct(p.tea)}</span>
        </div>
        <div className="dato">
          <span className="k">Atraso &gt; 30 días (simulado)</span>
          <span className="v grande">
            <span style={{ color: "var(--cf-gris-600)" }}>{fmtPct(fija.mora30)}</span>
            {" → "}
            <span className={flex.mora30 <= fija.mora30 ? "mejor" : "peor"}>{fmtPct(flex.mora30)}</span>
          </span>
          <span className="nota">cuota fija → esta propuesta</span>
        </div>
      </div>

      {reducido && (
        <div className="info" style={{ marginTop: 12 }}>
          El agente bajó el monto para que la cuota no supere lo que el negocio puede pagar en sus meses flojos.
        </div>
      )}

      <div className="explicacion" style={{ marginTop: 12 }}>
        <div className="k-mini">Qué decirle al cliente</div>
        {p.explicacion}
      </div>

      <div className="info" style={{ fontSize: 13, marginTop: 12 }} data-testid="fuera-de-alcance">
        Aplazamientos durante el crédito y alivio de El Niño en vivo: fuera del alcance del reto (créditos vigentes =
        reprogramación). El Niño se evalúa como escenario adverso al diseñar el plan, en <strong>Nueva solicitud</strong>.
      </div>

      <div className="acciones">
        <button type="button" className="btn btn-primario" onClick={onRegistrar}>
          Registrar solicitud
        </button>
        <button type="button" className="btn" onClick={copiar}>
          {copiado ? "✓ Copiado" : "Copiar explicación"}
        </button>
        <a
          className="btn"
          href={`https://wa.me/?text=${encodeURIComponent(p.explicacion)}`}
          target="_blank"
          rel="noreferrer"
        >
          Enviar por WhatsApp
        </a>
        <button type="button" className="btn" onClick={onVerCronograma}>
          Ver cronograma
        </button>

      </div>
    </section>
  );
}
