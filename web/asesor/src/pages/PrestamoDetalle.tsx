import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, CuotaDetalle, DetallePrestamo } from "../api";
import type { Documento } from "../exportar";
import { fmtPct, fmtS, fmtS0, RUBRO_ETIQUETA } from "../formato";
import MenuExportar from "../MenuExportar";
import { ESTADOS, PRODUCTO } from "./Prestamos";
import CodigoCliente from "../components/CodigoCliente";

const ESTADO_CUOTA: Record<CuotaDetalle["estado"], { texto: string; clase: string }> = {
  pagada: { texto: "Pagada", clase: "baja" },
  proxima: { texto: "Próxima", clase: "aplazamiento" },
  pendiente: { texto: "Pendiente", clase: "fija" },
};
const MES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];

function leerFecha(iso: string | null | undefined): Date | null {
  const m = iso ? /^(\d{4})-(\d{2})-(\d{2})/.exec(iso) : null;
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}
const fecha = (iso: string | null | undefined) => {
  const d = leerFecha(iso);
  return d ? `${d.getDate()} ${MES_CORTO[d.getMonth()]} ${d.getFullYear()}` : "—";
};
const mesAnio = (c: CuotaDetalle) => {
  const d = leerFecha(c.fecha);
  return d ? `${MES_CORTO[d.getMonth()]} ${String(d.getFullYear()).slice(2)}` : c.mes;
};
const texto = (v: string | null | undefined) => (v && v.trim() ? v : "—");
const soles = (v: number | null | undefined) => (v === null || v === undefined ? "—" : fmtS(v));
const ajuste = (a: number | null) => {
  if (a === null) return "—";
  const pct = Math.round((a - 1) * 100);
  return pct === 0 ? "Sin ajuste" : `${pct > 0 ? "+" : ""}${pct}% ${pct > 0 ? "(más optimista)" : "(más prudente)"}`;
};

function documento(d: DetallePrestamo): Documento {
  const estado = ESTADOS[d.estado]?.texto ?? d.estado;
  return {
    archivo: `prestamo-${d.id}`,
    titulo: `Préstamo N° ${d.id}`,
    subtitulo: [d.cliente.nombre, d.producto ? PRODUCTO[d.producto] ?? d.producto : null, estado].filter(Boolean).join(", "),
    resumen: [
      { etiqueta: "Cliente", valor: d.cliente.nombre },
      { etiqueta: "Rubro", valor: d.cliente.rubro ? RUBRO_ETIQUETA[d.cliente.rubro] ?? d.cliente.rubro : null },
      { etiqueta: "Estado", valor: estado },
      { etiqueta: "Monto aprobado", valor: d.principal, tipo: "moneda" },
      { etiqueta: "Monto solicitado", valor: d.principalSolicitado, tipo: "moneda" },
      { etiqueta: "Plazo (meses)", valor: d.plazo, tipo: "entero" },
      { etiqueta: "TEA", valor: d.tea, tipo: "porcentaje" },
      { etiqueta: "Desembolso", valor: d.fechaDesembolso, tipo: "fecha" },
      { etiqueta: "Cuota mínima", valor: d.cuotaMinima, tipo: "moneda" },
      { etiqueta: "Cuota máxima", valor: d.cuotaMaxima, tipo: "moneda" },
      { etiqueta: "Cuota fija de referencia", valor: d.cuotaFijaReferencia, tipo: "moneda" },
      { etiqueta: "Cuotas pagadas", valor: d.cuotasPagadas, tipo: "entero" },
      { etiqueta: "Total cobrado", valor: d.resumen.totalPagado, tipo: "moneda" },
      { etiqueta: "Por cobrar", valor: d.resumen.porPagar, tipo: "moneda" },
      { etiqueta: "Saldo de capital", valor: d.resumen.saldoCapital, tipo: "moneda" },
      { etiqueta: "Intereses del crédito", valor: d.resumen.interesesTotales, tipo: "moneda" },
    ],
    tablas: [
      {
        titulo: "Cronograma",
        columnas: [
          { clave: "numero", titulo: "N°", tipo: "entero" },
          { clave: "mes", titulo: "Mes" },
          { clave: "fecha", titulo: "Vence", tipo: "fecha" },
          { clave: "cuota", titulo: "Cuota", tipo: "moneda" },
          { clave: "capital", titulo: "Capital", tipo: "moneda" },
          { clave: "interes", titulo: "Interés", tipo: "moneda" },
          { clave: "saldo", titulo: "Saldo", tipo: "moneda" },
          { clave: "estado", titulo: "Estado" },
          { clave: "fechaPago", titulo: "Pagada el", tipo: "fecha" },
        ],
        filas: d.cronograma.map((c) => ({ ...c, estado: ESTADO_CUOTA[c.estado].texto })),
      },
      {
        titulo: "Pagos registrados",
        columnas: [
          { clave: "fecha", titulo: "Fecha", tipo: "fecha" },
          { clave: "cuota", titulo: "Cuota N°", tipo: "entero" },
          { clave: "monto", titulo: "Monto", tipo: "moneda" },
        ],
        filas: d.pagos,
      },
    ],
    notas: d.explicacion ? [d.explicacion] : [],
  };
}

function GraficoCuotasPrestamo({ d }: { d: DetallePrestamo }) {
  const filas = d.cronograma.map((c) => ({ ...c, etiqueta: mesAnio(c) }));
  return (
    <ResponsiveContainer width="100%" height={230}>
      <BarChart data={filas} margin={{ top: 14, right: 12, left: 4, bottom: 0 }} barCategoryGap="22%">
        <CartesianGrid stroke="#eee" vertical={false} />
        <XAxis dataKey="etiqueta" fontSize={11} interval={0} tickLine={false} />
        <YAxis tickFormatter={(v: number) => fmtS0(v)} width={70} fontSize={11} />
        <Tooltip
          cursor={{ fill: "#EEF1F5" }}
          content={({ active, payload }) => {
            const c = active && payload?.[0] ? (payload[0].payload as CuotaDetalle & { etiqueta: string }) : null;
            if (!c) return null;
            return (
              <div className="tooltip-graf">
                <b>Cuota {c.numero}, vence el {fecha(c.fecha)}</b>
                <span>{fmtS(c.cuota)}: capital {fmtS(c.capital)}, interés {fmtS(c.interes)}</span>
                <span>{c.estado === "pagada" ? `Pagada el ${fecha(c.fechaPago)}` : ESTADO_CUOTA[c.estado].texto}</span>
              </div>
            );
          }}
        />
        <Bar dataKey="cuota" name="Cuota" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {filas.map((c) => (
            <Cell key={c.numero} fill="#0B5CAD" fillOpacity={c.estado === "pagada" ? 0.35 : 1} />
          ))}
        </Bar>
        {d.cuotaFijaReferencia !== null && (
          <ReferenceLine y={d.cuotaFijaReferencia} stroke="#8792A6" strokeWidth={2} strokeDasharray="6 4" ifOverflow="extendDomain" />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function PrestamoDetalle() {
  const { id } = useParams();
  const numero = Number(id);
  const [d, setD] = useState<DetallePrestamo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setD(await api.detallePrestamo(numero));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [numero]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const ejecutar = async (accion: "approve" | "disburse") => {
    setOcupado(true);
    try {
      await api.comando(numero, accion);
      await cargar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOcupado(false);
    }
  };

  const volver = (
    <Link to="/prestamos" className="volver">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
        strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
      Préstamos registrados
    </Link>
  );

  if (!Number.isInteger(numero)) return <>{volver}<div className="aviso">Ese préstamo no existe.</div></>;
  if (error && !d) return <>{volver}<div className="aviso">{error}</div></>;
  if (!d) return <>{volver}<div className="cargando">Cargando el préstamo…</div></>;

  const estado = ESTADOS[d.estado] ?? { texto: d.estado, clase: "fija" };
  const proxima = d.cronograma.find((c) => c.estado === "proxima");
  const avance = d.resumen.totalAPagar > 0 ? d.resumen.totalPagado / d.resumen.totalAPagar : 0;
  const rubro = d.cliente.rubro ? RUBRO_ETIQUETA[d.cliente.rubro] ?? d.cliente.rubro : null;
  const producto = d.producto ? PRODUCTO[d.producto] ?? d.producto : "—";
  const variable = Math.abs(d.cuotaMaxima - d.cuotaMinima) >= 1;

  return (
    <div className="rejilla pd">
      {volver}
      <section className="tarjeta" aria-labelledby="pd-titulo">
        <div className="pd-cabecera">
          <div>
            <div className="pd-titulo">
              <h1 id="pd-titulo">Préstamo N° {d.id}</h1>
              <span className={`etiqueta ${estado.clase}`}>{estado.texto}</span>
            </div>
            <div className="ayuda">{[d.cliente.nombre, rubro, producto].filter(Boolean).join(", ")}</div>
          </div>
          <div className="espacio" />
          {estado.accion && (
            <button type="button" className="btn btn-primario" disabled={ocupado} onClick={() => void ejecutar(estado.accion!)}>
              {ocupado ? "…" : estado.boton}
            </button>
          )}
          <MenuExportar claseBoton="btn" documento={() => documento(d)} />
        </div>
        {error && <div className="aviso" style={{ marginTop: 12 }}>{error}</div>}

        <dl className="pd-kpis">
          <div>
            <dt>Monto aprobado</dt>
            <dd>{fmtS0(d.principal)}</dd>
            <span>
              {d.principalSolicitado !== null && Math.abs(d.principalSolicitado - d.principal) >= 1
                ? `Pidió ${fmtS0(d.principalSolicitado)}`
                : "Lo que pidió el cliente"}
            </span>
          </div>
          <div>
            <dt>Plazo y tasa</dt>
            <dd>{d.plazo} meses</dd>
            <span>TEA {fmtPct(d.tea)}</span>
          </div>
          <div>
            <dt>{variable ? "Cuotas entre" : "Cuota"}</dt>
            <dd>{variable ? `${fmtS0(d.cuotaMinima)} y ${fmtS0(d.cuotaMaxima)}` : fmtS0(d.cuotaMinima)}</dd>
            <span>{d.cuotaFijaReferencia !== null ? `Cuota fija equivalente ${fmtS0(d.cuotaFijaReferencia)}` : "—"}</span>
          </div>
          <div>
            <dt>Cobrado</dt>
            <dd>{fmtS0(d.resumen.totalPagado)}</dd>
            <span>{d.cuotasPagadas} de {d.totalCuotas} cuotas</span>
          </div>
          <div>
            <dt>Próximo vencimiento</dt>
            <dd>{proxima ? fecha(proxima.fecha) : d.estado === "Active" ? "Sin cuotas pendientes" : "—"}</dd>
            <span>{proxima ? `Cuota ${proxima.numero}, ${fmtS(proxima.cuota)}` : d.fechaDesembolso ? "" : "Aún sin desembolso"}</span>
          </div>
        </dl>

        <div className="pd-avance">
          <div className="pd-avance__texto">
            <span>Avance de cobro</span>
            <b>{Math.round(avance * 100)}%</b>
          </div>
          <progress value={d.resumen.totalPagado} max={Math.max(d.resumen.totalAPagar, 1)}
            aria-label={`Cobrado ${fmtS(d.resumen.totalPagado)} de ${fmtS(d.resumen.totalAPagar)}`} />
          <div className="pd-avance__texto ayuda">
            <span>Por cobrar {fmtS(d.resumen.porPagar)}</span>
            <span>Saldo de capital {fmtS(d.resumen.saldoCapital)}</span>
          </div>
        </div>
      </section>

      <section className="tarjeta" aria-labelledby="pd-acceso">
        <h2 id="pd-acceso" className="sr-solo">Acceso del cliente</h2>
        <CodigoCliente prestamo={d.id} />
      </section>

      <div className="pd-columnas">
        <section className="tarjeta" aria-labelledby="pd-cliente">
          <h2 id="pd-cliente">Cliente</h2>
          <dl className="pd-datos">
            <div><dt>Nombre</dt><dd>{texto(d.cliente.nombre)}</dd></div>
            <div><dt>Rubro</dt><dd>{texto(rubro)}</dd></div>
            {d.cliente.region && <div><dt>Zona</dt><dd>{d.cliente.region}</dd></div>}
            <div><dt>Ventas promedio al mes</dt><dd>{soles(d.cliente.ventas_medias)}</dd></div>
            <div><dt>Margen del negocio</dt><dd>{d.cliente.margen === null ? "—" : fmtPct(d.cliente.margen)}</dd></div>
            <div><dt>Gasto familiar al mes</dt><dd>{soles(d.cliente.gasto_familiar)}</dd></div>
            <div><dt>Otras cuotas al mes</dt><dd>{soles(d.cliente.otras_cuotas)}</dd></div>
            <div><dt>Mayor atraso (días)</dt><dd>{d.cliente.dias_atraso_max ?? "—"}</dd></div>
            <div><dt>Ventas según la visita</dt><dd>{ajuste(d.cliente.ajuste_asesor)}</dd></div>
          </dl>
        </section>
        <section className="tarjeta" aria-labelledby="pd-condiciones">
          <h2 id="pd-condiciones">Condiciones</h2>
          <dl className="pd-datos">
            <div><dt>Producto</dt><dd>{producto}</dd></div>
            <div><dt>Desembolso</dt><dd>{d.fechaDesembolso ? fecha(d.fechaDesembolso) : "Pendiente"}</dd></div>
            <div><dt>Total a pagar</dt><dd>{fmtS(d.resumen.totalAPagar)}</dd></div>
            <div><dt>Intereses del crédito</dt><dd>{fmtS(d.resumen.interesesTotales)}</dd></div>
            <div><dt>Aplazamientos disponibles</dt><dd>{d.aplazamientosRestantes}</dd></div>
            <div><dt>Revisado para El Niño</dt><dd>{d.clausulaElNino ? "Sí" : "No"}</dd></div>
            <div>
              <dt>Políticas de crédito</dt>
              <dd>{d.cumplePoliticas === null ? "—" : d.cumplePoliticas ? "Cumple" : "Con observaciones"}</dd>
            </div>
          </dl>
          {d.descripcionProducto && <p className="ayuda pd-nota">{d.descripcionProducto}</p>}
        </section>
      </div>

      <section className="tarjeta" aria-labelledby="pd-grafico">
        <div className="fila pd-grafico-cab">
          <h2 id="pd-grafico">Cuotas mes a mes</h2>
          <div className="espacio" />
          <ul className="pd-leyenda" aria-label="Leyenda">
            <li><i className="pd-muestra pd-muestra--pagada" aria-hidden="true" />Pagada</li>
            <li><i className="pd-muestra" aria-hidden="true" />Por pagar</li>
            {d.cuotaFijaReferencia !== null && <li><i className="pd-muestra pd-muestra--fija" aria-hidden="true" />Cuota fija de referencia</li>}
          </ul>
        </div>
        <GraficoCuotasPrestamo d={d} />
      </section>

      <section className="tarjeta" aria-labelledby="pd-cronograma">
        <h2 id="pd-cronograma">Cronograma</h2>
        <div className="tabla-desliza">
          <table>
            <thead>
              <tr>
                <th className="num">N°</th>
                <th>Vence</th>
                <th className="num">Cuota</th>
                <th className="num">Capital</th>
                <th className="num">Interés</th>
                <th className="num">Saldo</th>
                <th>Estado</th>
                <th>Pagada el</th>
              </tr>
            </thead>
            <tbody>
              {d.cronograma.map((c) => (
                <tr key={c.numero} className={c.estado === "proxima" ? "pd-proxima" : undefined}>
                  <td className="num">{c.numero}</td>
                  <td>{fecha(c.fecha)}</td>
                  <td className="num" style={{ fontWeight: 650 }}>{fmtS(c.cuota)}</td>
                  <td className="num">{fmtS(c.capital)}</td>
                  <td className="num">{fmtS(c.interes)}</td>
                  <td className="num">{fmtS(Math.max(c.saldo, 0))}</td>
                  <td><span className={`etiqueta ${ESTADO_CUOTA[c.estado].clase}`}>{ESTADO_CUOTA[c.estado].texto}</span></td>
                  <td>{c.fechaPago ? fecha(c.fechaPago) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="tarjeta" aria-labelledby="pd-pagos">
        <h2 id="pd-pagos">Pagos registrados</h2>
        {d.pagos.length === 0 ? (
          <p className="ayuda" style={{ marginTop: 0 }}>Todavía no hay pagos. Se registran desde la app del cliente.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th className="num">Cuota N°</th>
                <th className="num">Monto</th>
              </tr>
            </thead>
            <tbody>
              {d.pagos.map((p, i) => (
                <tr key={i}>
                  <td>{fecha(p.fecha)}</td>
                  <td className="num">{p.cuota ?? "—"}</td>
                  <td className="num">{soles(p.monto)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {d.explicacion && (
        <section className="tarjeta" aria-labelledby="pd-explicacion">
          <h2 id="pd-explicacion">Por qué este plan</h2>
          <p className="pd-explicacion">{d.explicacion}</p>
        </section>
      )}
    </div>
  );
}
