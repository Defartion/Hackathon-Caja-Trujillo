import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Cliente, RespuestaPropuesta } from "../api";
import Bitacora from "../components/Bitacora";
import Comparativa from "../components/Comparativa";
import GraficoCuotas from "../components/GraficoCuotas";
import GraficoVentas from "../components/GraficoVentas";
import RegistroCore from "../components/RegistroCore";
import TablaCronograma from "../components/TablaCronograma";
import TarjetaProducto from "../components/TarjetaProducto";
import { fmtPct, fmtS0, MESES, nivelEstacionalidad, RUBRO_ETIQUETA } from "../formato";
import { useCartera } from "../useCartera";

export default function Ficha() {
  const { id } = useParams();
  const { datos, error: errCartera } = useCartera();
  const base = datos?.find((c) => c.cliente_id === id);

  const [edicion, setEdicion] = useState<Pick<Cliente, "principal" | "plazo" | "ajuste_asesor"> | null>(null);
  const [resp, setResp] = useState<RespuestaPropuesta | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calcular = useCallback(async (c: Cliente) => {
    setCargando(true);
    setError(null);
    try {
      setResp(await api.propuesta(c));
      setCliente(c);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (base) {
      setEdicion({ principal: base.principal, plazo: base.plazo, ajuste_asesor: base.ajuste_asesor });
      setResp(null);
      void calcular(base);
    }
  }, [base, calcular]);

  if (errCartera) return <div className="aviso">{errCartera}</div>;
  if (!datos) return <div className="cargando">Cargando…</div>;
  if (!base || !edicion) return <div className="aviso">No existe la solicitud {id}. <Link to="/">Volver a la bandeja</Link></div>;

  const est = nivelEstacionalidad(base.indice_estacionalidad);
  const recalcular = () => void calcular({ ...base, ...edicion });
  const p = resp?.propuesta;

  return (
    <div className="rejilla">
      <div className="tarjeta">
        <div className="fila" style={{ marginBottom: 12 }}>
          <Link to="/">← Bandeja</Link>
          <h1 style={{ fontSize: 20 }}>Solicitud {base.cliente_id}</h1>
          <span className={`etiqueta ${est.clase}`}>Estacionalidad {est.texto.toLowerCase()}</span>
        </div>
        <div className="datos">
          <div className="dato"><span className="k">Rubro</span><span className="v">{RUBRO_ETIQUETA[base.rubro]}</span></div>
          <div className="dato"><span className="k">Región</span><span className="v">{base.region}</span></div>
          <div className="dato"><span className="k">Ventas medias</span><span className="v">{fmtS0(base.ventas_medias)}</span></div>
          <div className="dato"><span className="k">Margen</span><span className="v">{fmtPct(base.margen)}</span></div>
          <div className="dato"><span className="k">Gasto familiar</span><span className="v">{fmtS0(base.gasto_familiar)}</span></div>
          <div className="dato"><span className="k">Otras cuotas</span><span className="v">{fmtS0(base.otras_cuotas)}</span></div>
          <div className="dato"><span className="k">Atraso máx.</span><span className="v">{base.dias_atraso_max} días</span></div>
          <div className="dato"><span className="k">Primera cuota</span><span className="v">{MESES[base.mes_desembolso]}</span></div>
        </div>
      </div>

      <div className="tarjeta">
        <h2>Simular cambios en la solicitud</h2>
        <div className="fila">
          <label className="campo">
            Monto (S/)
            <input type="number" min={500} step={100} value={edicion.principal}
              onChange={(e) => setEdicion({ ...edicion, principal: Number(e.target.value) })} />
          </label>
          <label className="campo">
            Plazo
            <select value={edicion.plazo} onChange={(e) => setEdicion({ ...edicion, plazo: Number(e.target.value) })}>
              {[12, 18, 24].map((m) => <option key={m} value={m}>{m} meses</option>)}
            </select>
          </label>
          <label className="campo" style={{ minWidth: 220 }}>
            Ajuste del asesor a las ventas: {Math.round((edicion.ajuste_asesor - 1) * 100)}%
            <input type="range" min={0.9} max={1.1} step={0.01} value={edicion.ajuste_asesor}
              onChange={(e) => setEdicion({ ...edicion, ajuste_asesor: Number(e.target.value) })} />
          </label>
          <button className="btn btn-primario" disabled={cargando || edicion.principal <= 0} onClick={recalcular}>
            {cargando ? "Calculando…" : "Recalcular"}
          </button>
        </div>
      </div>

      {error && <div className="aviso">{error}</div>}
      {!resp && cargando && <div className="cargando">El agente está evaluando la solicitud…</div>}

      {resp && p && cliente && (
        <div style={{ opacity: cargando ? 0.55 : 1, transition: "opacity .2s" }} className="rejilla">
          <div className="rejilla r-ficha">
            <div className="tarjeta">
              <h2>Ventas: histórico y pronóstico con incertidumbre</h2>
              <GraficoVentas historial={resp.historial_ventas} pronostico={resp.pronostico} mesInicio={cliente.mes_desembolso} />
            </div>
            <TarjetaProducto p={p} />
          </div>

          <div className="tarjeta">
            <h2>Explicación para el cliente</h2>
            <div className="explicacion">{p.explicacion}</div>
          </div>

          <div className="rejilla r-ficha">
            <div className="tarjeta">
              <h2>Cuota vs. capacidad de pago (en ámbar: excede la capacidad)</h2>
              <GraficoCuotas fija={resp.comparativa.fija.cuotas} flex={resp.comparativa.cuotaflex.cuotas}
                capacidad={resp.capacidad} mesInicio={cliente.mes_desembolso} />
            </div>
            <Bitacora pasos={p.bitacora} />
          </div>

          <Comparativa fija={resp.comparativa.fija} flex={resp.comparativa.cuotaflex} n={resp.comparativa.n_escenarios} />
          <TablaCronograma filas={p.cronograma} capacidad={resp.capacidad} />
          <RegistroCore key={JSON.stringify(edicion) + p.plazo} cliente={cliente} propuesta={p} />
        </div>
      )}
    </div>
  );
}
