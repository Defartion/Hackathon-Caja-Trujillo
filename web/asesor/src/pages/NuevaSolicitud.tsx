// Fase 4 · Lote C: el Asesor de Negocios estima el ciclo y, en el mismo lugar, propone el plan.
// Paso 1 negocio y captura → paso 2 ciclo estimado (POST /ciclo/estimar) → paso 3 crédito y plan
// (POST /plan/proponer, cada vez que cambian los datos). Al final guarda el expediente del comité.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiPlan, MODO_MOCK, MOCK_MONTO_MAXIMO } from "../apiPlan";
import type { AjusteSugerido, CatalogoCiclo, CicloRespuesta, CicloSolicitud, PlanRespuesta, PlanSolicitud } from "../contratos";
import { valorAjuste } from "../contratos";
import { fmtS0 } from "../formato";
import { casoPorId, CasoEstrella, copiar } from "../components/plan/casos";
import { AjusteAplicado, guardarExpediente, leerExpediente } from "../components/plan/expedientes";
import {
  conCiclo,
  creditoPorDefecto,
  FormCredito,
  FormNegocio,
  negocioVacio,
  numero,
  validarCredito,
  validarNegocio,
} from "../components/plan/formularios";
import PasoCiclo from "../components/plan/PasoCiclo";
import PasoNegocio from "../components/plan/PasoNegocio";
import PasoPlan from "../components/plan/PasoPlan";
import "../components/plan/plan.css";

type Paso = 1 | 2 | 3;

interface Borrador {
  paso: Paso;
  negocio: FormNegocio;
  credito: FormCredito;
  cicloSol: CicloSolicitud | null;
  ciclo: CicloRespuesta | null;
  ajustes: AjusteAplicado[];
}

// Borrador en memoria: sobrevive a ir y volver de la vista del comité dentro de la app.
let borrador: Borrador | null = null;

const PASOS: { n: Paso; t: string }[] = [
  { n: 1, t: "Negocio" },
  { n: 2, t: "Ciclo estimado" },
  { n: 3, t: "Crédito y plan" },
];

const ESPERA_MS = 350;

function inicial(caso: CasoEstrella | undefined, desde: string | null): Borrador {
  if (desde) {
    const e = leerExpediente(desde);
    if (e)
      return {
        paso: 3,
        negocio: e.negocio,
        credito: e.credito,
        cicloSol: e.cicloSolicitud,
        ciclo: e.ciclo,
        ajustes: e.ajustes,
      };
  }
  if (caso) return { paso: 1, negocio: copiar(caso.negocio), credito: copiar(caso.credito), cicloSol: null, ciclo: null, ajustes: [] };
  return borrador ?? { paso: 1, negocio: negocioVacio(), credito: creditoPorDefecto(), cicloSol: null, ciclo: null, ajustes: [] };
}

export default function NuevaSolicitud() {
  const [busqueda] = useSearchParams();
  const nav = useNavigate();
  const arranque = useMemo(() => inicial(casoPorId(busqueda.get("caso") ?? undefined), busqueda.get("desde")), []);

  const [paso, setPaso] = useState<Paso>(arranque.paso);
  const [negocio, setNegocio] = useState<FormNegocio>(arranque.negocio);
  const [credito, setCredito] = useState<FormCredito>(arranque.credito);
  const [cicloSol, setCicloSol] = useState<CicloSolicitud | null>(arranque.cicloSol);
  const [ciclo, setCiclo] = useState<CicloRespuesta | null>(arranque.ciclo);
  const [ajustes, setAjustes] = useState<AjusteAplicado[]>(arranque.ajustes);
  const [versionCiclo, setVersionCiclo] = useState(0);

  const [catalogo, setCatalogo] = useState<CatalogoCiclo | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);
  const [intentado, setIntentado] = useState(false);
  const [estimando, setEstimando] = useState(false);
  const [errorCiclo, setErrorCiclo] = useState<string | null>(null);

  const [respuesta, setRespuesta] = useState<PlanRespuesta | null>(null);
  const [solicitudUsada, setSolicitudUsada] = useState<Omit<PlanSolicitud, "ciclo"> | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [errorPlan, setErrorPlan] = useState<string | null>(null);
  const secuencia = useRef(0);
  const cicloRef = useRef({ ciclo, cicloSol });
  cicloRef.current = { ciclo, cicloSol };

  useEffect(() => {
    borrador = { paso, negocio, credito, cicloSol, ciclo, ajustes };
  }, [paso, negocio, credito, cicloSol, ciclo, ajustes]);

  useEffect(() => {
    let vivo = true;
    apiPlan
      .catalogo()
      .then((c) => vivo && setCatalogo(c))
      .catch((e: Error) => vivo && setErrorCatalogo(`No se pudo cargar el catálogo de actividades. ${e.message}`));
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [paso]);

  const valNegocio = useMemo(() => validarNegocio(negocio), [negocio]);
  // El plan usa la fecha del ciclo vigente: si el asesor cambia el paso 1, debe volver a estimar.
  const fechaDesembolso = cicloSol?.fecha_inicio ?? negocio.fecha_inicio;
  const valCredito = useMemo(() => validarCredito(credito, fechaDesembolso), [credito, fechaDesembolso]);
  const cicloVigente = !!ciclo && !!cicloSol && JSON.stringify(valNegocio.solicitud) === JSON.stringify(cicloSol);

  function cargarCaso(c: CasoEstrella) {
    secuencia.current += 1;
    setNegocio(copiar(c.negocio));
    setCredito(copiar(c.credito));
    setCiclo(null);
    setCicloSol(null);
    setRespuesta(null);
    setSolicitudUsada(null);
    setAjustes([]);
    setIntentado(false);
    setErrorCiclo(null);
    setErrorPlan(null);
  }

  function empezarDeNuevo() {
    cargarCaso({ id: "", nombre: "", resumen: "", negocio: negocioVacio(), credito: creditoPorDefecto() });
    setPaso(1);
  }

  async function estimar() {
    setIntentado(true);
    const sol = valNegocio.solicitud;
    if (!sol) return;
    setEstimando(true);
    setErrorCiclo(null);
    try {
      const c = await apiPlan.estimarCiclo(sol);
      setCiclo(c);
      setCicloSol(sol);
      setRespuesta(null);
      setSolicitudUsada(null);
      setVersionCiclo((v) => v + 1);
      setCredito((cr) => (cr.plazo === String(sol.meses) ? cr : { ...cr, plazo: String(sol.meses) }));
      setPaso(2);
    } catch (e) {
      setErrorCiclo((e as Error).message);
    } finally {
      setEstimando(false);
    }
  }

  const proponer = useCallback(async (sol: Omit<PlanSolicitud, "ciclo">) => {
    const { ciclo: c0, cicloSol: s0 } = cicloRef.current;
    if (!c0 || !s0) return;
    const yo = ++secuencia.current;
    setCalculando(true);
    setErrorPlan(null);
    try {
      let c = c0;
      if (sol.plazo_meses !== c0.meses) {
        // El horizonte del ciclo es el plazo del crédito: se vuelve a estimar.
        const s = { ...s0, meses: sol.plazo_meses };
        c = await apiPlan.estimarCiclo(s);
        if (yo !== secuencia.current) return;
        setCiclo(c);
        setCicloSol(s);
        setNegocio((n) => ({ ...n, meses: String(sol.plazo_meses) }));
      }
      const r = await apiPlan.proponerPlan(conCiclo(sol, c));
      if (yo !== secuencia.current) return;
      setRespuesta(r);
      setSolicitudUsada(sol);
    } catch (e) {
      if (yo === secuencia.current) setErrorPlan((e as Error).message);
    } finally {
      if (yo === secuencia.current) setCalculando(false);
    }
  }, []);

  // Paso 3: cada cambio en los datos del crédito vuelve a proponer el plan (con una espera corta).
  const claveCredito = JSON.stringify(valCredito.solicitud);
  useEffect(() => {
    if (paso !== 3 || !ciclo) return;
    const sol = valCredito.solicitud;
    if (!sol) {
      secuencia.current += 1;
      setCalculando(false);
      return;
    }
    const t = window.setTimeout(() => void proponer(sol), respuesta ? ESPERA_MS : 0);
    return () => window.clearTimeout(t);
  }, [paso, claveCredito, versionCiclo, proponer]);

  function aplicarAjuste(a: AjusteSugerido) {
    const v = valorAjuste(a);
    if (v == null) return;
    let nuevo: AjusteAplicado | null = null;
    if (a.tipo === "reducir_monto") {
      const monto = numero(credito.monto);
      nuevo = { campo: "monto", antes: credito.monto, despues: String(v), texto: `Monto de ${monto != null ? fmtS0(monto) : "?"} a ${fmtS0(v)}` };
    } else if (a.tipo === "ampliar_plazo") {
      nuevo = { campo: "plazo", antes: credito.plazo, despues: String(Math.round(v)), texto: `Plazo de ${credito.plazo} a ${Math.round(v)} meses` };
    } else if (a.tipo === "bajar_factor") {
      nuevo = { campo: "factor", antes: credito.factor, despues: v.toFixed(2), texto: `Factor de ${credito.factor} a ${v.toFixed(2)}` };
    }
    if (!nuevo) return;
    setCredito({ ...credito, [nuevo.campo]: nuevo.despues });
    setAjustes([...ajustes, { ...nuevo, texto: `${nuevo.texto} (sugerencia del motor)` }]);
  }

  // Un ajuste deja de informarse si el asesor volvió a cambiar ese dato a mano.
  const ajustesVigentes = ajustes.filter((a) => credito[a.campo] === a.despues);
  const montoAntes = ajustesVigentes.find((a) => a.campo === "monto")?.antes;

  const actualizado = !!respuesta && !!solicitudUsada && JSON.stringify(solicitudUsada) === claveCredito && !calculando;
  // Datos válidos que todavía no tienen respuesta (espera corta o llamada en curso).
  const pendiente = !!valCredito.solicitud && !actualizado && !errorPlan;

  function enviarAlComite() {
    if (!respuesta || !solicitudUsada || !ciclo || !cicloSol || !actualizado) return;
    const id = cicloSol.cliente_id;
    guardarExpediente({
      version: 1,
      id,
      creado: new Date().toISOString(),
      modo: MODO_MOCK ? "mock" : "api",
      negocio,
      credito,
      cicloSolicitud: cicloSol,
      ciclo,
      planSolicitud: solicitudUsada,
      plan: respuesta,
      montoSolicitado: numero(montoAntes ?? "") ?? solicitudUsada.monto,
      ajustes: ajustesVigentes,
    });
    nav(`/comite/${encodeURIComponent(id)}`);
  }

  function irA(n: Paso) {
    if (n === 1 || cicloVigente) setPaso(n);
  }

  function ajustarMeses() {
    setPaso(1);
    window.setTimeout(() => document.getElementById("sec-ventas")?.scrollIntoView({ block: "start" }), 50);
  }

  const factor = solicitudUsada?.producto.factor ?? numero(credito.factor) ?? 0.85;

  return (
    <div className="pl-asistente">
      <div className="pl-cabecera">
        <Link to="/">← Bandeja</Link>
        <h1>Nueva solicitud</h1>
        <ol className="pl-pasos" aria-label="Pasos">
          {PASOS.map((p) => (
            <li key={p.n} className={`pl-paso ${paso === p.n ? "activo" : paso > p.n ? "hecho" : ""}`} aria-current={paso === p.n ? "step" : undefined}>
              <button type="button" onClick={() => irA(p.n)} disabled={p.n > 1 && !cicloVigente}>
                <span className="num">{paso > p.n ? "✓" : p.n}</span>
                {p.t}
              </button>
            </li>
          ))}
        </ol>
        <div className="espacio" style={{ flex: 1 }} />
        <button type="button" className="btn" onClick={empezarDeNuevo}>
          Empezar de nuevo
        </button>
      </div>

      {MODO_MOCK && (
        <div className="pl-banner-mock" role="status">
          Modo de prueba (VITE_MOCK=1): el ciclo y el plan son los JSON de ejemplo del contrato (caso Rosa) y no cambian con la
          captura. Por encima de {fmtS0(MOCK_MONTO_MAXIMO)} el plan de ejemplo no es factible.
        </div>
      )}

      {paso === 1 && (
        <>
          <PasoNegocio
            valor={negocio}
            cambiar={setNegocio}
            catalogo={catalogo}
            errorCatalogo={errorCatalogo}
            errores={intentado ? valNegocio.errores : {}}
            avisos={valNegocio.avisos}
            alCargarCaso={cargarCaso}
          />
          {errorCiclo && <div className="aviso" role="alert">{errorCiclo}</div>}
          <div className="pl-acciones tarjeta pl-barra-acciones">
            <Link to="/" className="btn">
              Cancelar
            </Link>
            <div className="espacio" />
            {intentado && Object.keys(valNegocio.errores).length > 0 && (
              <span className="pl-error">Revisa los campos marcados ({Object.keys(valNegocio.errores).length}).</span>
            )}
            {ciclo && !cicloVigente && Object.keys(valNegocio.errores).length === 0 && (
              <span className="pl-gris">Cambiaste datos del negocio: vuelve a estimar el ciclo.</span>
            )}
            <button type="button" className="btn btn-primario" onClick={() => void estimar()} disabled={estimando}>
              {estimando ? "Estimando el ciclo…" : "Estimar ciclo →"}
            </button>
          </div>
        </>
      )}

      {paso === 2 && ciclo && (
        <>
          <PasoCiclo ciclo={ciclo} />
          <div className="pl-acciones tarjeta pl-barra-acciones">
            <button type="button" className="btn" onClick={ajustarMeses}>
              ← Ajustar meses
            </button>
            <div className="espacio" />
            <button type="button" className="btn btn-primario" onClick={() => setPaso(3)}>
              Continuar: crédito y plan →
            </button>
          </div>
        </>
      )}

      {paso === 3 && ciclo && (
        <>
          <PasoPlan
            credito={credito}
            cambiar={setCredito}
            errores={valCredito.errores}
            ciclo={ciclo}
            respuesta={respuesta}
            factor={factor}
            calculando={calculando || pendiente}
            desactualizado={!valCredito.solicitud && !!respuesta}
            error={errorPlan}
            alAplicarAjuste={aplicarAjuste}
            ajustesAplicados={ajustesVigentes.map((a) => a.texto)}
          />
          <div className="pl-acciones tarjeta pl-barra-acciones">
            <button type="button" className="btn" onClick={() => setPaso(2)}>
              ← Ver ciclo
            </button>
            <div className="espacio" />
            {respuesta && !respuesta.factible && actualizado && (
              <span className="pl-gris">Sin plan factible: el expediente informa los ajustes al comité.</span>
            )}
            <button type="button" className="btn btn-primario" onClick={enviarAlComite} disabled={!actualizado}>
              {respuesta && !respuesta.factible ? "Informar al comité →" : "Guardar y abrir la vista del comité →"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
