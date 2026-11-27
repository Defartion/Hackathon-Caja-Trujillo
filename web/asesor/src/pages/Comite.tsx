// Fase 4 · Lote C: vista para el Asesor de Riesgos y el comité. Página limpia e imprimible
// (A4 vertical, 2 o 3 páginas) con el ciclo, el plan, Cuota/UN por etapa, el estrés frente a la
// cuota fija, los supuestos y las fuentes. El Asesor de Riesgos valida y el comité aprueba.
import { ReactNode, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiPlan, ExplicacionAgente, MODO_MOCK, RUTA_EXPLICACION } from "../apiPlan";
import { fmtPct, fmtS0 } from "../formato";
import { casoPorId } from "../components/plan/casos";
import { CuotaUnPorEtapa, Indicadores, ResumenComparado, TablaEstres } from "../components/plan/Comparacion";
import { filasGraficoPlan } from "../components/plan/datos";
import { AjustesSugeridos, SupuestosFuentes } from "../components/plan/Detalles";
import { Expediente, leerExpediente } from "../components/plan/expedientes";
import { estadoPlan, etiquetaPeriodo, fmtFecha, fmtFechaHora, fmtTasa } from "../components/plan/formato";
import { conCiclo, validarCredito, validarNegocio } from "../components/plan/formularios";
import GraficoCiclo from "../components/plan/GraficoCiclo";
import GraficoPlan from "../components/plan/GraficoPlan";
import TablaPlan, { LeyendaSemaforo } from "../components/plan/TablaPlan";
import ValidacionRiesgos from "../components/plan/ValidacionRiesgos";
import "../components/plan/plan.css";

const ANCHO_GRAFICO = 700;
const capital = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** Calcula al vuelo un caso estrella que todavía no se guardó en este navegador. */
async function expedienteDeCaso(id: string): Promise<Expediente | null> {
  const caso = casoPorId(id);
  if (!caso) return null;
  const solCiclo = validarNegocio(caso.negocio).solicitud;
  const solPlan = validarCredito(caso.credito, caso.negocio.fecha_inicio).solicitud;
  if (!solCiclo || !solPlan) return null;
  const ciclo = await apiPlan.estimarCiclo(solCiclo);
  const plan = await apiPlan.proponerPlan(conCiclo(solPlan, ciclo));
  return {
    version: 1,
    id,
    creado: new Date().toISOString(),
    modo: MODO_MOCK ? "mock" : "api",
    negocio: caso.negocio,
    credito: caso.credito,
    cicloSolicitud: solCiclo,
    ciclo,
    planSolicitud: solPlan,
    plan,
    montoSolicitado: solPlan.monto,
    ajustes: [],
  };
}

function Seccion({ n, titulo, sub, children, clase }: { n: number; titulo: string; sub?: string; children: ReactNode; clase?: string }) {
  return (
    <section className={clase} aria-labelledby={`sec-${n}`}>
      <h2 id={`sec-${n}`}>
        <span className="n">{n}.</span> {titulo}
      </h2>
      {sub && <div className="pl-sub">{sub}</div>}
      {children}
    </section>
  );
}

export default function Comite() {
  const { id = "" } = useParams();
  const [exp, setExp] = useState<Expediente | null>(() => leerExpediente(id));
  const [calculado, setCalculado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [explicacion, setExplicacion] = useState<ExplicacionAgente | null | undefined>(undefined);

  useEffect(() => {
    document.documentElement.classList.add("modo-comite");
    return () => document.documentElement.classList.remove("modo-comite");
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [id]);

  useEffect(() => {
    const guardado = leerExpediente(id);
    setError(null);
    setCalculado(false);
    if (guardado) {
      setExp(guardado);
      return;
    }
    let vivo = true;
    setExp(null);
    expedienteDeCaso(id)
      .then((e) => {
        if (!vivo) return;
        if (e) {
          setExp(e);
          setCalculado(true);
        } else setError(`No encontramos la solicitud ${id} en este navegador.`);
      })
      .catch((e: Error) => vivo && setError(e.message));
    return () => {
      vivo = false;
    };
  }, [id]);

  useEffect(() => {
    if (!exp) return;
    let vivo = true;
    setExplicacion(undefined);
    apiPlan
      .explicacionComite({ cliente_id: exp.id, ciclo: exp.ciclo, plan: exp.plan, solicitud: exp.planSolicitud })
      .then((x) => vivo && setExplicacion(x))
      .catch(() => vivo && setExplicacion(null));
    return () => {
      vivo = false;
    };
  }, [exp]);

  if (error)
    return (
      <div className="aviso">
        {error} <Link to="/nueva">Crear una nueva solicitud</Link>
      </div>
    );
  if (!exp) return <div className="cargando">Preparando el expediente para el comité…</div>;

  const { ciclo, plan: r, planSolicitud: sol, negocio } = exp;
  const factor = sol.producto.factor;
  const estado = estadoPlan(r, factor);
  const zona = `${ciclo.zona.provincia}${ciclo.zona.distrito ? ` · ${ciclo.zona.distrito}` : ""} (${ciclo.zona.departamento})`;
  const ps = ciclo.periodos;
  const anio = ps.slice(0, 12);
  const sinUn = ps.filter((p) => p.un_p50 <= 0).length;
  const seguros = [
    sol.seguros.desgravamen.activo ? `Desgravamen ${fmtTasa(sol.seguros.desgravamen.tasa_mensual, 3)} mensual` : null,
    sol.seguros.multirriesgo.activo
      ? `Multirriesgo ${fmtTasa(sol.seguros.multirriesgo.tasa_mensual, 3)} sobre ${fmtS0(sol.seguros.multirriesgo.valor_asegurable)}`
      : null,
  ].filter(Boolean);
  const montoCambio = exp.montoSolicitado !== sol.monto;
  const tabla = r.plan ?? r.plan_cuota_fija;

  return (
    <div className="pl-comite-fondo">
      <div className="pl-herramientas">
        <Link to="/nueva" className="btn">
          ← Nueva solicitud
        </Link>
        <Link to={`/nueva?desde=${encodeURIComponent(exp.id)}`} className="btn" aria-disabled={calculado} onClick={(e) => calculado && e.preventDefault()}>
          Editar solicitud
        </Link>
        <div className="espacio" />
        {MODO_MOCK && <span className="pl-gris">Modo de prueba: datos de ejemplo del contrato</span>}
        <button type="button" className="btn btn-primario" onClick={() => window.print()}>
          Imprimir o guardar en PDF
        </button>
      </div>

      <article className="pl-comite cf-claro" aria-label={`Expediente ${exp.id} para el comité`}>
        <header className="rejilla" style={{ gap: 12 }}>
          <div className="pl-membrete">
            <div className="marca">
              Thinku · Expediente para el comité de créditos
            </div>
            <div className="doc">
              Elaborado el {fmtFechaHora(exp.creado).slice(0, 10)}
              <br />
              Datos sintéticos · prototipo
            </div>
          </div>
          <h1>
            Solicitud {exp.id}
            {negocio.nombre ? ` · ${negocio.nombre}` : ""}
          </h1>
          <div className="pl-ficha">
            <div>
              <div className="k">Actividad</div>
              <div className="v">
                {capital(ciclo.actividad)} · {capital(ciclo.sector)}
              </div>
            </div>
            <div>
              <div className="k">Zona</div>
              <div className="v">{zona}</div>
            </div>
            <div>
              <div className="k">Monto</div>
              <div className="v">
                {fmtS0(sol.monto)}
                {montoCambio && <span className="pl-gris"> (pidió {fmtS0(exp.montoSolicitado)})</span>}
              </div>
            </div>
            <div>
              <div className="k">Plazo · desembolso</div>
              <div className="v">
                {sol.plazo_meses} meses · {fmtFecha(sol.fecha_desembolso)}
              </div>
            </div>
            <div>
              <div className="k">TEA · TCEA</div>
              <div className="v">
                {fmtTasa(sol.tea)} · {r.plan ? fmtTasa(r.plan.resumen.tcea) : "—"}
              </div>
            </div>
            <div>
              <div className="k">Producto · factor</div>
              <div className="v">
                {sol.producto.nombre} · {factor.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="k">Seguros</div>
              <div className="v" style={{ fontSize: 12 }}>
                {seguros.length ? seguros.join(" · ") : "Sin seguros"}
              </div>
            </div>
            <div>
              <div className="k">Propone</div>
              <div className="v">Asesor de Negocios</div>
            </div>
          </div>
          {exp.ajustes.length > 0 && (
            <div className="pl-ajustes-aplicados">Ajustes aplicados por el asesor: {exp.ajustes.map((a) => a.texto).join(" · ")}</div>
          )}
          <div className={`pl-estado ${estado.ok ? "ok" : "mal"}`} data-testid="estado-comite">
            <span aria-hidden="true">{estado.ok ? "✓" : "✕"}</span>
            {estado.texto}
            {r.plan && r.plan_cuota_fija && (
              <span className="det">
                · {r.plan.resumen.etapas_sobre_factor} etapas sobre el factor (cuota fija: {r.plan_cuota_fija.resumen.etapas_sobre_factor})
              </span>
            )}
          </div>
        </header>

        <Seccion
          n={1}
          titulo="Ciclo económico estimado"
          sub={`Utilidad neta mensual (UN) de ${etiquetaPeriodo(ps[0]?.periodo ?? "")} a ${etiquetaPeriodo(ps[ps.length - 1]?.periodo ?? "")}: patrón del sector y la zona ajustado con la captura del asesor, sin historial de pagos.`}
        >
          <GraficoCiclo periodos={ps} ancho={ANCHO_GRAFICO} alto={190} />
          <div className="pl-calidad">
            UN esperada en {anio.length} meses: <strong>{fmtS0(anio.reduce((s, p) => s + p.un_p50, 0))}</strong> · {ps.filter((p) => p.etapa === "cima").length} meses en
            cima y {ps.filter((p) => p.etapa === "valle").length} en valle · {sinUn} meses con UN ≤ 0 · cobertura p10–p90 en el backtest:{" "}
            {fmtPct(ciclo.calidad.cobertura_p10_p90_backtest)}
          </div>
        </Seccion>

        <Seccion n={2} titulo="Plan propuesto frente a la cuota fija" sub={`Tope de cada mes: factor ${factor.toFixed(2)} × UN esperada. Con UN ≤ 0 la cuota debe ser 0 (gracia).`}>
          <div className="rejilla" style={{ gap: 10 }}>
            <Indicadores r={r} factor={factor} />
            {!r.factible && <AjustesSugeridos ajustes={r.ajustes_sugeridos} />}
            <GraficoPlan filas={filasGraficoPlan(ciclo, r, factor)} factor={factor} ancho={ANCHO_GRAFICO} alto={200} />
          </div>
        </Seccion>

        <Seccion n={3} titulo="Cuota/UN por etapa" sub="Máximo Cuota/UN de cada etapa frente al factor del producto.">
          <CuotaUnPorEtapa adaptado={r.plan} fija={r.plan_cuota_fija} factor={factor} />
        </Seccion>

        <Seccion n={4} titulo="Escenarios adversos" sub="Los dos planes contra la UN de cada escenario del ciclo.">
          <TablaEstres estres={r.estres} />
        </Seccion>

        {tabla && (
          <Seccion
            n={5}
            titulo={r.plan ? "Cronograma del plan adaptado" : "Cronograma de la cuota fija (no hay plan adaptado factible)"}
            sub="Prelación: seguros → interés → capital. Lo pendiente no capitaliza: suma a la deuda, no al saldo de capital."
          >
            <LeyendaSemaforo factor={factor} />
            <TablaPlan plan={tabla} factor={factor} variante="compacta" titulo="Cronograma para el comité" />
          </Seccion>
        )}

        <Seccion n={6} titulo="Costos comparados">
          <ResumenComparado r={r} />
        </Seccion>

        <Seccion n={7} titulo="Supuestos y fuentes" clase="puede-partirse">
          <SupuestosFuentes ciclo={ciclo} supuestosPlan={r.supuestos} abierto />
        </Seccion>

        <Seccion n={8} titulo="Explicación del agente">
          {explicacion === undefined && <div className="pl-reservado">Consultando al agente…</div>}
          {explicacion === null && (
            <div className="pl-reservado" data-testid="explicacion-reservada">
              Espacio reservado para la explicación del agente de Thinku ({RUTA_EXPLICACION}, lote D). Cuando esté disponible, aquí va
              un resumen con cifras verificadas del ciclo, el plan y el estrés.
            </div>
          )}
          {explicacion && (
            <div className="pl-explicacion">
              {explicacion.texto}
              {explicacion.verificada != null && (
                <div className="pl-gris" style={{ marginTop: 6 }}>
                  {explicacion.verificada ? "✓ Cifras verificadas contra el ciclo y el plan." : "Cifras sin verificar."}
                </div>
              )}
            </div>
          )}
        </Seccion>

        <Seccion n={9} titulo="Validación del Asesor de Riesgos y decisión del comité">
          <div className="pl-cierre">
          <ValidacionRiesgos key={exp.id} id={exp.id} />
          <div className="pl-validacion">
            <strong>Comité de créditos</strong>
            <div className="pl-casillas">
              <span>☐ Aprobado</span>
              <span>☐ Observado</span>
              <span>☐ Rechazado</span>
            </div>
            <div className="pl-firmas">
              <div className="pl-firma">Firma de los miembros del comité</div>
              <div className="pl-firma">Fecha</div>
            </div>
          </div>
          </div>
        </Seccion>

        <footer className="pl-pie">
          Thinku · Cajathón 2026 (NEG-01) · Expediente {exp.id} · {exp.modo === "mock" ? "datos de ejemplo del contrato" : "ciclo y plan calculados por la API"}
          {calculado ? " · caso de demostración calculado al abrir" : ""} · generado el {fmtFechaHora(exp.creado)}. Solo datos sintéticos: no
          se conecta a la Caja.
        </footer>
      </article>
    </div>
  );
}
