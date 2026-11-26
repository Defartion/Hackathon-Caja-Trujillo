import { useState, type ReactNode } from "react";
import { PasoBitacora } from "../api";
import { fmtPct, fmtS0 } from "../formato";

const CHEQUEOS: Record<string, string> = {
  cierra_valor_presente: "El valor presente cierra el crédito (rentabilidad)",
  respeta_piso: "Ninguna cuota bajo el piso",
  respeta_techo: "Ninguna cuota sobre el techo (sin cuota globo)",
  meses_reducidos_ok: "Meses con cuota reducida dentro de política",
  carga_mediana_ok: "Carga mediana cuota/excedente dentro de política",
};

const PRODUCTOS: Record<string, string> = {
  fija: "cuota fija",
  aplazamiento: "cuota fija con aplazamientos",
  estacional: "cuotas estacionales",
};

function describir(p: PasoBitacora): { titulo: string; detalle: ReactNode; clase: string } {
  const v = p as Record<string, unknown>;
  switch (p.paso) {
    case "elegibilidad": {
      const motivos = (v.motivos as string[]) ?? [];
      return {
        titulo: v.elegible_flex ? "Elegible para flexibilidad" : "No elegible para flexibilidad",
        detalle: (
          <>
            Carga de deuda: {fmtPct(Number(v.ratio_deuda))} del excedente.
            {motivos.length > 0 && <div>Motivos: {motivos.join("; ")}</div>}
          </>
        ),
        clase: v.elegible_flex ? "ok" : "mal",
      };
    }
    case "seleccion": {
      const cand = (v.candidatos as Record<string, { default: number; mora30: number; vpn: number }>) ?? {};
      return {
        titulo: `Selección por simulación: ${PRODUCTOS[String(v.elegido)] ?? v.elegido}`,
        detalle: (
          <div>
            {Object.entries(cand).map(([prod, m]) => (
              <div key={prod} style={{ fontWeight: prod === v.elegido ? 600 : 400 }}>
                {prod === v.elegido ? "★ " : ""}
                {PRODUCTOS[prod] ?? prod}: incumplimiento {fmtPct(m.default)} · atraso {fmtPct(m.mora30)} · ganancia {fmtS0(m.vpn)}
              </div>
            ))}
            <div>Criterio: menor incumplimiento sin perder rentabilidad</div>
          </div>
        ),
        clase: "ok",
      };
    }
    case "producto":
      return { titulo: `Producto elegido: ${PRODUCTOS[String(v.producto)] ?? v.producto}`, detalle: null, clase: "" };
    case "cronograma": {
      const def = Number(v.deficit_p25);
      const ok = def <= 0.02 * Number(v.principal);
      return {
        titulo: `Cronograma a ${v.plazo} meses por ${fmtS0(Number(v.principal))}`,
        detalle: ok ? "Cabe en la capacidad del escenario conservador." : `Excede la capacidad en ${fmtS0(def)}: se replanifica.`,
        clase: ok ? "ok" : "re",
      };
    }
    case "replanificar":
      return { titulo: `Replanificación: ${v.accion}`, detalle: `Nuevo monto: ${fmtS0(Number(v.nuevo_principal))}`, clase: "re" };
    case "validacion": {
      const ch = (v.chequeos as Record<string, boolean>) ?? {};
      return {
        titulo: v.valido ? "Validación de políticas superada" : "Validación con observaciones",
        detalle: (
          <div>
            {Object.entries(ch).map(([k, ok]) => (
              <div key={k}>
                <span className={ok ? "mejor" : "peor"}>{ok ? "✓" : "✗"}</span> {CHEQUEOS[k] ?? k}
              </div>
            ))}
          </div>
        ),
        clase: v.valido ? "ok" : "mal",
      };
    }
    default:
      return { titulo: p.paso, detalle: JSON.stringify(p), clase: "" };
  }
}

type Item = { titulo: string; detalle: ReactNode; clase: string; sub?: Item[] };

/** Junta los intentos de cronograma y replanificación en un solo paso que se puede desplegar. */
function agrupar(pasos: PasoBitacora[]): Item[] {
  const out: Item[] = [];
  let grupo: PasoBitacora[] = [];
  const cerrar = () => {
    if (grupo.length === 0) return;
    const crons = grupo.filter((g) => g.paso === "cronograma") as Record<string, unknown>[];
    const ini = Number(crons[0]?.principal);
    const fin = Number(crons[crons.length - 1]?.principal);
    const intentos = grupo.filter((g) => g.paso === "replanificar").length;
    const ult = describir(grupo[grupo.length - 1]);
    out.push({
      titulo:
        intentos === 0
          ? `Cronograma a ${crons[0]?.plazo} meses por ${fmtS0(ini)}`
          : `Ajuste del monto: ${fmtS0(ini)} → ${fmtS0(fin)} (${intentos} ${intentos === 1 ? "intento" : "intentos"})`,
      detalle: intentos === 0 ? ult.detalle : "Bajó el monto hasta que la cuota entró en la capacidad de pago.",
      clase: ult.clase,
      sub: intentos === 0 ? undefined : grupo.map(describir),
    });
    grupo = [];
  };
  for (const p of pasos) {
    if (p.paso === "cronograma" || p.paso === "replanificar") grupo.push(p);
    else {
      cerrar();
      out.push(describir(p));
    }
  }
  cerrar();
  return out;
}

function Paso({ d }: { d: Item }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <li className={d.clase}>
      <div className="titulo">{d.titulo}</div>
      {d.detalle && <div className="detalle">{d.detalle}</div>}
      {d.sub && (
        <>
          <button type="button" className="btn-enlace" style={{ paddingLeft: 0 }} onClick={() => setAbierto(!abierto)}>
            {abierto ? "Ocultar intentos" : "Ver intentos"}
          </button>
          {abierto && (
            <ol className="linea-tiempo" style={{ marginTop: 8 }}>
              {d.sub.map((x, i) => (
                <li key={i} className={x.clase}>
                  <div className="titulo">{x.titulo}</div>
                  {x.detalle && <div className="detalle">{x.detalle}</div>}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </li>
  );
}

export default function Bitacora({ pasos }: { pasos: PasoBitacora[] }) {
  return (
    <div className="tarjeta">
      <h2>Cómo decidió el agente</h2>
      <ol className="linea-tiempo">
        {agrupar(pasos).map((d, i) => (
          <Paso key={i} d={d} />
        ))}
      </ol>
    </div>
  );
}
