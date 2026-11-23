import { useState } from "react";
import { api, Cliente, Prestamo, Propuesta } from "../api";
import { fmtS } from "../formato";

type Estado = { loanId: number; status: string; aviso?: string };

export default function RegistroCore({ cliente, propuesta }: { cliente: Cliente; propuesta: Propuesta }) {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<Prestamo | null>(null);

  async function ejecutar(fn: () => Promise<void>) {
    setOcupado(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  const registrar = () =>
    ejecutar(async () => {
      const { clientId } = await api.crearCliente(cliente);
      const { loanId } = await api.crearPrestamo(clientId, cliente);
      const loan = await api.prestamo(loanId);
      let aviso: string | undefined;
      // Fija en el core el mismo cronograma que vio el asesor (variaciones antes de aprobar, como Fineract)
      if (loan.numberOfRepayments === propuesta.plazo && Math.abs(loan.principal - propuesta.principal_aprobado) < 1) {
        await api.variaciones(loanId, propuesta.cronograma.map((f) => f.cuota));
      } else {
        aviso = "El core recalculó monto o plazo; revisa el cronograma registrado.";
      }
      setEstado({ loanId, status: loan.status.value, aviso });
    });

  const comando = (c: "approve" | "disburse") =>
    ejecutar(async () => {
      const r = await api.comando(estado!.loanId, c);
      setEstado({ ...estado!, status: r.status.value });
    });

  const verCronograma = () => ejecutar(async () => setModal(await api.prestamo(estado!.loanId)));

  return (
    <div className="tarjeta">
      <h2>Registro en el core (API compatible con Fineract)</h2>
      {!estado ? (
        <button className="btn btn-primario" disabled={ocupado} onClick={registrar}>
          {ocupado ? "Registrando…" : "Registrar solicitud"}
        </button>
      ) : (
        <>
          <div className="datos" style={{ marginBottom: 12 }}>
            <div className="dato">
              <span className="k">Préstamo</span>
              <span className="v">#{estado.loanId}</span>
            </div>
            <div className="dato">
              <span className="k">Estado</span>
              <span className="v">{estado.status}</span>
            </div>
          </div>
          {estado.aviso && <div className="info" style={{ marginBottom: 10 }}>{estado.aviso}</div>}
          <div className="fila">
            <button className="btn" disabled={ocupado || estado.status !== "Submitted and pending approval"} onClick={() => comando("approve")}>
              Aprobar
            </button>
            <button className="btn" disabled={ocupado || estado.status !== "Approved"} onClick={() => comando("disburse")}>
              Desembolsar
            </button>
            <button className="btn" disabled={ocupado} onClick={verCronograma}>
              Ver cronograma en core
            </button>
          </div>
        </>
      )}
      {error && <div className="aviso" style={{ marginTop: 10 }}>{error}</div>}
      {modal && (
        <div className="modal-fondo" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="fila" style={{ marginBottom: 10 }}>
              <h2 style={{ margin: 0 }}>
                Préstamo #{modal.id} · {modal.status.value}
              </h2>
              <div className="espacio" />
              <button className="btn" onClick={() => setModal(null)}>
                Cerrar
              </button>
            </div>
            <table>
              <thead>
                <tr>
                  <th className="num">Periodo</th>
                  <th className="num">Cuota</th>
                  <th className="num">Capital</th>
                  <th className="num">Interés</th>
                  <th className="num">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {modal.repaymentSchedule?.periods.map((p) => (
                  <tr key={p.period}>
                    <td className="num">{p.period}</td>
                    <td className="num">{fmtS(p.totalDueForPeriod)}</td>
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
