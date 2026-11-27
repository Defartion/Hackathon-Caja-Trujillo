import { useCallback, useEffect, useRef, useState } from 'react';
import {
  API_URL,
  ESPERADO_S,
  ErrorApi,
  SEMILLA,
  TAMANOS,
  correr,
  obtenerEscenarios,
  obtenerParametros,
} from './api';
import type { Escenario, ParametroEditable, TamanoId } from './api';
import { redondearAPaso } from './formato';
import EstadoEnfen from './components/EstadoEnfen';
import GraficoDispersion from './components/GraficoDispersion';
import GraficoHistograma from './components/GraficoHistograma';
import GraficoProductos from './components/GraficoProductos';
import GraficoRubros from './components/GraficoRubros';
import Historial from './components/Historial';
import type { Corrida } from './components/Historial';
import Indicadores from './components/Indicadores';
import PanelControles from './components/PanelControles';
import AlertaNino from './components/AlertaNino';
import Avisos from './components/Avisos';
import NavSupervisor from './components/NavSupervisor';
import type { Vista } from './components/NavSupervisor';
import Marca from './marca';
import { useGuardado } from './apariencia';
import MenuExportar from './MenuExportar';
import { documentoCorrida } from './exportarCorrida';

const MAX_HISTORIAL = 5;

export default function App() {
  const [parametros, setParametros] = useState<ParametroEditable[]>([]);
  const [escenarios, setEscenarios] = useState<Escenario[]>([]);
  const [cargaError, setCargaError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const [valores, setValores] = useState<Record<string, number>>({});
  const [activo, setActivo] = useState<string | null>('base');
  const [replanificar, setReplanificar] = useState(true);
  const [tamano, setTamano] = useState<TamanoId>('rapido');

  const [vista, setVista] = useState<Vista>('simular');
  const [corriendo, setCorriendo] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [progreso, setProgreso] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [corridas, setCorridas] = useState<Corrida[]>([]);
  // Columnas plegables: el menú (misma preferencia que en la app del asesor) y el panel de controles.
  const [menu, setMenu] = useGuardado('cuotaflex.menu', 'abierto', ['abierto', 'plegado'] as const);
  const [controles, setControles] = useGuardado('cuotaflex.tablero.controles', 'abierto', ['abierto', 'plegado'] as const);
  const [mostrada, setMostrada] = useState<number | null>(null);
  const contador = useRef(0);
  const medidos = useRef<Record<string, number>>({});
  const inicio = useRef(0);
  const esperado = useRef(7);

  const cargar = useCallback(async () => {
    setCargando(true);
    setCargaError(null);
    try {
      const [p, e] = await Promise.all([obtenerParametros(), obtenerEscenarios()]);
      setParametros(p);
      setEscenarios(e);
      setValores(Object.fromEntries(p.map((x) => [x.ruta, x.valor])));
    } catch (err) {
      setCargaError(err instanceof ErrorApi ? err.message : `No se pudo conectar con la API (${API_URL}).`);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // Al abrir, corre una vez el escenario base para que el supervisor vea resultados sin pulsar nada.
  const autoCorrida = useRef(false);

  // Temporizador de la simulación en curso.
  useEffect(() => {
    if (!corriendo) return;
    const id = setInterval(() => {
      const s = (performance.now() - inicio.current) / 1000;
      setSegundos(s);
      setProgreso(Math.min(95, (s / esperado.current) * 95));
    }, 100);
    return () => clearInterval(id);
  }, [corriendo]);

  const base: Record<string, number> = Object.fromEntries(parametros.map((x) => [x.ruta, x.valor]));

  const diff = (vals: Record<string, number>): Record<string, number> => {
    const out: Record<string, number> = {};
    for (const x of parametros) {
      const v = redondearAPaso(vals[x.ruta] ?? x.valor, x.paso);
      if (Math.abs(v - x.valor) > 1e-9) out[x.ruta] = v;
    }
    return out;
  };

  const ejecutar = async (vals: Record<string, number>, escenarioId: string | null) => {
    if (corriendo) return;
    const cambios = diff(vals);
    const esc = escenarios.find((e) => e.id === escenarioId);
    const nombre = esc?.nombre ?? (Object.keys(cambios).length === 0 ? 'Base' : 'Personalizado');
    const clave = `${tamano}|${replanificar}`;
    esperado.current = medidos.current[clave] ?? ESPERADO_S[tamano];
    inicio.current = performance.now();
    setSegundos(0);
    setProgreso(0);
    setError(null);
    setCorriendo(true);
    try {
      const t = TAMANOS[tamano];
      const resp = await correr({
        n_clientes: t.n_clientes,
        n_escenarios: t.n_escenarios,
        semilla: SEMILLA,
        replanificar,
        cambios,
      });
      if (!resp.desde_cache) {
        medidos.current[clave] = (performance.now() - inicio.current) / 1000;
      }
      setProgreso(100);
      contador.current += 1;
      const num = contador.current;
      setCorridas((prev) =>
        [{ num, escenario: nombre, cambios, tamano, replanificar, resp }, ...prev].slice(0, MAX_HISTORIAL),
      );
      setMostrada(num);
      await new Promise((r) => setTimeout(r, 200));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido al simular.');
    } finally {
      setCorriendo(false);
    }
  };

  const elegirEscenario = (e: Escenario) => {
    if (corriendo) return;
    const vals = { ...base, ...e.cambios };
    setValores(vals);
    setActivo(e.id);
    void ejecutar(vals, e.id);
  };

  useEffect(() => {
    if (autoCorrida.current || cargando || parametros.length === 0) return;
    autoCorrida.current = true;
    void ejecutar(Object.fromEntries(parametros.map((x) => [x.ruta, x.valor])), 'base');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargando, parametros]);

  const cambiarParametro = (ruta: string, v: number) => {
    setValores((prev) => ({ ...prev, [ruta]: v }));
    setActivo(null);
  };

  const restablecer = () => {
    setValores(base);
    setActivo(null);
  };

  const hayCambios = Object.keys(diff(valores)).length > 0;
  const actual = corridas.find((c) => c.num === mostrada) ?? null;

  let estado = 'API conectada';
  let estadoError = false;
  if (cargaError) {
    estado = 'Sin conexión con la API';
    estadoError = true;
  } else if (cargando) {
    estado = 'Conectando con la API…';
  } else if (corriendo) {
    estado = 'Simulando…';
  } else if (error) {
    estado = 'La última simulación falló';
    estadoError = true;
  } else if (actual) {
    estado = `Mostrando corrida #${actual.num} · API conectada`;
  }

  return (
    <div className="app">
      <header className="cabecera">
        <Marca tam={32} />
        <div className="cab-sep" aria-hidden="true" />
        <div>
          <div className="titulo-tablero">Tablero de simulación</div>
          <div className="subtitulo-tablero">Cuota fija vs. CuotaFlex en una cartera sintética de La Libertad</div>
        </div>
        <div className={`estado-api ${estadoError ? 'error' : ''}`} role="status">
          {estado}
        </div>
        <EstadoEnfen />
      </header>

      <div
        className={`cuerpo ${vista === 'simular' ? '' : 'sin-panel'} ${menu === 'plegado' ? 'nav-plegada' : ''} ${
          controles === 'plegado' ? 'panel-plegado' : ''}`}
      >
        <NavSupervisor
          vista={vista}
          onVista={setVista}
          plegado={menu === 'plegado'}
          onPlegar={() => setMenu(menu === 'plegado' ? 'abierto' : 'plegado')}
        />
        {vista !== 'simular' ? (
          <main className="principal">{vista === 'alerta' ? <AlertaNino /> : <Avisos />}</main>
        ) : (
        <>
        {parametros.length > 0 ? (
          <PanelControles
            parametros={parametros}
            escenarios={escenarios}
            valores={valores}
            escenarioActivo={activo}
            personalizado={hayCambios}
            replanificar={replanificar}
            tamano={tamano}
            corriendo={corriendo}
            segundos={segundos}
            progreso={progreso}
            onEscenario={elegirEscenario}
            onCambio={cambiarParametro}
            onRestablecer={restablecer}
            onModo={setReplanificar}
            onTamano={setTamano}
            onSimular={() => void ejecutar(valores, activo)}
            plegado={controles === 'plegado'}
            onPlegar={() => setControles(controles === 'plegado' ? 'abierto' : 'plegado')}
          />
        ) : (
          <aside className="panel" />
        )}

        <main className="principal">
          {cargaError ? (
            <div className="centro">
              <h2>No se pudo cargar el tablero</h2>
              <p>{cargaError}</p>
              <button type="button" className="btn-primario" onClick={() => void cargar()}>
                Reintentar
              </button>
            </div>
          ) : cargando ? (
            <div className="centro">
              <p>Conectando con la API…</p>
            </div>
          ) : (
            <>
              {error && (
                <div className="banner-error" role="alert">
                  <p>{error}</p>
                  <button type="button" aria-label="Cerrar aviso" onClick={() => setError(null)}>
                    ×
                  </button>
                </div>
              )}
              {actual ? (
                <div className={`resultados ${corriendo ? 'cargando' : ''}`} aria-busy={corriendo}>
                  <div className="cab-corrida">
                    <span>
                      <b>Corrida #{actual.num}</b> · {actual.escenario} · {TAMANOS[actual.tamano].n_clientes} créditos ×{' '}
                      {TAMANOS[actual.tamano].n_escenarios} escenarios · {actual.replanificar ? 'Completo' : 'Solo cronograma'}{' '}
                      · {actual.resp.duracion_s.toFixed(1)} s{actual.resp.desde_cache ? ' · desde caché' : ''}
                    </span>
                    <MenuExportar claseBoton="btn-sec btn-exportar" etiqueta="Exportar resultados" documento={() => documentoCorrida(actual)} />
                  </div>
                  <Indicadores resumen={actual.resp.resumen} />
                  <div className="graficos">
                    <GraficoRubros resumen={actual.resp.resumen} />
                    <GraficoHistograma h={actual.resp.histograma_vpn} />
                    <GraficoDispersion datos={actual.resp.dispersion} />
                    <GraficoProductos mix={actual.resp.resumen.mix_productos} />
                    <Historial
                      corridas={corridas}
                      mostrada={mostrada}
                      parametros={parametros}
                      onElegir={setMostrada}
                    />
                  </div>
                </div>
              ) : (
                <div className="vacio">
                  <h2>Elige un escenario o pulsa Simular</h2>
                  <p>Compara la cuota fija con CuotaFlex sobre una cartera sintética.</p>
                  <button
                    type="button"
                    className="btn-primario"
                    disabled={corriendo}
                    onClick={() => {
                      const b = escenarios.find((e) => e.id === 'base');
                      if (b) elegirEscenario(b);
                      else void ejecutar(base, null);
                    }}
                  >
                    {corriendo ? 'Simulando…' : 'Simular escenario Base'}
                  </button>
                </div>
              )}
            </>
          )}
        </main>
        </>
        )}
      </div>

      <footer className="pie">
        Datos 100% sintéticos. Parámetros referenciales a calibrar con Caja Trujillo.
      </footer>
    </div>
  );
}
