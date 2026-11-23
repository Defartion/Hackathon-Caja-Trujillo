import { useState } from "react";
import { FilaCronograma } from "../api";
import { fmtS } from "../formato";

export default function TablaCronograma({ filas, capacidad }: { filas: FilaCronograma[]; capacidad: number[] }) {
  const [abierta, setAbierta] = useState(false);
  return (
    <div className="tarjeta">
      <div className="fila">
        <h2 style={{ margin: 0 }}>Cronograma propuesto</h2>
        <div className="espacio" />
        <button className="btn" onClick={() => setAbierta(!abierta)}>
          {abierta ? "Ocultar" : `Ver ${filas.length} cuotas`}
        </button>
      </div>
      {abierta && (
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th className="num">N°</th>
              <th>Mes</th>
              <th className="num">Cuota</th>
              <th className="num">Interés</th>
              <th className="num">Capital</th>
              <th className="num">Saldo</th>
              <th className="num">Capacidad p25</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={f.numero}>
                <td className="num">{f.numero}</td>
                <td>{f.mes}</td>
                <td className="num" style={{ fontWeight: 600, color: f.cuota > capacidad[i] + 0.5 ? "var(--cf-ambar)" : undefined }}>
                  {fmtS(f.cuota)}
                </td>
                <td className="num">{fmtS(f.interes)}</td>
                <td className="num">{fmtS(f.capital)}</td>
                <td className="num">{fmtS(f.saldo)}</td>
                <td className="num">{fmtS(capacidad[i])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
