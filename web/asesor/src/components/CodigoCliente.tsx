import { useEffect, useState } from "react";
import { api, LlaveCliente } from "../api";

/** Dónde abre el cliente su app: en el despliegue, /cliente/ del mismo sitio; en local, el puerto 5174. */
function enlaceCliente(prestamo: number): string {
  const base = import.meta.env.BASE_URL !== "/" ? `${window.location.origin}/cliente/` : "http://localhost:5174/";
  return `${base}?loanId=${prestamo}`;
}

const agrupar = (c: string) => `${c.slice(0, 3)} ${c.slice(3)}`;

/**
 * Fase 4: la llave personal del cliente. El asesor la ve al desembolsar y en el detalle del préstamo,
 * la envía por WhatsApp o la copia, y puede generar otra (la anterior deja de servir).
 */
export default function CodigoCliente({ prestamo }: { prestamo: number }) {
  const [llave, setLlave] = useState<LlaveCliente | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    let vivo = true;
    api
      .llave(prestamo)
      .then((l) => vivo && setLlave(l))
      .catch((e: Error) => vivo && setError(e.message));
    return () => {
      vivo = false;
    };
  }, [prestamo]);

  if (error) return <div className="aviso">No se pudo leer el código del cliente. {error}</div>;
  if (!llave) return <div className="ayuda">Cargando el código del cliente…</div>;

  const nombre = llave.cliente?.trim().split(/\s+/)[0];
  const mensaje =
    `Hola${nombre ? ` ${nombre}` : ""}: ya puedes ver tu crédito en Thinku. ` +
    `Entra a ${enlaceCliente(llave.prestamo)} con tu número de préstamo ${llave.prestamo} ` +
    `y tu código ${llave.codigo}. No lo compartas con nadie.`;

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(mensaje);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setVisible(true);
    }
  };

  const regenerar = async () => {
    setOcupado(true);
    try {
      setLlave(await api.regenerarLlave(llave.prestamo));
      setVisible(true);
      setConfirmar(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="codigo-cliente" aria-label="Código de acceso del cliente">
      <div className="codigo-cliente__cab">
        <div>
          <div className="k-mini">Acceso del cliente</div>
          <div className="ayuda" style={{ marginTop: 0 }}>
            Entra a su app con el préstamo N° {llave.prestamo} y este código. Solo ve su propio crédito.
          </div>
        </div>
        <div className="codigo-cliente__valor">
          <span className="codigo-cliente__digitos" aria-live="polite">
            {visible ? agrupar(llave.codigo) : "••• •••"}
          </span>
          <button type="button" className="btn-enlace" onClick={() => setVisible(!visible)}>
            {visible ? "Ocultar" : "Mostrar código"}
          </button>
        </div>
      </div>
      <div className="acciones" style={{ marginTop: 10 }}>
        <a className="btn btn-primario" href={`https://wa.me/?text=${encodeURIComponent(mensaje)}`} target="_blank" rel="noreferrer">
          Enviar por WhatsApp
        </a>
        <button type="button" className="btn" onClick={copiar}>
          {copiado ? "✓ Mensaje copiado" : "Copiar mensaje"}
        </button>
        {confirmar ? (
          <span className="confirmar-linea" role="group" aria-label="Confirmar código nuevo">
            El código actual dejará de funcionar.
            <button type="button" className="btn btn-peligro" disabled={ocupado} onClick={regenerar}>
              {ocupado ? "Generando…" : "Sí, generar otro"}
            </button>
            <button type="button" className="btn-enlace" onClick={() => setConfirmar(false)}>
              Cancelar
            </button>
          </span>
        ) : (
          <button type="button" className="btn" onClick={() => setConfirmar(true)}>
            Generar otro código
          </button>
        )}
      </div>
    </div>
  );
}
