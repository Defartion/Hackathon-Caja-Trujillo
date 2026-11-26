import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Cliente, RespuestaPropuesta } from "../api";
import Bitacora from "../components/Bitacora";
import ChatAgente from "../components/ChatAgente";
import Comparativa from "../components/Comparativa";
import GraficoCuotas from "../components/GraficoCuotas";
import GraficoVentas from "../components/GraficoVentas";
import RegistroCore from "../components/RegistroCore";
import ResumenDecision from "../components/ResumenDecision";
import TablaCronograma from "../components/TablaCronograma";
import { fmtPct, fmtS0, MESES, nivelEstacionalidad, RUBRO_ETIQUETA } from "../formato";
import { useCartera } from "../useCartera";

type Edicion = Pick<Cliente, "principal" | "plazo" | "ajuste_asesor">;
type Pestana = "cuotas" | "ventas" | "riesgo" | "cronograma" | "agente";

const PESTANAS: { id: Pestana; texto: string }[] = [
  { id: "cuotas", texto: "Cuotas vs. capacidad" },
  { id: "ventas", texto: "Ventas del negocio" },
  { id: "riesgo", texto: "Riesgo simulado" },
  { id: "cronograma", texto: "Cronograma" },
  { id: "agente", texto: "Cómo decidió el agente" },
];

const clave = (e: Edicion) => `${e.principal}|${e.plazo}|${e.ajuste_asesor}`;

function textoAjuste(a: number) {
  const pct = Math.round((a - 1) * 100);
  if (pct === 0) return "sin ajuste";
  return pct < 0 ? `${pct}% (más prudente)` : `+${pct}% (más optimista)`;
}

export default function Ficha() {
  const { id } = useParams();
  const { datos, error: errCartera } = useCartera();
  const base = datos?.find((c) => c.cliente_id === id);

  const [edicion, setEdicion] = useState<Edicion | null>(null);
  const [resp, setResp] = useState<RespuestaPropuesta | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pestana, setPestana] = useState<Pestana>("cuotas");
  const calculado = useRef<string>("");
  const refRegistro = useRef<HTMLDivElement>(null);
  const refPestanas = useRef<HTMLDivElement>(null);

  const calcular = useCallback(async (c: Cliente) => {
    calculado.current = clave(c);
    setCargando(true);
    setError(null);
    try {
      setResp(await api.propuesta(c));
      setCliente(c);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (base) {
      setEdicion({ principal: base.principal, plazo: base.plazo, ajuste_asesor: base.ajuste_asesor });
      setResp(null);
      setPestana("cuotas");
      void calcular(base);
    }
  }, [base, calcular]);

  // Recalcula solo al dejar de editar (sin botón): el asesor ve el efecto de cada cambio.
  useEffect(() => {
    if (!base || !edicion || edicion.principal < 500 || clave(edicion) === calculado.current) return;
    const t = setTimeout(() => void calcular({ ...base, ...edicion }), 700);
    return () => clearTimeout(t);
  }, [base, edicion, calcular]);

  if (errCartera) return <div className="aviso">{errCartera}</div>;
  if (!datos) return <div className="cargando">Cargando…</div>;
  if (!base || !edicion)
    return (
      <div className="aviso">
        No existe la solicitud {id}. <Link to="/">Volver a la bandeja</Link>
      </div>
    );

  const est = nivelEstacionalidad(base.indice_estacionalidad);
  const p = resp?.propuesta;
  const cambiado = clave(edicion) !== clave(base);
  const sugerido =
    p && (Math.abs(p.principal_aprobado - edicion.principal) > 0.5 || p.plazo !== edicion.plazo) && [12, 18, 24].includes(p.plazo)
      ? { principal: p.principal_aprobado, plazo: p.plazo }
      : null;

  const irA = (ref: React.RefObject<HTMLDivElement>) =>
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="rejilla">
      <div className="tarjeta">
        <div className="fila" style={{ marginBottom: 12, alignItems: "center" }}>
          <Link to="/" className="volver">
            ← Bandeja
          </Link>
          <h1>Solicitud {base.cliente_id}</h1>
          <span className={`etiqueta ${est.clase}`}>Estacionalidad {est.texto.toLowerCase()}</span>
        </div>
        <div className="datos">
          <div className="dato"><span className="k">Rubro</span><span className="v">{RUBRO_ETIQUETA[base.rubro]}</span></div>
          <div className="dato"><span className="k">Región</span><span className="v">{base.region}</span></div>
          <div className="dato"><span className="k">Ventas medias</span><span className="v">{fmtS0(base.ventas_medias)}</span></div>
          <div className="dato"><span className="k">Margen</span><span className="v">{fmtPct(base.margen)}</span></div>
          <div className="dato"><span className="k">Gasto familiar</span><span className="v">{fmtS0(base.gasto_familiar)}</span></div>
          <div className="dato"><span className="k">Otras cuotas</span><span className="v">{fmtS0(base.otras_cuotas)}</span></div>
          <div className="dato"><span className="k">Atraso máx.</span><span className="v">{base.dias_atraso_max} días</span></div>
          <div className="dato"><span className="k">Primera cuota</span><span className="v">{MESES[base.mes_desembolso]}</span></div>
        </div>
      </div>

      <div className="tarjeta">
        <div className="fila" style={{ alignItems: "center", marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Ajustar la solicitud</h2>
          <span className="ayuda" style={{ marginTop: 0 }} aria-live="polite">
            {cargando ? "Actualizando la propuesta…" : "La propuesta se actualiza sola al cambiar un dato."}
          </span>
        </div>
        <div className="fila">
          <label className="campo">
            Monto (S/)
            <input
              type="number"
              inputMode="numeric"
              min={500}
              step={100}
              value={edicion.principal}
              onChange={(e) => setEdicion({ ...edicion, principal: Number(e.target.value) })}
            />
          </label>
          <div className="campo">
            Plazo
            <div className="segmentos" role="radiogroup" aria-label="Plazo">
              {[12, 18, 24].map((m) => (
                <button
                  key={m}
                  type="button"
                  role="radio"
                  aria-checked={edicion.plazo === m}
                  onClick={() => setEdicion({ ...edicion, plazo: m })}
                >
                  {m} m
                </button>
              ))}
            </div>
          </div>
          <label className="campo" style={{ minWidth: 240 }}>
            Ventas según tu visita: {textoAjuste(edicion.ajuste_asesor)}
            <input
              type="range"
              min={0.9}
              max={1.1}
              step={0.01}
              value={edicion.ajuste_asesor}
              onChange={(e) => setEdicion({ ...edicion, ajuste_asesor: Number(e.target.value) })}
            />
          </label>
          {sugerido !== null && !cargando && (
            <button type="button" className="btn" onClick={() => setEdicion({ ...edicion, ...sugerido })}>
              Usar la propuesta ({fmtS0(sugerido.principal)} a {sugerido.plazo} m)
            </button>
          )}
          {cambiado && (
            <button
              type="button"
              className="btn-enlace"
              onClick={() => setEdicion({ principal: base.principal, plazo: base.plazo, ajuste_asesor: base.ajuste_asesor })}
            >
              Volver a lo solicitado
            </button>
          )}
        </div>
        {edicion.principal < 500 && <div className="aviso" style={{ marginTop: 10 }}>El monto mínimo es S/ 500.</div>}
      </div>

      {error && <div className="aviso">{error}</div>}
      {!resp && cargando && <div className="cargando">El agente está evaluando la solicitud…</div>}

      {resp && p && cliente && (
        <div style={{ opacity: cargando ? 0.55 : 1, transition: "opacity .2s" }} className="rejilla">
          <ChatAgente
            key={JSON.stringify([cliente.cliente_id, cliente.principal, cliente.plazo, cliente.ajuste_asesor])}
            cliente={cliente}
            deshabilitado={cargando}
          />

          <ResumenDecision
            p={p}
            fija={resp.comparativa.fija}
            flex={resp.comparativa.cuotaflex}
            onRegistrar={() => irA(refRegistro)}
            onVerCronograma={() => {
              setPestana("cronograma");
              irA(refPestanas);
            }}
          />

          <div className="tarjeta" ref={refPestanas} style={{ scrollMarginTop: 12 }}>
            <div className="pestanas" role="tablist" aria-label="Detalle de la propuesta">
              {PESTANAS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={pestana === t.id}
                  onClick={() => setPestana(t.id)}
                >
                  {t.texto}
                </button>
              ))}
            </div>
            <div role="tabpanel" style={{ marginTop: 14 }}>
              {pestana === "cuotas" && (
                <>
                  <p className="ayuda" style={{ marginTop: 0 }}>
                    Barras: lo que pagaría cada mes. Línea roja: lo que el negocio puede pagar en un mes flojo. En ámbar,
                    los meses en que la cuota fija se pasa de esa línea.
                  </p>
                  <GraficoCuotas
                    fija={resp.comparativa.fija.cuotas}
                    flex={resp.comparativa.cuotaflex.cuotas}
                    capacidad={resp.capacidad}
                    mesInicio={cliente.mes_desembolso}
                  />
                </>
              )}
              {pestana === "ventas" && (
                <>
                  <p className="ayuda" style={{ marginTop: 0 }}>
                    Línea negra: ventas de los últimos meses. Punteada: lo que se espera vender. Sombra: rango probable.
                  </p>
                  <GraficoVentas
                    historial={resp.historial_ventas}
                    pronostico={resp.pronostico}
                    mesInicio={cliente.mes_desembolso}
                  />
                </>
              )}
              {pestana === "riesgo" && (
                <Comparativa fija={resp.comparativa.fija} flex={resp.comparativa.cuotaflex} n={resp.comparativa.n_escenarios} />
              )}
              {pestana === "cronograma" && <TablaCronograma filas={p.cronograma} capacidad={resp.capacidad} />}
              {pestana === "agente" && <Bitacora pasos={p.bitacora} />}
            </div>
          </div>

          <div ref={refRegistro} style={{ scrollMarginTop: 12 }}>
            <RegistroCore key={JSON.stringify(edicion) + p.plazo} cliente={cliente} propuesta={p} />
          </div>
        </div>
      )}
    </div>
  );
}
