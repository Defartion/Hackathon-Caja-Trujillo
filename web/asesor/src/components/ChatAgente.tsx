import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { API_URL, type Cliente, type Propuesta } from "../api";
import { fmtPct, fmtS } from "../formato";

const PREGUNTAS = [
  "¿Por qué bajó el monto?",
  "¿Y a 24 meses?",
  "¿Por qué este producto?",
  "¿Qué pasa si hay El Niño?",
  "¿Cuánto le cuesta el aplazamiento?",
];

const HERRAMIENTAS: Record<string, string> = {
  recalcular_propuesta: "Recalculó la propuesta",
  simular_cliente: "Simuló el riesgo",
  consultar_politica: "Consultó la política",
  explicar_paso_bitacora: "Revisó la bitácora",
};

interface RespuestaAgente {
  respuesta: string;
  herramientas_usadas: string[];
  cifras_verificadas: boolean;
  fuente: "llm" | "plantilla";
  propuesta_actualizada?: Propuesta | null;
}

interface Turno {
  pregunta: string;
  resultado: RespuestaAgente;
}

function enviar(ruta: string, body: unknown, signal: AbortSignal): Promise<Response> {
  return fetch(API_URL + ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

async function leer<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => null);
    throw new Error(typeof error?.detail === "string"
      ? error.detail
      : `La API del agente devolvió un error (${respuesta.status}).`);
  }
  return respuesta.json() as Promise<T>;
}

function VistaPrevia({ propuesta }: { propuesta: Propuesta }) {
  return (
    <div className="chat-agente-vista">
      <strong>Vista previa de la propuesta</strong>
      <p>{propuesta.descripcion_producto}</p>
      <dl>
        <div><dt>Monto propuesto</dt><dd>{fmtS(propuesta.principal_aprobado)}</dd></div>
        <div><dt>Plazo</dt><dd>{propuesta.plazo} meses</dd></div>
        <div><dt>TEA</dt><dd>{fmtPct(propuesta.tea, 2)}</dd></div>
        <div><dt>Cuota fija de referencia</dt><dd>{fmtS(propuesta.cuota_fija_referencia)}</dd></div>
      </dl>
      {!propuesta.valido && <span className="etiqueta alta">No cumple la validación del motor</span>}
    </div>
  );
}

export default function ChatAgente({ cliente, deshabilitado = false }: { cliente: Cliente; deshabilitado?: boolean }) {
  const [texto, setTexto] = useState("");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [vista, setVista] = useState<number | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sesion = useRef<string | null>(null);
  const solicitud = useRef<AbortController | null>(null);
  const historial = useRef<HTMLDivElement>(null);
  const propuestaVisible = useRef<HTMLDivElement>(null);
  const id = useId();
  const bloqueado = deshabilitado || cargando;

  useEffect(() => () => solicitud.current?.abort(), []);

  useEffect(() => {
    if (historial.current) historial.current.scrollTop = historial.current.scrollHeight;
  }, [turnos]);

  useEffect(() => {
    propuestaVisible.current?.scrollIntoView({ block: "nearest" });
  }, [vista]);

  async function preguntar(pregunta: string, desdeFormulario = false) {
    if (deshabilitado || solicitud.current || !pregunta.trim()) return;
    const preguntaLimpia = pregunta.trim();
    const abortar = new AbortController();
    solicitud.current = abortar;
    setCargando(true);
    setError(null);

    async function iniciarSesion() {
      const respuesta = await enviar("/agente/sesion", cliente, abortar.signal);
      const datos = await leer<{ sesion_id: string }>(respuesta);
      sesion.current = datos.sesion_id;
      return datos.sesion_id;
    }

    function enviarMensaje(sesionId: string) {
      const ruta = `/agente/sesion/${encodeURIComponent(sesionId)}/mensaje`;
      return enviar(ruta, { texto: preguntaLimpia }, abortar.signal);
    }

    try {
      const idGuardado = sesion.current;
      let respuesta = await enviarMensaje(idGuardado ?? await iniciarSesion());
      if (respuesta.status === 404 && idGuardado) {
        sesion.current = null;
        respuesta = await enviarMensaje(await iniciarSesion());
      }
      const resultado = await leer<RespuestaAgente>(respuesta);
      setTurnos((historialAnterior) => [...historialAnterior, { pregunta: preguntaLimpia, resultado }]);
      if (desdeFormulario) setTexto("");
    } catch (e) {
      if (!abortar.signal.aborted) {
        setError(e instanceof TypeError ? "No se pudo conectar con el agente." : (e as Error).message);
      }
    } finally {
      solicitud.current = null;
      if (!abortar.signal.aborted) setCargando(false);
    }
  }

  function enviarFormulario(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    void preguntar(texto, true);
  }

  return (
    <aside className="chat-agente" aria-label="Agente de CuotaFlex">
      <style>{estilos}</style>
      <details>
        <summary>Pregúntale al agente</summary>
        <div className="chat-agente-contenido">
          <div className="chat-agente-preguntas" role="group" aria-label="Preguntas frecuentes">
            {PREGUNTAS.map((pregunta) => (
              <button key={pregunta} type="button" className="btn" disabled={bloqueado} onClick={() => void preguntar(pregunta)}>
                {pregunta}
              </button>
            ))}
          </div>

          <div ref={historial} className="chat-agente-historial" role="log" aria-label="Conversación con el agente">
            {turnos.map(({ pregunta, resultado }, indice) => {
              const propuesta = resultado.propuesta_actualizada;
              return (
                <article key={indice} className="chat-agente-turno">
                  <p className="chat-agente-pregunta">{pregunta}</p>
                  <p className="chat-agente-respuesta">{resultado.respuesta}</p>
                  <div className="chat-agente-herramientas">
                    {[...new Set(resultado.herramientas_usadas)].map((herramienta) => (
                      <span key={herramienta} className="etiqueta aplazamiento">
                        {herramienta === "recalcular_propuesta" && propuesta
                          ? `Recalculó a ${propuesta.plazo} meses`
                          : HERRAMIENTAS[herramienta] ?? herramienta}
                      </span>
                    ))}
                    {resultado.cifras_verificadas && <span className="etiqueta baja">✓ Cifras verificadas</span>}
                    <span className="etiqueta fija">{resultado.fuente === "llm" ? "IA generativa" : "Plantilla"}</span>
                  </div>
                  {propuesta && (
                    <>
                      <button
                        className="btn chat-agente-aplicar"
                        type="button"
                        aria-expanded={vista === indice}
                        aria-controls={`${id}-propuesta-${indice}`}
                        onClick={() => setVista(vista === indice ? null : indice)}
                      >
                        {vista === indice ? "Ocultar propuesta" : "Aplicar a la ficha"}
                      </button>
                      <div id={`${id}-propuesta-${indice}`} hidden={vista !== indice} ref={vista === indice ? propuestaVisible : null}>
                        {vista === indice && <VistaPrevia propuesta={propuesta} />}
                      </div>
                    </>
                  )}
                </article>
              );
            })}
          </div>

          {cargando && <div className="chat-agente-estado" role="status">Consultando el motor…</div>}
          {error && <div className="aviso" role="alert">{error}</div>}
          <form className="chat-agente-formulario" onSubmit={enviarFormulario}>
            <label className="campo">
              Tu pregunta
              <input
                type="text"
                value={texto}
                maxLength={500}
                onChange={(evento) => setTexto(evento.target.value)}
                readOnly={bloqueado}
              />
            </label>
            <button className="btn btn-primario" type="submit" disabled={bloqueado || !texto.trim()}>Enviar</button>
          </form>
        </div>
      </details>
    </aside>
  );
}

const estilos = `
  .chat-agente {
    position: fixed;
    inset-inline-end: max(16px, calc((100vw - 1272px) / 2));
    inset-block-end: max(16px, env(safe-area-inset-bottom));
    z-index: 8;
    width: max-content;
    max-width: calc(100vw - 32px);
  }
  .chat-agente:has(details[open]) { width: 440px; }
  .chat-agente details {
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid var(--cf-gris-200);
    border-radius: var(--cf-radio-lg);
    box-shadow: var(--cf-sombra-3);
  }
  .chat-agente details:not([open]) { background: none; border-color: transparent; box-shadow: none; }
  .chat-agente summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 18px;
    min-height: 48px;
    background: var(--cf-rojo);
    color: #fff;
    border-radius: 999px;
    box-shadow: 0 14px 30px -10px rgb(142 11 32 / 60%);
    cursor: pointer;
    list-style: none;
    font-weight: 650;
    transition: background-color var(--cf-rapido);
  }
  .chat-agente summary:hover { background: var(--cf-rojo-hover); }
  .chat-agente details[open] summary { border-radius: calc(var(--cf-radio-lg) - 1px) calc(var(--cf-radio-lg) - 1px) 0 0; box-shadow: none; }
  .chat-agente summary::-webkit-details-marker { display: none; }
  .chat-agente summary::after { content: "+" / ""; font-size: 18px; line-height: 1; }
  .chat-agente details[open] summary::after { content: "−" / ""; }
  .chat-agente-contenido {
    display: grid;
    gap: 12px;
    padding: 12px;
    max-height: calc(100dvh - 80px);
    overflow: auto;
  }
  .chat-agente-preguntas, .chat-agente-herramientas { display: flex; flex-wrap: wrap; gap: 6px; }
  .chat-agente-preguntas .btn { font-size: 12px; padding: 6px 8px; }
  .chat-agente-historial { max-height: min(40dvh, 340px); overflow-y: auto; }
  .chat-agente-historial:empty { display: none; }
  .chat-agente-turno { display: grid; gap: 8px; padding: 12px; background: var(--cf-gris-100); border-radius: 12px; }
  .chat-agente-turno + .chat-agente-turno { margin-top: 8px; }
  .chat-agente-pregunta, .chat-agente-respuesta, .chat-agente-vista p { margin: 0; overflow-wrap: anywhere; }
  .chat-agente-pregunta { font-weight: 650; }
  .chat-agente-respuesta { line-height: 1.45; white-space: pre-wrap; }
  .chat-agente-aplicar { justify-self: start; }
  .chat-agente-vista { background: #fff; border: 1px solid var(--cf-gris-200); border-radius: 12px; padding: 12px; }
  .chat-agente-vista p { margin-top: 4px; }
  .chat-agente-vista dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 8px 0 0; }
  .chat-agente-vista dt, .chat-agente-estado { color: var(--cf-gris-600); font-size: 12px; }
  .chat-agente-vista dd { margin: 2px 0 0; font-weight: 650; }
  .chat-agente-vista .etiqueta { margin-top: 8px; }
  .chat-agente-formulario { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: end; }
  .chat-agente-formulario input { min-width: 0; }
`;
