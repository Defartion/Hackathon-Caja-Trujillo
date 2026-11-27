import { CSSProperties, ReactNode, useCallback, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cliente } from "../api";
import { useGuardado } from "../apariencia";
import SelectorColumnas from "../components/SelectorColumnas";
import type { Documento } from "../exportar";
import { fmtPct, fmtS0, nivelEstacionalidad, RUBRO_ETIQUETA } from "../formato";
import MenuExportar from "../MenuExportar";
import { useCartera } from "../useCartera";

type Filtro = "todas" | "alta" | "atraso" | "limpias";
type Orden = { col: keyof Cliente; asc: boolean };

const ATRASO_ALERTA = 8;

const FILTROS: { id: Filtro; texto: string; prueba: (c: Cliente) => boolean }[] = [
  { id: "todas", texto: "Todas", prueba: () => true },
  { id: "alta", texto: "Estacionalidad alta", prueba: (c) => nivelEstacionalidad(c.indice_estacionalidad).clase === "alta" },
  { id: "atraso", texto: `Atraso mayor a ${ATRASO_ALERTA} días`, prueba: (c) => c.dias_atraso_max > ATRASO_ALERTA },
  { id: "limpias", texto: "Sin atrasos", prueba: (c) => c.dias_atraso_max === 0 },
];

interface Columna {
  id: string;
  /** Campo por el que se ordena. */
  col: keyof Cliente;
  texto: string;
  num?: boolean;
  /** Se ve también en el celular. */
  movil?: boolean;
  /** No se puede ocultar: identifica la solicitud. */
  fija?: boolean;
  celda: (c: Cliente) => ReactNode;
  estilo?: (c: Cliente) => CSSProperties | undefined;
}

const COLUMNAS: Columna[] = [
  { id: "codigo", col: "cliente_id", texto: "Código", movil: true, fija: true, celda: (c) => c.cliente_id },
  { id: "rubro", col: "rubro", texto: "Rubro", movil: true, celda: (c) => RUBRO_ETIQUETA[c.rubro] ?? c.rubro },
  { id: "region", col: "region", texto: "Región", celda: (c) => c.region ?? "—" },
  { id: "monto", col: "principal", texto: "Monto", num: true, movil: true, celda: (c) => fmtS0(c.principal) },
  { id: "plazo", col: "plazo", texto: "Plazo", num: true, celda: (c) => `${c.plazo} m` },
  { id: "ventas", col: "ventas_medias", texto: "Ventas medias", num: true, celda: (c) => fmtS0(c.ventas_medias) },
  { id: "margen", col: "margen", texto: "Margen", num: true, celda: (c) => fmtPct(c.margen, 0) },
  { id: "gasto", col: "gasto_familiar", texto: "Gasto familiar", num: true, celda: (c) => fmtS0(c.gasto_familiar) },
  { id: "otras", col: "otras_cuotas", texto: "Otras cuotas", num: true, celda: (c) => fmtS0(c.otras_cuotas) },
  {
    id: "atraso", col: "dias_atraso_max", texto: "Atraso máx.", num: true, celda: (c) => `${c.dias_atraso_max} d`,
    estilo: (c) => (c.dias_atraso_max > ATRASO_ALERTA ? { color: "var(--cf-rojo-texto)", fontWeight: 650 } : undefined),
  },
  { id: "previos", col: "creditos_previos", texto: "Créditos previos", num: true, celda: (c) => c.creditos_previos ?? "—" },
  {
    id: "antiguedad", col: "antiguedad_negocio_anios", texto: "Antigüedad", num: true,
    celda: (c) => (c.antiguedad_negocio_anios == null ? "—" : `${c.antiguedad_negocio_anios} ${c.antiguedad_negocio_anios === 1 ? "año" : "años"}`),
  },
  { id: "yape", col: "pct_cobros_yape", texto: "Cobros digitales", num: true, celda: (c) => (c.pct_cobros_yape == null ? "—" : fmtPct(c.pct_cobros_yape, 0)) },
  {
    id: "estacionalidad", col: "indice_estacionalidad", texto: "Estacionalidad",
    celda: (c) => {
      const est = nivelEstacionalidad(c.indice_estacionalidad);
      return <span className={`etiqueta ${est.clase}`}>{est.texto}</span>;
    },
  },
];

const TODAS = COLUMNAS.map((c) => c.id);
const POR_DEFECTO = ["codigo", "rubro", "region", "monto", "plazo", "atraso", "estacionalidad"];
const VISTAS = [
  { id: "esenciales", texto: "Esenciales", columnas: ["codigo", "rubro", "monto", "plazo", "estacionalidad"] },
  { id: "recomendadas", texto: "Recomendadas", columnas: POR_DEFECTO },
  { id: "riesgo", texto: "Capacidad y riesgo", columnas: ["codigo", "rubro", "monto", "ventas", "margen", "gasto", "otras", "atraso", "estacionalidad"] },
  { id: "todas", texto: "Todas", columnas: TODAS },
];

function documentoBandeja(filas: Cliente[], filtro: string): Documento {
  return {
    archivo: "bandeja-de-solicitudes",
    titulo: "Bandeja de solicitudes",
    subtitulo: `${filtro} (${filas.length} ${filas.length === 1 ? "solicitud" : "solicitudes"})`,
    resumen: [
      { etiqueta: "Solicitudes", valor: filas.length, tipo: "entero" },
      { etiqueta: "Monto solicitado", valor: filas.reduce((s, c) => s + c.principal, 0), tipo: "moneda" },
      { etiqueta: "Con atraso mayor a 8 días", valor: filas.filter((c) => c.dias_atraso_max > ATRASO_ALERTA).length, tipo: "entero" },
    ],
    tablas: [
      {
        titulo: "Solicitudes",
        columnas: [
          { clave: "cliente_id", titulo: "Código" },
          { clave: "rubro", titulo: "Rubro" },
          { clave: "region", titulo: "Región" },
          { clave: "principal", titulo: "Monto", tipo: "moneda" },
          { clave: "plazo", titulo: "Plazo (meses)", tipo: "entero" },
          { clave: "ventas_medias", titulo: "Ventas medias", tipo: "moneda" },
          { clave: "margen", titulo: "Margen", tipo: "porcentaje" },
          { clave: "gasto_familiar", titulo: "Gasto familiar", tipo: "moneda" },
          { clave: "otras_cuotas", titulo: "Otras cuotas", tipo: "moneda" },
          { clave: "dias_atraso_max", titulo: "Atraso máx. (días)", tipo: "entero" },
          { clave: "estacionalidad", titulo: "Estacionalidad" },
        ],
        filas: filas.map((c) => ({
          ...c,
          rubro: RUBRO_ETIQUETA[c.rubro] ?? c.rubro,
          estacionalidad: nivelEstacionalidad(c.indice_estacionalidad).texto,
        })),
      },
    ],
  };
}

const normalizar = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function Bandeja() {
  const { datos, error } = useCartera();
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [rubro, setRubro] = useState("");
  const [busca, setBusca] = useState("");
  const [orden, setOrden] = useState<Orden | null>(null);
  const nav = useNavigate();
  // Columnas y altura de filas que eligió el asesor (se recuerdan entre visitas).
  const [guardadas, setGuardadas] = useGuardado("cuotaflex.bandeja.columnas", POR_DEFECTO.join(","));
  const [densidad, setDensidad] = useGuardado("cuotaflex.bandeja.filas", "comoda", ["comoda", "compacta"] as const);
  const elegidas = guardadas.split(",").filter((id) => TODAS.includes(id));
  const visibles = COLUMNAS.filter((c) => c.fija || elegidas.includes(c.id));
  // Con muchas columnas la tabla se desliza: una sombra en el borde avisa que hay más a un lado.
  const [bordes, setBordes] = useState("");
  const observador = useRef<ResizeObserver | null>(null);
  const medirDesliza = useCallback((el: HTMLElement) => {
    const izq = el.scrollLeft > 1;
    const der = el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
    const clase = `${izq ? " sombra-izq" : ""}${der ? " sombra-der" : ""}`;
    setBordes((actual) => (actual === clase ? actual : clase));
  }, []);
  const refDesliza = useCallback((el: HTMLDivElement | null) => {
    observador.current?.disconnect();
    observador.current = null;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => medirDesliza(el));
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    observador.current = ro;
  }, [medirDesliza]);

  const conteo = useMemo(
    () => Object.fromEntries(FILTROS.map((f) => [f.id, (datos ?? []).filter(f.prueba).length])) as Record<Filtro, number>,
    [datos],
  );

  const filas = useMemo(() => {
    const q = normalizar(busca.trim());
    const prueba = FILTROS.find((f) => f.id === filtro)!.prueba;
    const lista = (datos ?? []).filter((c) => {
      if (!prueba(c) || (rubro && c.rubro !== rubro)) return false;
      if (!q) return true;
      const texto = normalizar(`${c.cliente_id} ${RUBRO_ETIQUETA[c.rubro] ?? c.rubro} ${c.region ?? ""}`);
      return q.split(/\s+/).every((p) => texto.includes(p));
    });
    if (!orden) return lista;
    return [...lista].sort((a, b) => {
      const va = a[orden.col] ?? "";
      const vb = b[orden.col] ?? "";
      const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), "es");
      return orden.asc ? cmp : -cmp;
    });
  }, [datos, filtro, rubro, busca, orden]);

  if (error) return <div className="aviso">{error}</div>;
  if (!datos) return <div className="cargando">Cargando solicitudes…</div>;

  const ordenar = (col: keyof Cliente) =>
    setOrden((o) => (o?.col === col ? (o.asc ? { col, asc: false } : null) : { col, asc: true }));
  const abrir = (c: Cliente) => nav(`/cliente/${c.cliente_id}`);
  const hayFiltros = filtro !== "todas" || rubro || busca;

  return (
    <div className="tarjeta">
      <div className="fila bandeja-cab">
        <div>
          <h1>Bandeja de solicitudes</h1>
          <div className="ayuda">Toca una solicitud para ver la propuesta del agente y registrarla.</div>
        </div>
        <div className="espacio" />
        <button type="button" className="btn btn-primario" onClick={() => nav("/nueva")}>
          Nueva solicitud
        </button>
        <MenuExportar
          claseBoton="btn"
          deshabilitado={filas.length === 0}
          documento={() => {
            if (!filas.length) return null;
            const partes = [
              FILTROS.find((f) => f.id === filtro)?.texto ?? "Todas",
              rubro ? `rubro ${RUBRO_ETIQUETA[rubro] ?? rubro}` : "",
              busca.trim() ? `búsqueda "${busca.trim()}"` : "",
            ].filter(Boolean);
            return documentoBandeja(filas, partes.join(", "));
          }}
        />
      </div>

      <div className="fila bandeja-herramientas">
        <label className="campo buscador">
          Buscar
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Código, rubro o región"
            aria-label="Buscar por código, rubro o región"
          />
        </label>
        <label className="campo">
          Rubro
          <select value={rubro} onChange={(e) => setRubro(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(RUBRO_ETIQUETA).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <div className="espacio" />
        <SelectorColumnas
          columnas={COLUMNAS}
          visibles={visibles.map((c) => c.id)}
          vistas={VISTAS}
          porDefecto={POR_DEFECTO}
          densidad={densidad}
          onColumnas={(ids) => setGuardadas(ids.join(","))}
          onDensidad={setDensidad}
        />
      </div>

      <div className="chips" role="group" aria-label="Filtros rápidos">
        {FILTROS.map((f) => (
          <button
            key={f.id}
            type="button"
            className="chip"
            aria-pressed={filtro === f.id}
            onClick={() => setFiltro(f.id)}
          >
            {f.texto} <b>{conteo[f.id]}</b>
          </button>
        ))}
        {hayFiltros && (
          <button
            type="button"
            className="btn-enlace"
            onClick={() => {
              setFiltro("todas");
              setRubro("");
              setBusca("");
            }}
          >
            Limpiar filtros
          </button>
        )}
        <div className="espacio" />
        <span className="ayuda">
          {filas.length} de {datos.length} solicitudes, {fmtS0(filas.reduce((suma, c) => suma + c.principal, 0))} en total
        </span>
      </div>

      <div className={`tabla-desliza${bordes}`} ref={refDesliza} onScroll={(e) => medirDesliza(e.currentTarget)}>
        <table className={`tabla-bandeja ${densidad === "compacta" ? "compacta" : ""}`}>
          <thead>
            <tr>
              {visibles.map((c) => (
                <th
                  key={c.id}
                  className={`${c.num ? "num" : ""} ${c.movil ? "" : "solo-escritorio"}`}
                  aria-sort={orden?.col === c.col ? (orden.asc ? "ascending" : "descending") : "none"}
                >
                  <button type="button" className="th-orden" onClick={() => ordenar(c.col)}>
                    {c.texto}
                    <span aria-hidden="true">{orden?.col === c.col ? (orden.asc ? " ▲" : " ▼") : ""}</span>
                  </button>
                </th>
              ))}
              <th aria-label="Abrir" />
            </tr>
          </thead>
          <tbody>
            {filas.map((c) => (
              <tr
                key={c.cliente_id}
                className="clic"
                tabIndex={0}
                onClick={() => abrir(c)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), abrir(c))}
              >
                {visibles.map((col) => (
                  <td
                    key={col.id}
                    className={`${col.num ? "num" : ""} ${col.movil ? "" : "solo-escritorio"}`}
                    style={col.estilo?.(c)}
                  >
                    {col.celda(c)}
                  </td>
                ))}
                <td className="abrir" aria-hidden="true">
                  Ver →
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filas.length === 0 && (
        <div className="cargando">
          No hay solicitudes con ese filtro.{" "}
          <button type="button" className="btn-enlace" onClick={() => (setFiltro("todas"), setRubro(""), setBusca(""))}>
            Ver todas
          </button>
        </div>
      )}
    </div>
  );
}
