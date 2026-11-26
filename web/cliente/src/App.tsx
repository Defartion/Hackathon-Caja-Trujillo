import { useEffect, useRef, useState } from 'react'
import MenuCliente from './MenuCliente'
import {
  CalendarDays, CheckCircle2, CircleHelp, FlaskConical, House, LoaderCircle,
  TriangleAlert, WalletCards,
} from 'lucide-react'
import {
  api, ErrorApi, guardarPrestamo, leerPrestamo, prestamoEnUrl, quitarPrestamoDeUrl,
  type Prestamo, type ProductoDemo, type VistaPrevia,
} from './api'
import { Aplazamiento, Ayuda, Cronograma, Inicio, MOSTRAR_CREDITO_VIGENTE } from './screens'

type Pantalla = 'inicio' | 'cronograma' | 'aplazar' | 'actualizado' | 'ayuda'
type Accion = 'crear' | 'alerta' | 'pago' | 'alivio' | 'preview' | 'confirmar' | 'refrescar'

const navegacion = [
  { pantalla: 'inicio', nombre: 'Inicio', Icono: House },
  { pantalla: 'cronograma', nombre: 'Cronograma', Icono: CalendarDays },
  { pantalla: 'ayuda', nombre: 'Ayuda', Icono: CircleHelp },
] as const

function mensajeError(error: unknown): string {
  if (error instanceof ErrorApi) return error.message
  if (error instanceof Error && error.message.startsWith('No pudimos conectar')) return error.message
  return 'Algo salió mal. Intenta de nuevo.'
}

function PanelDemo({
  activo, accion, alertaCargando, onCrear, onAlerta, onConsultarAlerta,
}: {
  activo: boolean | null
  accion: Accion | null
  alertaCargando: boolean
  onCrear: (producto: ProductoDemo) => void
  onAlerta: () => void
  onConsultarAlerta: () => void
}) {
  const [producto, setProducto] = useState<ProductoDemo>('estacional')

  return (
    <section className="demo-panel" aria-labelledby="demo-title">
      <div className="demo-panel__heading">
        <FlaskConical size={21} aria-hidden="true" />
        <h2 id="demo-title">Panel de demo</h2>
      </div>
      {MOSTRAR_CREDITO_VIGENTE && (
      <fieldset disabled={accion !== null}>
        <legend>Tipo de crédito</legend>
        <div className="demo-options">
          <label>
            <input type="radio" name="producto" checked={producto === 'estacional'} onChange={() => setProducto('estacional')} />
            Estacional
          </label>
          <label>
            <input type="radio" name="producto" checked={producto === 'aplazamiento'} onChange={() => setProducto('aplazamiento')} />
            Con aplazamientos
          </label>
        </div>
      </fieldset>
      )}
      <button className="button" onClick={() => onCrear(producto)} disabled={accion !== null}>
        {accion === 'crear' ? 'Creando cliente…' : 'Crear cliente de demo'}
      </button>
      {MOSTRAR_CREDITO_VIGENTE && (
      <div className="demo-panel__alert">
        <span>Alerta El Niño</span>
        {activo === null ? (
          <button
            type="button"
            disabled={alertaCargando || accion !== null}
            onClick={onConsultarAlerta}
          >
            {alertaCargando || accion === 'alerta' ? 'Consultando…' : 'Consultar estado'}
          </button>
        ) : (
          <button
            type="button"
            role="switch"
            aria-label="Alerta El Niño"
            aria-checked={activo}
            disabled={alertaCargando || accion !== null}
            onClick={onAlerta}
          >
            <span>{accion === 'alerta' ? 'Actualizando…' : activo ? 'Activa' : 'Inactiva'}</span>
            <span className="switch-track" aria-hidden="true"><span /></span>
          </button>
        )}
      </div>
      )}
    </section>
  )
}

export default function App() {
  const [idEnUrl] = useState(prestamoEnUrl)
  const [idInicial] = useState(() => idEnUrl ?? leerPrestamo())
  const [id, setId] = useState<number | null>(idInicial)
  const [prestamo, setPrestamo] = useState<Prestamo | null>(null)
  const [cargando, setCargando] = useState(idInicial !== null)
  const [desactualizado, setDesactualizado] = useState(false)
  const [pantalla, setPantalla] = useState<Pantalla>('inicio')
  const [accion, setAccion] = useState<Accion | null>(null)
  const [alertaDemo, setAlertaDemo] = useState<boolean | null>(null)
  const [alertaCargando, setAlertaCargando] = useState(true)
  const [cuota, setCuota] = useState<number | null>(null)
  const [preview, setPreview] = useState<VistaPrevia | null>(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const ocupada = useRef(false)
  const contenido = useRef<HTMLElement>(null)
  const demo = new URLSearchParams(window.location.search).get('demo') === '1'

  useEffect(() => {
    const controller = new AbortController()
    if (idInicial !== null) {
      api.prestamo(idInicial, controller.signal)
        .then(datos => {
          if (controller.signal.aborted) return
          setPrestamo(datos)
          guardarPrestamo(datos.loanId)
        })
        .catch(causa => {
          if (controller.signal.aborted) return
          if (causa instanceof ErrorApi && causa.estado === 404) {
            setId(null)
            if (idEnUrl !== null) setError(mensajeError(causa))
            if (leerPrestamo() === idInicial) guardarPrestamo(null)
            quitarPrestamoDeUrl()
          } else {
            setError(mensajeError(causa))
            setDesactualizado(true)
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setCargando(false)
        })
    }
    api.estadoElNino(controller.signal)
      .then(datos => {
        if (!controller.signal.aborted) setAlertaDemo(datos.activo)
      })
      .catch(() => {})
      .finally(() => {
        if (!controller.signal.aborted) setAlertaCargando(false)
      })
    return () => controller.abort()
  }, [idEnUrl, idInicial])

  function desplazarAlInicio() {
    window.scrollTo(0, 0)
    contenido.current?.focus({ preventScroll: true })
  }

  function irA(destino: Pantalla) {
    setPantalla(destino)
    setError('')
    setAviso('')
    setPreview(null)
    desplazarAlInicio()
  }

  async function ejecutar(operacion: Accion, tarea: () => Promise<void>) {
    if (ocupada.current) return
    ocupada.current = true
    setAccion(operacion)
    setError('')
    setAviso('')
    try {
      await tarea()
    } catch (causa) {
      setError(mensajeError(causa))
    } finally {
      ocupada.current = false
      setAccion(null)
    }
  }

  async function cargarCredito(loanId: number) {
    setId(loanId)
    try {
      const datos = await api.prestamo(loanId)
      setPrestamo(datos)
      setAlertaDemo(datos.elNino.activo)
      guardarPrestamo(datos.loanId)
      setDesactualizado(false)
    } catch (causa) {
      if (causa instanceof ErrorApi && causa.estado === 404) {
        setPrestamo(null)
        setId(null)
        setDesactualizado(false)
        guardarPrestamo(null)
        quitarPrestamoDeUrl()
      } else {
        setDesactualizado(true)
      }
      throw causa
    }
  }

  function crearDemo(producto: ProductoDemo) {
    void ejecutar('crear', async () => {
      const datos = await api.crearDemo(producto)
      quitarPrestamoDeUrl()
      setPantalla('inicio')
      setPreview(null)
      await cargarCredito(datos.loanId)
      desplazarAlInicio()
    })
  }

  function cambiarAlerta() {
    if (alertaActiva === null) return
    void ejecutar('alerta', async () => {
      const datos = await api.cambiarAlerta(!alertaActiva)
      setAlertaDemo(datos.activo)
      if (id !== null) await cargarCredito(id)
      setAviso(datos.activo ? 'Alerta El Niño activada en la demo.' : 'Alerta El Niño desactivada en la demo.')
      desplazarAlInicio()
    })
  }

  function consultarAlerta() {
    void ejecutar('alerta', async () => {
      const datos = await api.estadoElNino()
      setAlertaDemo(datos.activo)
    })
  }

  function pagar() {
    if (!prestamo?.proximaCuota) return
    void ejecutar('pago', async () => {
      await api.pagar(prestamo.loanId)
      setAviso('Tu pago de demo quedó registrado.')
      await cargarCredito(prestamo.loanId)
      desplazarAlInicio()
    })
  }

  function aplicarAlivio() {
    if (!prestamo?.elNino.puedeAplicar) return
    void ejecutar('alivio', async () => {
      await api.usarAlivio(prestamo.loanId)
      setAviso('Alivio aplicado. Ya puedes revisar tu nuevo monto.')
      await cargarCredito(prestamo.loanId)
      desplazarAlInicio()
    })
  }

  function iniciarAplazamiento() {
    setCuota(null)
    irA('aplazar')
  }

  function verVistaPrevia() {
    if (!prestamo || cuota === null) return
    void ejecutar('preview', async () => {
      setPreview(await api.previsualizar(prestamo.loanId, cuota))
      desplazarAlInicio()
    })
  }

  function confirmarAplazamiento() {
    if (!prestamo || cuota === null || !preview) return
    void ejecutar('confirmar', async () => {
      try {
        await api.aplazar(prestamo.loanId, cuota, preview.revision)
      } catch (causa) {
        if (causa instanceof ErrorApi && [400, 409].includes(causa.estado)) {
          setPreview(null)
          setCuota(null)
          await cargarCredito(prestamo.loanId)
          desplazarAlInicio()
        }
        throw causa
      }
      setPantalla('actualizado')
      setPreview(null)
      try {
        await cargarCredito(prestamo.loanId)
      } catch (causa) {
        setAviso('Tu aplazamiento quedó confirmado.')
        throw causa
      }
      desplazarAlInicio()
    })
  }

  const bloqueado = accion !== null
  const listo = !cargando && !desactualizado && prestamo !== null
  const mostrarDemo = !cargando && (prestamo === null || demo)
    && (pantalla === 'inicio' || !listo)
  const alertaActiva = desactualizado ? alertaDemo : prestamo?.elNino.activo ?? alertaDemo
  const pestanaActiva = pantalla === 'aplazar' ? 'inicio' : pantalla === 'actualizado' ? 'cronograma' : pantalla

  return (
    <div className={`app-shell ${listo ? 'app-shell--nav' : ''}`}>
      <header className="app-header">
        <div className="brand">
          <span className="brand__symbol"><WalletCards aria-hidden="true" size={22} /></span>
          <span>Cuota<span className="brand__accent">Flex</span></span>
        </div>
        <MenuCliente prestamoId={id} />
      </header>
      <main ref={contenido} tabIndex={-1} className="main-content">
        {error && (
          <div className="feedback feedback--error" role="alert">
            <TriangleAlert size={21} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}
        {aviso && (
          <div className="feedback feedback--success" role="status">
            <CheckCircle2 size={21} aria-hidden="true" />
            <span>{aviso}</span>
          </div>
        )}
        {cargando && (
          <div className="loading" role="status">
            <LoaderCircle aria-hidden="true" size={21} /> Cargando tu crédito…
          </div>
        )}
        {!cargando && desactualizado && id !== null && (
          <section className="surface retry">
            <h1>Vuelve a cargar tu crédito</h1>
            <p>Así podrás ver tus cuotas actualizadas.</p>
            <button className="button button--primary" disabled={bloqueado} onClick={() => void ejecutar('refrescar', () => cargarCredito(id))}>
              {accion === 'refrescar' ? 'Cargando…' : 'Volver a cargar'}
            </button>
          </section>
        )}
        {!cargando && !desactualizado && !prestamo && (
          <section className="empty-state">
            <div className="empty-state__icon"><WalletCards size={28} aria-hidden="true" /></div>
            <h1>Hola, qué gusto verte</h1>
            <p>Crea un crédito de demo para consultar sus cuotas y probar cómo funciona CuotaFlex.</p>
          </section>
        )}
        {listo && (
          <>
            {pantalla === 'inicio' && (
              <Inicio
                prestamo={prestamo}
                accion={accion}
                bloqueado={bloqueado}
                onCronograma={() => irA('cronograma')}
                onPagar={pagar}
                onAplazar={iniciarAplazamiento}
                onAlivio={aplicarAlivio}
              />
            )}
            {(pantalla === 'cronograma' || pantalla === 'actualizado') && (
              <Cronograma prestamo={prestamo} actualizado={pantalla === 'actualizado'} bloqueado={bloqueado} onInicio={() => irA('inicio')} />
            )}
            {pantalla === 'aplazar' && (
              <Aplazamiento
                cronograma={prestamo.cronograma}
                restantes={prestamo.aplazamientosRestantes}
                seleccionada={cuota}
                preview={preview}
                bloqueado={bloqueado}
                accion={accion}
                onSeleccionar={setCuota}
                onVistaPrevia={verVistaPrevia}
                onConfirmar={confirmarAplazamiento}
                onCambiar={() => setPreview(null)}
                onCancelar={() => irA('inicio')}
              />
            )}
            {pantalla === 'ayuda' && <Ayuda explicacion={prestamo.explicacion} />}
          </>
        )}
        {mostrarDemo && (
          <PanelDemo
            activo={alertaActiva}
            alertaCargando={alertaCargando}
            accion={accion}
            onCrear={crearDemo}
            onAlerta={cambiarAlerta}
            onConsultarAlerta={consultarAlerta}
          />
        )}
      </main>
      {listo && (
        <nav className="bottom-nav" aria-label="Navegación principal">
          {navegacion.map(({ pantalla: destino, nombre, Icono }) => (
            <button
              key={destino}
              className="nav-button"
              aria-current={pestanaActiva === destino ? 'page' : undefined}
              disabled={bloqueado}
              onClick={() => irA(destino)}
            >
              <Icono size={21} aria-hidden="true" />
              {nombre}
            </button>
          ))}
        </nav>
      )}
    </div>
  )
}
