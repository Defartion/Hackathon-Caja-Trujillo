import { useState } from "react";
import type { AjusteSugerido, CicloRespuesta, PlanRespuesta } from "../../contratos";
import { Campo, EntradaNumero } from "./campos";
import { CuotaUnPorEtapa, Indicadores, ResumenComparado, TablaEstres } from "./Comparacion";
import { filasGraficoPlan } from "./datos";
import { AjustesSugeridos, BitacoraPlan } from "./Detalles";
import GraficoPlan from "./GraficoPlan";
import { estadoPlan } from "./formato";
import type { Errores, FormCredito, IdProducto } from "./formularios";
import { PLAZO_MAX, PLAZO_MIN, PRODUCTOS } from "./formularios";
import TablaPlan, { LeyendaSemaforo } from "./TablaPlan";

interface Props {
  credito: FormCredito;
  cambiar: (c: FormCredito) => void;
  errores: Errores;
  ciclo: CicloRespuesta;
  respuesta: PlanRespuesta | null;
  factor: number;
  calculando: boolean;
  /** Hay datos inválidos: lo que se ve corresponde a los últimos datos válidos. */
  desactualizado: boolean;
  error: string | null;
  alAplicarAjuste: (a: AjusteSugerido) => void;
  ajustesAplicados: string[];
}

export function FormularioCredito({ credito: c, cambiar, errores }: Pick<Props, "credito" | "cambiar" | "errores">) {
  const set = <K extends keyof FormCredito>(k: K, v: FormCredito[K]) => cambiar({ ...c, [k]: v });
  const prod = PRODUCTOS[c.producto];
  return (
    <div className="pl-campos" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(175px, 1fr))" }}>
      <Campo etiqueta="Monto" error={errores.monto}>
        {(id, d) => <EntradaNumero id={id} describe={d} valor={c.monto} cambiar={(v) => set("monto", v)} prefijo="S/" paso="100" placeholder="7000" />}
      </Campo>
      <Campo etiqueta="TEA" error={errores.tea_pct} ayuda={errores.tea_pct ? undefined : `Editable. Tope del producto: ${((prod.tope_tea ?? 0) * 100).toFixed(2)}%.`}>
        {(id, d) => <EntradaNumero id={id} describe={d} valor={c.tea_pct} cambiar={(v) => set("tea_pct", v)} sufijo="%" paso="0.5" />}
      </Campo>
      <Campo etiqueta="Plazo" error={errores.plazo} ayuda={errores.plazo ? undefined : "Al cambiarlo se vuelve a estimar el ciclo."}>
        {(id, d) => <EntradaNumero id={id} describe={d} valor={c.plazo} cambiar={(v) => set("plazo", v)} sufijo="meses" paso="1" min={PLAZO_MIN} max={PLAZO_MAX} />}
      </Campo>
      <Campo etiqueta="Producto">
        {(id, d) => (
          <select
            id={id}
            aria-describedby={d}
            value={c.producto}
            onChange={(e) => {
              const p = e.target.value as IdProducto;
              cambiar({ ...c, producto: p, factor: PRODUCTOS[p].factor.toFixed(2) });
            }}
          >
            {(Object.keys(PRODUCTOS) as IdProducto[]).map((k) => (
              <option key={k} value={k}>
                {PRODUCTOS[k].nombre} ({PRODUCTOS[k].factor.toFixed(2)})
              </option>
            ))}
          </select>
        )}
      </Campo>
      <Campo etiqueta="Factor Cuota/UN" error={errores.factor} ayuda={errores.factor ? undefined : `Puedes bajarlo (máx. ${prod.factor.toFixed(2)}) para dar más holgura.`}>
        {(id, d) => <EntradaNumero id={id} describe={d} valor={c.factor} cambiar={(v) => set("factor", v)} paso="0.01" min={0.1} max={prod.factor} />}
      </Campo>
      <Campo etiqueta="Desgravamen" error={errores.desgravamen_pct} ayuda="% mensual sobre el saldo de capital.">
        {(id, d) => (
          <div className="pl-prefijo">
            <span>
              <input type="checkbox" checked={c.desgravamen} onChange={(e) => set("desgravamen", e.target.checked)} aria-label="Incluir seguro de desgravamen" style={{ width: 16, height: 16, minHeight: 0, verticalAlign: "middle" }} />
            </span>
            <input id={id} aria-describedby={d} type="number" step="0.001" min={0} value={c.desgravamen_pct} disabled={!c.desgravamen} onChange={(e) => set("desgravamen_pct", e.target.value)} />
            <span className="suf">%</span>
          </div>
        )}
      </Campo>
      <Campo etiqueta="Multirriesgo" error={errores.multirriesgo_pct} ayuda="% mensual sobre el valor asegurable.">
        {(id, d) => (
          <div className="pl-prefijo">
            <span>
              <input type="checkbox" checked={c.multirriesgo} onChange={(e) => set("multirriesgo", e.target.checked)} aria-label="Incluir seguro multirriesgo" style={{ width: 16, height: 16, minHeight: 0, verticalAlign: "middle" }} />
            </span>
            <input id={id} aria-describedby={d} type="number" step="0.001" min={0} value={c.multirriesgo_pct} disabled={!c.multirriesgo} onChange={(e) => set("multirriesgo_pct", e.target.value)} />
            <span className="suf">%</span>
          </div>
        )}
      </Campo>
      <Campo etiqueta="Valor asegurable" error={errores.valor_asegurable} ayuda="Bien cubierto por el multirriesgo.">
        {(id, d) => <EntradaNumero id={id} describe={d} valor={c.valor_asegurable} cambiar={(v) => set("valor_asegurable", v)} prefijo="S/" paso="500" deshabilitada={!c.multirriesgo} />}
      </Campo>
    </div>
  );
}

/** Paso 3: datos del crédito y plan propuesto frente a la cuota fija. */
export default function PasoPlan(p: Props) {
  const [vista, setVista] = useState<"adaptado" | "fija">("adaptado");
  const r = p.respuesta;
  const estado = r ? estadoPlan(r, p.factor) : null;
  const tabla = r ? (vista === "adaptado" && r.plan ? r.plan : r.plan_cuota_fija) : null;
  const vistaReal = r?.plan && vista === "adaptado" ? "adaptado" : "fija";

  return (
    <div className="rejilla">
      <div className="tarjeta">
        <div className="fila" style={{ marginBottom: 12, alignItems: "baseline" }}>
          <h2 style={{ margin: 0 }}>Datos del crédito</h2>
          <span className="pl-estado-calculo" aria-live="polite">
            {p.calculando
              ? "Proponiendo el plan…"
              : p.desactualizado
                ? "Corrige los datos marcados para actualizar el plan."
                : r
                  ? "Plan actualizado con estos datos."
                  : ""}
          </span>
        </div>
        <FormularioCredito credito={p.credito} cambiar={p.cambiar} errores={p.errores} />
        {p.ajustesAplicados.length > 0 && (
          <div className="pl-ajustes-aplicados" style={{ marginTop: 12 }}>
            Ajustes aplicados: {p.ajustesAplicados.join(" · ")}
          </div>
        )}
      </div>

      {p.error && <div className="aviso" role="alert">{p.error}</div>}
      {!r && p.calculando && <div className="cargando">El motor está construyendo el plan…</div>}

      {r && estado && (
        <div className={`rejilla ${p.calculando || p.desactualizado ? "pl-recalculando" : ""}`} aria-busy={p.calculando}>
          <div className={`pl-estado ${estado.ok ? "ok" : "mal"}`} data-testid="estado-plan">
            <span aria-hidden="true">{estado.ok ? "✓" : "✕"}</span>
            {estado.texto}
            {r.plan && (
              <span className="det">
                · {r.plan.resumen.meses_gracia} meses de gracia · deuda en 0 al mes {r.plan.periodos.length}
              </span>
            )}
          </div>
          {!r.factible && <AjustesSugeridos ajustes={r.ajustes_sugeridos} alAplicar={p.alAplicarAjuste} ocupado={p.calculando} />}
          <Indicadores r={r} factor={p.factor} />
          <div className="tarjeta">
            <h2>Cuotas del plan frente a la cuota fija</h2>
            <GraficoPlan filas={filasGraficoPlan(p.ciclo, r, p.factor)} factor={p.factor} alto={290} />
          </div>
          <div className="pl-r-resumen">
            <div className="tarjeta">
              <h2>Resumen comparado</h2>
              <ResumenComparado r={r} />
            </div>
            <div className="tarjeta">
              <h2>Cuota/UN por etapa</h2>
              <CuotaUnPorEtapa adaptado={r.plan} fija={r.plan_cuota_fija} factor={p.factor} />
            </div>
          </div>
          <div className="tarjeta">
            <h2>Escenarios adversos: plan adaptado frente a la cuota fija</h2>
            <TablaEstres estres={r.estres} />
          </div>
          {tabla && (
            <div className="tarjeta">
              <div className="fila" style={{ marginBottom: 6, alignItems: "center" }}>
                <h2 style={{ margin: 0 }}>Cronograma por periodo</h2>
                <div className="pl-pestanas" role="tablist" aria-label="Plan a mostrar">
                  <button type="button" role="tab" aria-selected={vistaReal === "adaptado"} disabled={!r.plan} onClick={() => setVista("adaptado")}>
                    Plan adaptado
                  </button>
                  <button type="button" role="tab" aria-selected={vistaReal === "fija"} onClick={() => setVista("fija")}>
                    Cuota fija
                  </button>
                </div>
              </div>
              <LeyendaSemaforo factor={p.factor} />
              <TablaPlan plan={tabla} factor={p.factor} titulo={vistaReal === "adaptado" ? "Cronograma del plan adaptado" : "Cronograma de la cuota fija"} />
            </div>
          )}
          {r.bitacora && r.bitacora.length > 0 && <BitacoraPlan pasos={r.bitacora} />}
        </div>
      )}
    </div>
  );
}
