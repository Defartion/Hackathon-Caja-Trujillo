import { Propuesta } from "../api";
import { fmtPct, fmtS, fmtS0 } from "../formato";

export default function TarjetaProducto({ p }: { p: Propuesta }) {
  const reducido = p.principal_aprobado < p.principal_solicitado;
  return (
    <div className="tarjeta">
      <div className="fila" style={{ marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>Propuesta del agente</h2>
        <span className={`etiqueta ${p.producto}`}>{p.producto}</span>
        {!p.valido && <span className="etiqueta alta">no válida</span>}
      </div>
      <div style={{ fontWeight: 600, marginBottom: 12 }}>{p.descripcion_producto}</div>
      <div className="datos" style={{ marginBottom: 12 }}>
        <div className="dato">
          <span className="k">Monto aprobado</span>
          <span className="v" style={{ color: reducido ? "var(--cf-ambar)" : undefined }}>{fmtS0(p.principal_aprobado)}</span>
        </div>
        <div className="dato">
          <span className="k">Plazo</span>
          <span className="v">{p.plazo} meses</span>
        </div>
        <div className="dato">
          <span className="k">TEA</span>
          <span className="v">{fmtPct(p.tea)}</span>
        </div>
        <div className="dato">
          <span className="k">Cuota fija ref.</span>
          <span className="v">{fmtS(p.cuota_fija_referencia)}</span>
        </div>
      </div>
      {reducido && (
        <div className="info" style={{ marginBottom: 10 }}>
          Solicitó {fmtS0(p.principal_solicitado)}: el agente reduce el monto para no exceder la capacidad de pago del
          escenario conservador.
        </div>
      )}
      <div className="datos">
        <div className="dato">
          <span className="k">Aplazamientos</span>
          <span className="v">{p.aplazamientos_disponibles}</span>
        </div>
        <div className="dato">
          <span className="k">Cláusula El Niño</span>
          <span className="v">{p.clausula_el_nino ? "Sí" : "No"}</span>
        </div>
      </div>
    </div>
  );
}
