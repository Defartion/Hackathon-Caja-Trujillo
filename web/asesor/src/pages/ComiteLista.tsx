import { Link, useNavigate } from "react-router-dom";
import { DECISION_ETIQUETA, leerValidacion, listarExpedientes } from "../components/plan/expedientes";
import { fmtS0 } from "../formato";

const CLASE: Record<string, string> = { aprobado: "baja", observado: "media", rechazado: "alta" };

/** Entrada del menú "Comité de créditos": expedientes enviados y su estado de validación. */
export default function ComiteLista() {
  const nav = useNavigate();
  const lista = listarExpedientes();

  return (
    <div className="tarjeta">
      <div className="fila" style={{ marginBottom: 12 }}>
        <div>
          <h1>Comité de créditos</h1>
          <div className="ayuda">Expedientes enviados al comité. Ábrelos para validar o imprimir.</div>
        </div>
        <div className="espacio" />
        <button type="button" className="btn btn-primario" onClick={() => nav("/nueva")}>
          Nueva solicitud
        </button>
      </div>
      {lista.length === 0 ? (
        <div className="cargando">
          Todavía no hay expedientes. Arma un plan en <Link to="/nueva">Nueva solicitud</Link> y pulsa "Enviar al comité".
        </div>
      ) : (
        <table className="tabla-bandeja">
          <thead>
            <tr>
              <th>Expediente</th>
              <th>Negocio</th>
              <th className="num">Monto</th>
              <th className="num solo-escritorio">Plazo</th>
              <th className="solo-escritorio">Enviado</th>
              <th>Estado</th>
              <th aria-label="Abrir" />
            </tr>
          </thead>
          <tbody>
            {lista.map((e) => {
              const v = leerValidacion(e.id);
              const abrir = () => nav(`/comite/${encodeURIComponent(e.id)}`);
              return (
                <tr
                  key={e.id}
                  className="clic"
                  tabIndex={0}
                  onClick={abrir}
                  onKeyDown={(k) => (k.key === "Enter" || k.key === " ") && (k.preventDefault(), abrir())}
                >
                  <td style={{ fontWeight: 600 }}>{e.id}</td>
                  <td>
                    {e.negocio.nombre || e.negocio.cliente_id}
                    <div className="ayuda" style={{ marginTop: 0 }}>{e.negocio.actividad}</div>
                  </td>
                  <td className="num">{fmtS0(Number(e.credito.monto))}</td>
                  <td className="num solo-escritorio">{e.credito.plazo} m</td>
                  <td className="solo-escritorio">{new Date(e.creado).toLocaleDateString("es-PE")}</td>
                  <td>
                    <span className={`etiqueta ${v ? CLASE[v.decision] : "fija"}`}>
                      {v ? DECISION_ETIQUETA[v.decision] : "Por validar"}
                    </span>
                  </td>
                  <td className="abrir" aria-hidden="true">Ver →</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
