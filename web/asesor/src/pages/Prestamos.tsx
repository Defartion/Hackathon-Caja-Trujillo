import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Prestamo, PrestamoListado } from "../api";
import { fmtS, fmtS0, RUBRO_ETIQUETA } from "../formato";

const ESTADOS: Record<string, { texto: string; clase: string; accion?: "approve" | "disburse"; boton?: string }> = {
  "Submitted and pending approval": { texto: "Falta aprobar", clase: "media", accion: "approve", boton: "Aprobar" },
  Approved: { texto: "Falta desembolsar", clase: "aplazamiento", accion: "disburse", boton: "Desembolsar" },
  Active: { texto: "Activo", clase: "baja" },
  "Closed (obligations met)": { texto: "Pagado", clase: "fija" },
};

const PRODUCTO: Record<string, string> = {
  fija: "Cuota fija",
  aplazamiento: "Fija con aplazamientos",
  estacional: "Por temporada",
};

type Filtro = "todos" | "pendientes" | "activos";

export default function Prestamos() {
  const [filas, setFilas] = useState<PrestamoListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<number | null>(null);
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [detalle, setDetalle] = useState<Prestamo | null>(null);

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

  const verDetalle = async (id: number) => {
    try {
      setDetalle(await api.prestamo(id));
    } catch (e) {
      setError((e as Error).message);
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
          <h1 style={{ fontSize: 20 }}>Préstamos registrados</h1>
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
                  <td style={{ fontWeight: 600 }}>#{f.id}</td>
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
                    <button type="button" className="btn" onClick={() => void verDetalle(f.id)}>
                      Cronograma
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {detalle && (
        <div className="modal-fondo" onClick={() => setDetalle(null)}>
          <div className="modal" role="dialog" aria-label={`Cronograma del préstamo ${detalle.id}`} onClick={(e) => e.stopPropagation()}>
            <div className="fila" style={{ marginBottom: 10, alignItems: "center" }}>
              <h2 style={{ margin: 0 }}>Préstamo #{detalle.id}</h2>
              <span className={`etiqueta ${ESTADOS[detalle.status.value]?.clase ?? "fija"}`}>
                {ESTADOS[detalle.status.value]?.texto ?? detalle.status.value}
              </span>
              <div className="espacio" />
              <button type="button" className="btn" onClick={() => setDetalle(null)}>
                Cerrar
              </button>
            </div>
            <table>
              <thead>
                <tr>
                  <th className="num">Cuota</th>
                  <th className="num">Monto</th>
                  <th className="num">Capital</th>
                  <th className="num">Interés</th>
                  <th className="num">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {detalle.repaymentSchedule?.periods.map((p) => (
                  <tr key={p.period}>
                    <td className="num">{p.period}</td>
                    <td className="num" style={{ fontWeight: 600 }}>{fmtS(p.totalDueForPeriod)}</td>
                    <td className="num">{fmtS(p.principalDue)}</td>
                    <td className="num">{fmtS(p.interestDue)}</td>
                    <td className="num">{fmtS(p.principalLoanBalanceOutstanding)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
