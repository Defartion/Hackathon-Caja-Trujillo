import { useState } from "react";
import type { CicloRespuesta } from "../../contratos";
import { fmtS0 } from "../../formato";
import { SupuestosFuentes } from "./Detalles";
import GraficoCiclo from "./GraficoCiclo";
import { ETAPA_ETIQUETA, etiquetaPeriodo } from "./formato";

const capital = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

export function DatosCiclo({ ciclo }: { ciclo: CicloRespuesta }) {
  const ps = ciclo.periodos;
  const anio = ps.slice(0, 12);
  const cuenta = (e: string) => ps.filter((p) => p.etapa === e).length;
  const sinUn = ps.filter((p) => p.un_p50 <= 0).length;
  return (
    <div className="pl-indicadores">
      <div className="pl-indicador">
        <div className="k">UN esperada en {anio.length === 12 ? "los primeros 12 meses" : `${anio.length} meses`}</div>
        <div className="v">{fmtS0(anio.reduce((s, p) => s + p.un_p50, 0))}</div>
        <div className="d">promedio {fmtS0(anio.reduce((s, p) => s + p.un_p50, 0) / Math.max(anio.length, 1))} al mes</div>
      </div>
      <div className="pl-indicador">
        <div className="k">Meses en cima</div>
        <div className="v">{cuenta("cima")}</div>
        <div className="d">de {ps.length} · temporada alta</div>
      </div>
      <div className="pl-indicador">
        <div className="k">Meses en valle</div>
        <div className="v">{cuenta("valle")}</div>
        <div className="d">de {ps.length} · temporada baja</div>
      </div>
      <div className={`pl-indicador ${sinUn ? "mal" : ""}`}>
        <div className="k">Meses con UN ≤ 0</div>
        <div className="v">{sinUn}</div>
        <div className="d">{sinUn ? "en esos meses la cuota debe ser 0" : "todos los meses dejan utilidad"}</div>
      </div>
    </div>
  );
}

/** Paso 2: ciclo estimado con su banda, etapas, supuestos y fuentes. */
export default function PasoCiclo({ ciclo }: { ciclo: CicloRespuesta }) {
  const [tabla, setTabla] = useState(false);
  const ps = ciclo.periodos;
  const zona = `${ciclo.zona.provincia}${ciclo.zona.distrito ? ` · ${ciclo.zona.distrito}` : ""}`;
  return (
    <div className="rejilla">
      <div className="tarjeta rejilla">
        <div className="fila" style={{ alignItems: "baseline" }}>
          <h2 style={{ margin: 0 }}>
            Ciclo estimado · {capital(ciclo.actividad)} en {zona}
          </h2>
          <span className="pl-gris">
            {etiquetaPeriodo(ps[0]?.periodo ?? "")} a {etiquetaPeriodo(ps[ps.length - 1]?.periodo ?? "")} · {ps.length} meses
          </span>
          <div className="espacio" />
          <button type="button" className="btn" onClick={() => setTabla(!tabla)} aria-expanded={tabla}>
            {tabla ? "Ocultar tabla" : "Ver tabla"}
          </button>
        </div>
        <DatosCiclo ciclo={ciclo} />
        <GraficoCiclo periodos={ps} alto={280} />
        {tabla && (
          <div className="pl-tabla-envoltura">
            <table className="pl-tabla" aria-label="Ciclo por mes">
              <thead>
                <tr>
                  <th>Mes</th>
                  <th>Etapa</th>
                  <th className="num">Ventas esperadas</th>
                  <th className="num">UN p10</th>
                  <th className="num">UN p50</th>
                  <th className="num">UN p90</th>
                </tr>
              </thead>
              <tbody>
                {ps.map((p) => (
                  <tr key={p.periodo} className={`etapa-${p.etapa}`}>
                    <td>{etiquetaPeriodo(p.periodo)}</td>
                    <td>
                      <span className={`pl-etapa ${p.etapa}`}>{ETAPA_ETIQUETA[p.etapa]}</span>
                    </td>
                    <td className="num">{fmtS0(p.ventas_p50)}</td>
                    <td className="num">{fmtS0(p.un_p10)}</td>
                    <td className="num fuerte">{fmtS0(p.un_p50)}</td>
                    <td className="num">{fmtS0(p.un_p90)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="pl-leyenda" style={{ marginTop: 2 }}>
          Escenarios adversos que se probarán con el plan:{" "}
          {ciclo.escenarios
            .filter((e) => e.id !== "base")
            .map((e) => (
              <span key={e.id} className="pl-etapa normal">
                {e.nombre}
              </span>
            ))}
        </div>
      </div>
      <div className="tarjeta">
        <h2>Supuestos y fuentes</h2>
        <SupuestosFuentes ciclo={ciclo} />
      </div>
    </div>
  );
}
