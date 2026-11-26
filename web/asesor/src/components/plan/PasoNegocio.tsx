import type { CatalogoCiclo, Zona } from "../../contratos";
import { fmtS0, MESES } from "../../formato";
import { Campo, EntradaNumero } from "./campos";
import { CASOS_ESTRELLA, CasoEstrella } from "./casos";
import { MESES_LARGOS } from "./formato";
import type { Errores, EstadoMes, FormNegocio } from "./formularios";
import { PLAZO_MAX, PLAZO_MIN, utilidadPorTipoMes } from "./formularios";

const SIGUIENTE: Record<EstadoMes, EstadoMes> = { normal: "alto", alto: "bajo", bajo: "normal" };
const ESTADO_TEXTO: Record<EstadoMes, string> = { normal: "normal", alto: "alto", bajo: "bajo" };

const capital = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const zonaTexto = (z: Zona) => `${z.provincia}${z.distrito ? ` · ${z.distrito}` : ""} (${z.departamento})`;
const mismaZona = (a: Zona | null, b: Zona) =>
  !!a && a.departamento === b.departamento && a.provincia === b.provincia && (a.distrito ?? null) === (b.distrito ?? null);

interface Props {
  valor: FormNegocio;
  cambiar: (f: FormNegocio) => void;
  catalogo: CatalogoCiclo | null;
  errorCatalogo: string | null;
  errores: Errores;
  avisos: string[];
  alCargarCaso: (c: CasoEstrella) => void;
}

export default function PasoNegocio({ valor: f, cambiar, catalogo, errorCatalogo, errores, avisos, alCargarCaso }: Props) {
  const set = <K extends keyof FormNegocio>(k: K, v: FormNegocio[K]) => cambiar({ ...f, [k]: v });
  const actividades = catalogo?.actividades ?? [];
  const sectores = [...new Set(actividades.map((a) => a.sector))];
  if (f.sector && !sectores.includes(f.sector)) sectores.push(f.sector);
  const delSector = actividades.filter((a) => a.sector === f.sector);
  const actual = delSector.find((a) => a.actividad === f.actividad);
  const zonas = actual?.zonas ?? (f.zona ? [f.zona] : []);
  const un = utilidadPorTipoMes(f);

  function elegirSector(sector: string) {
    cambiar({ ...f, sector, actividad: "", zona: null });
  }
  function elegirActividad(actividad: string) {
    const a = delSector.find((x) => x.actividad === actividad);
    cambiar({ ...f, actividad, zona: a && a.zonas.length === 1 ? a.zonas[0] : null });
  }
  function alternarMes(i: number) {
    const meses = [...f.meses_estado];
    meses[i] = SIGUIENTE[meses[i]];
    set("meses_estado", meses);
  }

  return (
    <div className="tarjeta pl-seccion-tarjeta">
      <section className="pl-seccion" aria-labelledby="casos-demo">
        <h3 id="casos-demo">Casos de demostración</h3>
        <div className="pl-ayuda-seccion">Llenan el formulario con la captura de un caso estrella (datos sintéticos).</div>
        <div className="pl-casos">
          {CASOS_ESTRELLA.map((c) => (
            <button key={c.id} type="button" className="pl-caso" onClick={() => alCargarCaso(c)} aria-label={`Cargar caso ${c.nombre} (${c.id})`}>
              <div className="t">
                {c.nombre} · {c.id}
              </div>
              <div className="s">{c.resumen}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="pl-seccion" aria-labelledby="sec-cliente">
        <h3 id="sec-cliente">Cliente y negocio</h3>
        {errorCatalogo && <div className="aviso">{errorCatalogo}</div>}
        <div className="pl-campos">
          <Campo etiqueta="Código de la solicitud" error={errores.cliente_id} ayuda="Identifica la solicitud ante el comité.">
            {(id, d) => (
              <input id={id} aria-describedby={d} value={f.cliente_id} onChange={(e) => set("cliente_id", e.target.value)} placeholder="C-0457" maxLength={20} />
            )}
          </Campo>
          <Campo etiqueta="Nombre o referencia" ayuda="Opcional. Solo para el expediente.">
            {(id, d) => <input id={id} aria-describedby={d} value={f.nombre} onChange={(e) => set("nombre", e.target.value)} placeholder="Rosa" maxLength={40} />}
          </Campo>
          <Campo etiqueta="Sector" error={errores.sector}>
            {(id, d) => (
              <select id={id} aria-describedby={d} value={f.sector} onChange={(e) => elegirSector(e.target.value)} disabled={!catalogo && !f.sector}>
                <option value="">{catalogo ? "Elige…" : "Cargando…"}</option>
                {sectores.map((s) => (
                  <option key={s} value={s}>
                    {capital(s)}
                  </option>
                ))}
              </select>
            )}
          </Campo>
          <Campo etiqueta="Actividad" error={errores.actividad}>
            {(id, d) => (
              <select id={id} aria-describedby={d} value={f.actividad} onChange={(e) => elegirActividad(e.target.value)} disabled={!f.sector}>
                <option value="">Elige…</option>
                {delSector.map((a) => (
                  <option key={a.actividad} value={a.actividad}>
                    {capital(a.actividad)}
                  </option>
                ))}
                {f.actividad && !actual && <option value={f.actividad}>{capital(f.actividad)}</option>}
              </select>
            )}
          </Campo>
          <Campo etiqueta="Provincia" error={errores.zona} ayuda="Zona del patrón público (MIDAGRI, PRODUCE, INEI…).">
            {(id, d) => (
              <select
                id={id}
                aria-describedby={d}
                value={f.zona ? String(zonas.findIndex((z) => mismaZona(f.zona, z))) : ""}
                onChange={(e) => set("zona", e.target.value === "" ? null : zonas[Number(e.target.value)])}
                disabled={!f.actividad}
              >
                <option value="">Elige…</option>
                {zonas.map((z, i) => (
                  <option key={zonaTexto(z)} value={String(i)}>
                    {zonaTexto(z)}
                  </option>
                ))}
              </select>
            )}
          </Campo>
          <Campo etiqueta="Desembolso previsto" error={errores.fecha_inicio}>
            {(id, d) => <input id={id} aria-describedby={d} type="date" value={f.fecha_inicio} onChange={(e) => set("fecha_inicio", e.target.value)} />}
          </Campo>
          <Campo etiqueta="Plazo solicitado" error={errores.meses} ayuda="El ciclo se estima para todo el plazo.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.meses} cambiar={(v) => set("meses", v)} sufijo="meses" paso="1" min={PLAZO_MIN} max={PLAZO_MAX} />}
          </Campo>
        </div>
      </section>

      <section className="pl-seccion" aria-labelledby="sec-ventas">
        <h3 id="sec-ventas">Ventas del negocio</h3>
        <div className="pl-ayuda-seccion">Lo que el cliente cuenta y el asesor verifica en la visita. Montos en soles por mes.</div>
        <div className="pl-campos">
          <Campo etiqueta="Ventas en un mes alto" error={errores.ventas_mes_alto} ayuda="Un buen mes: cosecha, temporada de pesca o campaña.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.ventas_mes_alto} cambiar={(v) => set("ventas_mes_alto", v)} prefijo="S/" paso="50" placeholder="16800" />}
          </Campo>
          <Campo etiqueta="Ventas en un mes normal" error={errores.ventas_mes_normal} ayuda="Un mes regular, sin temporada.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.ventas_mes_normal} cambiar={(v) => set("ventas_mes_normal", v)} prefijo="S/" paso="50" placeholder="7000" />}
          </Campo>
          <Campo etiqueta="Ventas en un mes bajo" error={errores.ventas_mes_bajo} ayuda="El peor mes: siembra, veda o temporada baja.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.ventas_mes_bajo} cambiar={(v) => set("ventas_mes_bajo", v)} prefijo="S/" paso="50" placeholder="1750" />}
          </Campo>
        </div>
        <div>
          <div className="pl-campo" style={{ marginBottom: 6 }}>
            <span className="etq">¿Qué meses son altos y cuáles bajos?</span>
            <span className="pl-ayuda">Toca un mes para marcarlo como alto, luego bajo y de vuelta normal. Si el cliente no coincide con el patrón de su zona, prevalece lo que marques.</span>
          </div>
          <div className="pl-meses" role="group" aria-label="Meses altos y bajos">
            {f.meses_estado.map((s, i) => (
              <button
                key={MESES[i]}
                type="button"
                className={`pl-mes ${s}`}
                onClick={() => alternarMes(i)}
                aria-label={`${MESES_LARGOS[i]}: mes ${ESTADO_TEXTO[s]}`}
              >
                <span className="pl-mes__nombre">{MESES_LARGOS[i].charAt(0).toUpperCase() + MESES_LARGOS[i].slice(1)}</span>
                <small>{ESTADO_TEXTO[s]}</small>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="pl-seccion" aria-labelledby="sec-costos">
        <h3 id="sec-costos">Costos, gastos y hogar</h3>
        <div className="pl-campos">
          <Campo etiqueta="Costo de ventas" error={errores.costo_ventas_pct} ayuda="De cada S/ 100 vendidos, cuánto se va en mercadería o insumos.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.costo_ventas_pct} cambiar={(v) => set("costo_ventas_pct", v)} sufijo="%" paso="1" max={99} placeholder="58" />}
          </Campo>
          <Campo etiqueta="Gastos operativos" error={errores.gastos_operativos} ayuda="Alquiler, luz, transporte, jornales.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.gastos_operativos} cambiar={(v) => set("gastos_operativos", v)} prefijo="S/" paso="10" placeholder="600" />}
          </Campo>
          <Campo etiqueta="Gastos tributarios" error={errores.gastos_tributarios} ayuda="RUS, RER u otros impuestos del mes.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.gastos_tributarios} cambiar={(v) => set("gastos_tributarios", v)} prefijo="S/" paso="10" placeholder="80" />}
          </Campo>
          <Campo etiqueta="Carga familiar" error={errores.carga_familiar} ayuda="Gastos del hogar que salen del negocio.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.carga_familiar} cambiar={(v) => set("carga_familiar", v)} prefijo="S/" paso="10" placeholder="1100" />}
          </Campo>
          <Campo etiqueta="Cuotas de otras deudas" error={errores.otras_deudas_cuota} ayuda="Lo que ya paga al mes en otras entidades.">
            {(id, d) => <EntradaNumero id={id} describe={d} valor={f.otras_deudas_cuota} cambiar={(v) => set("otras_deudas_cuota", v)} prefijo="S/" paso="10" placeholder="0" />}
          </Campo>
        </div>
        {un && (
          <div className="pl-vista-un" aria-live="polite">
            {(["alto", "normal", "bajo"] as const).map((k) => (
              <div key={k} className={`item ${un[k] <= 0 ? "negativo" : ""}`}>
                <div className="k">Utilidad neta en un mes {k}</div>
                <div className="v">{fmtS0(un[k])}</div>
              </div>
            ))}
            {un.bajo <= 0 && (
              <div className="pl-aviso-suave" style={{ alignSelf: "center" }}>
                En los meses bajos no le queda utilidad: el plan pondrá gracia (cuota 0) en esos meses.
              </div>
            )}
          </div>
        )}
      </section>

      <section className="pl-seccion" aria-labelledby="sec-evidencias">
        <h3 id="sec-evidencias">Evidencias (opcional)</h3>
        <div className="pl-ayuda-seccion">Movimientos de Yape o boletas que respaldan el nivel de ventas. No se usa el historial de pagos.</div>
        <div className="pl-evidencias">
          {f.evidencias.map((ev, i) => (
            <div key={i}>
              <div className="pl-evidencia">
                <Campo etiqueta="Tipo">
                  {(id) => (
                    <select
                      id={id}
                      value={ev.tipo}
                      onChange={(e) => set("evidencias", f.evidencias.map((x, j) => (j === i ? { ...x, tipo: e.target.value as "yape" | "boletas" } : x)))}
                    >
                      <option value="yape">Yape</option>
                      <option value="boletas">Boletas</option>
                    </select>
                  )}
                </Campo>
                <Campo etiqueta="Meses que cubre">
                  {(id) => (
                    <EntradaNumero id={id} valor={ev.meses} paso="1" min={1} cambiar={(v) => set("evidencias", f.evidencias.map((x, j) => (j === i ? { ...x, meses: v } : x)))} />
                  )}
                </Campo>
                <Campo etiqueta="Promedio mensual">
                  {(id) => (
                    <EntradaNumero id={id} valor={ev.monto} prefijo="S/" paso="50" cambiar={(v) => set("evidencias", f.evidencias.map((x, j) => (j === i ? { ...x, monto: v } : x)))} />
                  )}
                </Campo>
                <button type="button" className="btn" onClick={() => set("evidencias", f.evidencias.filter((_, j) => j !== i))} aria-label={`Quitar evidencia ${i + 1}`}>
                  Quitar
                </button>
              </div>
              {errores[`evidencia_${i}`] && <div className="pl-error">{errores[`evidencia_${i}`]}</div>}
            </div>
          ))}
          <div>
            <button type="button" className="btn" onClick={() => set("evidencias", [...f.evidencias, { tipo: "yape", meses: "3", monto: "" }])}>
              + Agregar evidencia
            </button>
          </div>
        </div>
      </section>

      {avisos.length > 0 && (
        <div className="pl-avisos">
          {avisos.map((a) => (
            <div key={a} className="pl-aviso-suave">
              {a}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
