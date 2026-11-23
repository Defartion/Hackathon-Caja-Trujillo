import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fmtS0, nivelEstacionalidad, RUBRO_ETIQUETA } from "../formato";
import { useCartera } from "../useCartera";

export default function Bandeja() {
  const { datos, error } = useCartera();
  const [rubro, setRubro] = useState("");
  const [busca, setBusca] = useState("");
  const nav = useNavigate();

  const filas = useMemo(
    () =>
      (datos ?? []).filter(
        (c) => (!rubro || c.rubro === rubro) && c.cliente_id.toLowerCase().includes(busca.trim().toLowerCase()),
      ),
    [datos, rubro, busca],
  );

  if (error) return <div className="aviso">{error}</div>;
  if (!datos) return <div className="cargando">Cargando solicitudes…</div>;

  return (
    <div className="tarjeta">
      <div className="fila" style={{ marginBottom: 14 }}>
        <div>
          <h1 style={{ fontSize: 20 }}>Bandeja de solicitudes</h1>
          <div style={{ color: "var(--cf-gris-600)", marginTop: 4 }}>
            {filas.length} de {datos.length} solicitudes · elige una para ver la propuesta del agente
          </div>
        </div>
        <div className="espacio" />
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
        <label className="campo">
          Buscar código
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="C00012" />
        </label>
      </div>
      <table>
        <thead>
          <tr>
            <th>Código</th>
            <th>Rubro</th>
            <th>Región</th>
            <th className="num">Monto solicitado</th>
            <th className="num">Plazo</th>
            <th className="num">Ventas medias</th>
            <th className="num">Atraso máx.</th>
            <th>Estacionalidad</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((c) => {
            const est = nivelEstacionalidad(c.indice_estacionalidad);
            return (
              <tr key={c.cliente_id} className="clic" onClick={() => nav(`/cliente/${c.cliente_id}`)}>
                <td style={{ fontWeight: 600 }}>{c.cliente_id}</td>
                <td>{RUBRO_ETIQUETA[c.rubro] ?? c.rubro}</td>
                <td>{c.region}</td>
                <td className="num">{fmtS0(c.principal)}</td>
                <td className="num">{c.plazo} m</td>
                <td className="num">{fmtS0(c.ventas_medias)}</td>
                <td className="num" style={{ color: c.dias_atraso_max > 8 ? "var(--cf-rojo)" : undefined }}>
                  {c.dias_atraso_max} d
                </td>
                <td>
                  <span className={`etiqueta ${est.clase}`}>{est.texto}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {filas.length === 0 && <div className="cargando">No hay solicitudes con ese filtro.</div>}
    </div>
  );
}
