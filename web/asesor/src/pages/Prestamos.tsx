import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, PrestamoListado } from "../api";
import type { Documento } from "../exportar";
import { fmtS0, RUBRO_ETIQUETA } from "../formato";
import MenuExportar from "../MenuExportar";

export const ESTADOS: Record<string, { texto: string; clase: string; accion?: "approve" | "disburse"; boton?: string }> = {
  "Submitted and pending approval": { texto: "Falta aprobar", clase: "media", accion: "approve", boton: "Aprobar" },
  Approved: { texto: "Falta desembolsar", clase: "aplazamiento", accion: "disburse", boton: "Desembolsar" },
  Active: { texto: "Activo", clase: "baja" },
  "Closed (obligations met)": { texto: "Pagado", clase: "fija" },
};

export const PRODUCTO: Record<string, string> = {
  fija: "Cuota fija",
  aplazamiento: "Fija con aplazamientos",
  estacional: "Por temporada",
};

type Filtro = "todos" | "pendientes" | "activos";

const NOMBRE_FILTRO: Record<Filtro, string> = { todos: "Todos", pendientes: "Pendientes", activos: "Activos" };

function documentoLista(filas: PrestamoListado[], filtro: Filtro): Documento {
  return {
    archivo: `prestamos-registrados-${filtro}`,
    titulo: "Préstamos registrados",
    subtitulo: `Filtro: ${NOMBRE_FILTRO[filtro]} (${filas.length} ${filas.length === 1 ? "préstamo" : "préstamos"})`,
    resumen: [
      { etiqueta: "Préstamos", valor: filas.length, tipo: "entero" },
      { etiqueta: "Monto total", valor: filas.reduce((s, f) => s + f.principal, 0), tipo: "moneda" },
      { etiqueta: "Activos", valor: filas.filter((f) => f.estado === "Active").length, tipo: "entero" },
      { etiqueta: "Pendientes", valor: filas.filter((f) => ESTADOS[f.estado]?.accion).length, tipo: "entero" },
    ],
    tablas: [
      {
        titulo: "Préstamos",
        columnas: [
          { clave: "id", titulo: "N°", tipo: "entero" },
          { clave: "cliente", titulo: "Cliente" },
          { clave: "rubro", titulo: "Rubro" },
          { clave: "producto", titulo: "Producto" },
          { clave: "principal", titulo: "Monto", tipo: "moneda" },
          { clave: "plazo", titulo: "Plazo (meses)", tipo: "entero" },
          { clave: "cuota_min", titulo: "Cuota mínima", tipo: "moneda" },
          { clave: "cuota_max", titulo: "Cuota máxima", tipo: "moneda" },
          { clave: "aplazamientos_restantes", titulo: "Aplazamientos", tipo: "entero" },
          { clave: "estado", titulo: "Estado" },
        ],
        filas: filas.map((f) => ({
          ...f,
          rubro: f.rubro ? RUBRO_ETIQUETA[f.rubro] ?? f.rubro : null,
          producto: f.producto ? PRODUCTO[f.producto] ?? f.producto : null,
          estado: ESTADOS[f.estado]?.texto ?? f.estado,
        })),
      },
    ],
  };
}

export default function Prestamos() {
  const [filas, setFilas] = useState<PrestamoListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<number | null>(null);
  const [filtro, setFiltro] = useState<Filtro>("todos");

  const cargar = useCallback(async () => {
    try {
      setFilas(await api.prestamos());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const ejecutar = async (id: number, accion: "approve" | "disburse") => {
    setOcupado(id);
    try {
      await api.comando(id, accion);
      await cargar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOcupado(null);
    }
  };

  if (error && !filas) return <div className="aviso">{error}</div>;
  if (!filas) return <div className="cargando">Cargando préstamos…</div>;

  const pendientes = filas.filter((f) => ESTADOS[f.estado]?.accion);
  const visibles = filtro === "pendientes" ? pendientes : filtro === "activos" ? filas.filter((f) => f.estado === "Active") : filas;

  return (
    <div className="tarjeta">
      <div className="fila" style={{ marginBottom: 12 }}>
        <div>
          <h1>Préstamos registrados</h1>
          <div className="ayuda">
            {pendientes.length > 0
              ? `Tienes ${pendientes.length} ${pendientes.length === 1 ? "préstamo pendiente" : "préstamos pendientes"} de aprobar o desembolsar.`
              : "No tienes préstamos pendientes."}
          </div>
        </div>
        <div className="espacio" />
        <button type="button" className="btn" onClick={() => void cargar()}>
          Actualizar
        </button>
        <MenuExportar
          claseBoton="btn"
          deshabilitado={visibles.length === 0}
          documento={() => (visibles.length ? documentoLista(visibles, filtro) : null)}
        />
      </div>

      <div className="chips" role="group" aria-label="Filtros">
        {(
          [
            ["todos", "Todos", filas.length],
            ["pendientes", "Pendientes", pendientes.length],
            ["activos", "Activos", filas.filter((f) => f.estado === "Active").length],
          ] as [Filtro, string, number][]
        ).map(([id, texto, n]) => (
          <button key={id} type="button" className="chip" aria-pressed={filtro === id} onClick={() => setFiltro(id)}>
            {texto} <b>{n}</b>
          </button>
        ))}
      </div>
      {error && <div className="aviso" style={{ marginBottom: 10 }}>{error}</div>}

      {filas.length === 0 ? (
        <div className="cargando">
          Aún no hay préstamos. Abre una solicitud en la <Link to="/">bandeja</Link> y pulsa "Registrar solicitud".
        </div>
      ) : (
        <table className="tabla-bandeja">
          <thead>
            <tr>
              <th>N°</th>
              <th>Cliente</th>
              <th className="solo-escritorio">Producto</th>
              <th className="num">Monto</th>
              <th className="num solo-escritorio">Cuota</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visibles.map((f) => {
              const e = ESTADOS[f.estado] ?? { texto: f.estado, clase: "fija" };
              return (
                <tr key={f.id}>
                  <td style={{ fontWeight: 600 }}>
                    <Link to={`/prestamos/${f.id}`} className="enlace-fila">#{f.id}</Link>
                  </td>
                  <td>
                    {f.cliente}
                    <div className="ayuda" style={{ marginTop: 0 }}>
                      {f.rubro ? RUBRO_ETIQUETA[f.rubro] ?? f.rubro : ""} · {f.plazo} meses
                    </div>
                  </td>
                  <td className="solo-escritorio">{f.producto ? PRODUCTO[f.producto] ?? f.producto : "—"}</td>
                  <td className="num">{fmtS0(f.principal)}</td>
                  <td className="num solo-escritorio">
                    {Math.abs(f.cuota_max - f.cuota_min) < 1 ? fmtS0(f.cuota_min) : `${fmtS0(f.cuota_min)} – ${fmtS0(f.cuota_max)}`}
                  </td>
                  <td>
                    <span className={`etiqueta ${e.clase}`}>{e.texto}</span>
                  </td>
                  <td className="num" style={{ whiteSpace: "nowrap" }}>
                    {e.accion && (
                      <button
                        type="button"
                        className="btn btn-primario"
                        disabled={ocupado !== null}
                        onClick={() => void ejecutar(f.id, e.accion!)}
                      >
                        {ocupado === f.id ? "…" : e.boton}
                      </button>
                    )}{" "}
                    <Link to={`/prestamos/${f.id}`} className="btn" aria-label={`Ver detalle del préstamo ${f.id}`}>
                      Ver detalle
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
