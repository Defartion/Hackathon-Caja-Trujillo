import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cliente } from "../api";
import { fmtS0, nivelEstacionalidad, RUBRO_ETIQUETA } from "../formato";
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

const COLUMNAS: { col: keyof Cliente; texto: string; num?: boolean; movil?: boolean }[] = [
  { col: "cliente_id", texto: "Código", movil: true },
  { col: "rubro", texto: "Rubro", movil: true },
  { col: "region", texto: "Región" },
  { col: "principal", texto: "Monto", num: true, movil: true },
  { col: "plazo", texto: "Plazo", num: true },
  { col: "ventas_medias", texto: "Ventas medias", num: true },
  { col: "dias_atraso_max", texto: "Atraso máx.", num: true },
  { col: "indice_estacionalidad", texto: "Estacionalidad" },
];

const normalizar = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function Bandeja() {
  const { datos, error } = useCartera();
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [rubro, setRubro] = useState("");
  const [busca, setBusca] = useState("");
  const [orden, setOrden] = useState<Orden | null>(null);
  const nav = useNavigate();

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
      <div className="fila" style={{ marginBottom: 12 }}>
        <div>
          <h1 style={{ fontSize: 20 }}>Bandeja de solicitudes</h1>
          <div className="ayuda">Toca una solicitud para ver la propuesta del agente y registrarla.</div>
        </div>
        <div className="espacio" />
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
          {filas.length} de {datos.length}
        </span>
      </div>

      <table className="tabla-bandeja">
        <thead>
          <tr>
            {COLUMNAS.map((c) => (
              <th
                key={c.col}
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
          {filas.map((c) => {
            const est = nivelEstacionalidad(c.indice_estacionalidad);
            return (
              <tr
                key={c.cliente_id}
                className="clic"
                tabIndex={0}
                onClick={() => abrir(c)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), abrir(c))}
              >
                <td style={{ fontWeight: 600 }}>{c.cliente_id}</td>
                <td>{RUBRO_ETIQUETA[c.rubro] ?? c.rubro}</td>
                <td className="solo-escritorio">{c.region}</td>
                <td className="num">{fmtS0(c.principal)}</td>
                <td className="num solo-escritorio">{c.plazo} m</td>
                <td className="num solo-escritorio">{fmtS0(c.ventas_medias)}</td>
                <td
                  className="num solo-escritorio"
                  style={{ color: c.dias_atraso_max > ATRASO_ALERTA ? "var(--cf-rojo)" : undefined }}
                >
                  {c.dias_atraso_max} d
                </td>
                <td className="solo-escritorio">
                  <span className={`etiqueta ${est.clase}`}>{est.texto}</span>
                </td>
                <td className="abrir" aria-hidden="true">
                  Ver →
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
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
