import { FormEvent, useState } from "react";
import { Decision, DECISION_ETIQUETA, guardarValidacion, leerValidacion, Validacion } from "./expedientes";
import { fmtFechaHora } from "./formato";

const DECISIONES: Decision[] = ["aprobado", "observado", "rechazado"];
const VERBO: Record<Decision, string> = { aprobado: "Aprobar", observado: "Observar", rechazado: "Rechazar" };

/**
 * Validación del Asesor de Riesgos (maqueta del flujo): aprobar, observar con comentario o
 * rechazar. Queda guardada en este navegador y se imprime con su fecha.
 */
export default function ValidacionRiesgos({ id }: { id: string }) {
  const [guardada, setGuardada] = useState<Validacion | null>(() => leerValidacion(id));
  const [editando, setEditando] = useState(!guardada);
  const [decision, setDecision] = useState<Decision | null>(guardada?.decision ?? null);
  const [comentario, setComentario] = useState(guardada?.comentario ?? "");
  const [nombre, setNombre] = useState(guardada?.nombre ?? "");
  const [error, setError] = useState<string | null>(null);
  const [soloMemoria, setSoloMemoria] = useState(false);

  function registrar(e: FormEvent) {
    e.preventDefault();
    if (!decision) return setError("Elige aprobar, observar o rechazar.");
    if (decision !== "aprobado" && !comentario.trim())
      return setError(decision === "observado" ? "Escribe la observación para el Asesor de Negocios." : "Escribe el motivo del rechazo.");
    const v: Validacion = { decision, comentario: comentario.trim(), nombre: nombre.trim(), fecha: new Date().toISOString() };
    setSoloMemoria(!guardarValidacion(id, v));
    setGuardada(v);
    setEditando(false);
    setError(null);
  }

  return (
    <div className="pl-validacion">
      {guardada && !editando && (
        <div className={`pl-sello ${guardada.decision}`} data-testid="validacion-registrada">
          <span>
            {guardada.decision === "aprobado" ? "✓" : guardada.decision === "observado" ? "!" : "✕"} {DECISION_ETIQUETA[guardada.decision]} por el
            Asesor de Riesgos
          </span>
          <span className="det">
            {fmtFechaHora(guardada.fecha)}
            {guardada.nombre ? ` · ${guardada.nombre}` : ""}
          </span>
          <span className="espacio" style={{ flex: 1 }} />
          <button type="button" className="btn solo-pantalla" onClick={() => setEditando(true)}>
            Corregir
          </button>
        </div>
      )}
      {guardada && !editando && guardada.comentario && (
        <div>
          <strong>Comentario:</strong> {guardada.comentario}
        </div>
      )}
      {soloMemoria && !editando && (
        <div className="pl-gris solo-pantalla">Este navegador no permite guardar datos: la validación se perderá al cerrar la pestaña.</div>
      )}

      {editando && (
        <form className="solo-pantalla rejilla" style={{ gap: 10 }} onSubmit={registrar}>
          <div className="pl-decisiones" role="group" aria-label="Decisión del Asesor de Riesgos">
            {DECISIONES.map((d) => (
              <button key={d} type="button" className={`pl-decision ${d}`} aria-pressed={decision === d} onClick={() => setDecision(d)}>
                {VERBO[d]}
              </button>
            ))}
          </div>
          <label className="pl-campo">
            <span className="etq">Comentario {decision === "aprobado" ? "(opcional)" : ""}</span>
            <textarea value={comentario} onChange={(e) => setComentario(e.target.value)} placeholder="Por ejemplo: confirmar con boletas las ventas de cosecha." maxLength={600} />
          </label>
          <label className="pl-campo" style={{ maxWidth: 320 }}>
            <span className="etq">Asesor de Riesgos (opcional)</span>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre o código" maxLength={60} />
          </label>
          {error && <div className="pl-error" role="alert">{error}</div>}
          <div className="pl-acciones">
            <button type="submit" className="btn btn-primario">
              Registrar validación
            </button>
            {guardada && (
              <button type="button" className="btn" onClick={() => setEditando(false)}>
                Cancelar
              </button>
            )}
            <span className="pl-gris">Maqueta: se guarda solo en este navegador.</span>
          </div>
        </form>
      )}
      {!guardada && (
        <div className="solo-impresion">
          <strong>Asesor de Riesgos</strong>
          <div className="pl-casillas">
            <span>☐ Aprobado</span>
            <span>☐ Observado</span>
            <span>☐ Rechazado</span>
          </div>
          <div className="pl-firmas">
            <div className="pl-firma">Asesor de Riesgos · firma</div>
            <div className="pl-firma">Fecha</div>
          </div>
        </div>
      )}
    </div>
  );
}
