// Ajustes sugeridos, supuestos, fuentes y bitácora del constructor.
import type { AjusteSugerido, CicloRespuesta, PasoBitacoraPlan } from "../../contratos";
import { valorAjuste } from "../../contratos";
import { fmtPct } from "../../formato";
import { textoAjuste } from "./formato";

/** Ajustes que propone el motor cuando no hay plan factible, cada uno con su botón. */
export function AjustesSugeridos({
  ajustes,
  alAplicar,
  ocupado,
}: {
  ajustes: AjusteSugerido[];
  alAplicar?: (a: AjusteSugerido) => void;
  ocupado?: boolean;
}) {
  return (
    <div className="pl-ajustes" role="alert">
      <div className="pl-ajustes-titulo">Ajustes que sugiere el motor</div>
      {ajustes.length ? (
        <>
          <div className="pl-ajustes-ayuda">
            Ninguna combinación de cuotas respeta Cuota/UN ≤ factor en todas las etapas con estos datos.
            {alAplicar ? " Al aplicar un ajuste se vuelve a proponer el plan." : ""}
          </div>
          <ul className="pl-ajustes-lista">
            {ajustes.map((a, i) => {
              const texto = textoAjuste(a.tipo, valorAjuste(a));
              return (
                <li key={`${a.tipo}-${i}`}>
                  <span>{texto}</span>
                  {alAplicar && (
                    <button type="button" className="btn btn-primario" disabled={ocupado} onClick={() => alAplicar(a)} aria-label={`Aplicar: ${texto}`}>
                      Aplicar
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <div className="pl-ajustes-ayuda">
          El motor no encontró un ajuste de monto o plazo que lo haga factible. Revisa la captura o informa al comité.
        </div>
      )}
    </div>
  );
}

const METODO: Record<string, string> = {
  "patron_sector_zona + ajuste_asesor": "Patrón del sector y la zona ajustado con la captura del asesor",
  adaptador_pronostico_fase2: "Adaptador provisional desde el pronóstico de la fase 2",
};

/** Supuestos y fuentes del ciclo y del plan. En pantalla se despliegan; al imprimir van abiertos. */
export function SupuestosFuentes({
  ciclo,
  supuestosPlan,
  abierto = false,
}: {
  ciclo: CicloRespuesta;
  supuestosPlan?: string[];
  abierto?: boolean;
}) {
  // El plan repite al final los supuestos del ciclo: se muestran una sola vez.
  const delPlan = (supuestosPlan ?? []).filter((s) => !ciclo.supuestos.includes(s));
  return (
    <div className="pl-supuestos">
      <details open={abierto} className="pl-desplegable">
        <summary>
          Supuestos del ciclo <span className="pl-contador">{ciclo.supuestos.length}</span>
        </summary>
        <ul>
          {ciclo.supuestos.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </details>
      {delPlan.length > 0 && (
        <details open={abierto} className="pl-desplegable">
          <summary>
            Supuestos del plan <span className="pl-contador">{delPlan.length}</span>
          </summary>
          <ul>
            {delPlan.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </details>
      )}
      <details open={abierto} className="pl-desplegable">
        <summary>
          Fuentes <span className="pl-contador">{ciclo.fuentes.length}</span>
        </summary>
        <ul className="pl-fuentes">
          {ciclo.fuentes.map((f) => (
            <li key={f.nombre}>
              <strong>{f.url ? <a href={f.url} target="_blank" rel="noreferrer">{f.nombre}</a> : f.nombre}</strong>
              <span> · {f.uso}</span>
            </li>
          ))}
        </ul>
      </details>
      <div className="pl-calidad">
        Método: {METODO[ciclo.calidad.metodo] ?? ciclo.calidad.metodo} · Cobertura p10–p90 en el backtest:{" "}
        <strong>{fmtPct(ciclo.calidad.cobertura_p10_p90_backtest)}</strong> (objetivo ≈ 80%). Sin historial de pagos.
      </div>
    </div>
  );
}

function pasoLegible(p: PasoBitacoraPlan): string {
  const v = p as Record<string, unknown>;
  if (typeof v.detalle === "string") return v.detalle;
  if (p.paso === "optimizacion") return `Optimización a ${v.plazo ?? "?"} meses: ${v.estado ?? ""}`;
  if (p.paso === "ajustes") {
    const s = (v.sugeridos as AjusteSugerido[] | undefined) ?? [];
    return s.length ? `Ajustes sugeridos: ${s.map((a) => textoAjuste(a.tipo, valorAjuste(a))).join("; ")}` : "Sin ajustes factibles";
  }
  return Object.entries(v)
    .filter(([k]) => k !== "paso")
    .map(([k, x]) => `${k}: ${typeof x === "object" ? JSON.stringify(x) : String(x)}`)
    .join(" · ");
}

const PASO_TITULO: Record<string, string> = {
  restriccion: "Restricción",
  robustez: "Robustez",
  optimizacion: "Optimización",
  ajustes: "Ajustes",
};

export function BitacoraPlan({ pasos }: { pasos: PasoBitacoraPlan[] }) {
  if (!pasos.length) return null;
  return (
    <details className="pl-desplegable">
      <summary>
        Cómo se construyó el plan <span className="pl-contador">{pasos.length}</span>
      </summary>
      <ol className="pl-bitacora">
        {pasos.map((p, i) => (
          <li key={i}>
            <strong>{PASO_TITULO[p.paso] ?? p.paso}:</strong> {pasoLegible(p)}
          </li>
        ))}
      </ol>
    </details>
  );
}
