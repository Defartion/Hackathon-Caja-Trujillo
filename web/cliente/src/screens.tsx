import { useEffect, useRef, useState } from 'react'
import {
  CalendarDays, CalendarPlus, Check, CheckCircle2, ChevronDown, ChevronRight,
  Circle, CircleDot, CreditCard, LogOut, Repeat, TriangleAlert, X,
} from 'lucide-react'
import type { Cuota, Prestamo, Temporada, VistaPrevia } from './api'
import MenuExportar from './MenuExportar'
import type { Documento } from './exportar'
import { SelectorTema } from './apariencia'
import { cerrarSesion, iniciales, perfilSesion, usuarioSesion, type Perfil } from './sesion'

const meses: Record<string, string> = {
  ene: 'Enero', feb: 'Febrero', mar: 'Marzo', abr: 'Abril', may: 'Mayo', jun: 'Junio',
  jul: 'Julio', ago: 'Agosto', set: 'Septiembre', sep: 'Septiembre', oct: 'Octubre',
  nov: 'Noviembre', dic: 'Diciembre',
}

const moneda = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
export const soles = (monto: number) => `S/ ${moneda.format(monto)}`
const solesRedondo = (monto: number) => `S/ ${Math.round(monto).toLocaleString('en-US')}`
export const mesCompleto = (mes: string) => meses[mes.toLowerCase()] ?? mes
const porcentaje = (fraccion: number) => `${(fraccion * 100).toFixed(2)}%`
const nombreTemporada: Record<Temporada, string> = {
  alta: 'Temporada alta',
  baja: 'Temporada baja',
  normal: 'Temporada regular',
}
const explicacionTemporada: Record<Temporada, string> = {
  alta: 'Es un mes de más ventas para tu negocio, por eso esta cuota es más alta.',
  baja: 'Es un mes de menos ventas para tu negocio, por eso esta cuota es más baja.',
  normal: 'Es un mes de ventas regulares, con una cuota intermedia.',
}
const estados = {
  pagada: { nombre: 'Pagada', Icono: Check },
  proxima: { nombre: 'Próxima', Icono: CircleDot },
  pendiente: { nombre: 'Pendiente', Icono: Circle },
}
export const nombreProducto: Record<string, string> = {
  fija: 'Crédito de cuota fija',
  aplazamiento: 'Crédito con opción de aplazar',
  estacional: 'Crédito con cuotas por temporada',
}

// ---------- Fechas (las fechas de la API son AAAA-MM-DD, sin hora: se leen como fecha local)

function leerFecha(iso: string | null | undefined): Date | null {
  const m = iso ? /^(\d{4})-(\d{2})-(\d{2})/.exec(iso) : null
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null
}
const largo = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const medio = new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'long', year: 'numeric' })
const MES_CORTO = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic']
const fechaLarga = (iso: string | null) => {
  const d = leerFecha(iso)
  return d ? largo.format(d).replace(',', '') : '—'
}
const fechaMedia = (iso: string | null) => {
  const d = leerFecha(iso)
  return d ? medio.format(d) : '—'
}
const fechaCorta = (iso: string | null) => {
  const d = leerFecha(iso)
  return d ? `${d.getDate()} ${MES_CORTO[d.getMonth()]}` : '—'
}
function diasHasta(iso: string | null): number | null {
  const d = leerFecha(iso)
  if (!d) return null
  const hoy = new Date()
  return Math.round((d.getTime() - new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()).getTime()) / 86_400_000)
}
function plazoTexto(dias: number | null): string {
  if (dias === null) return ''
  if (dias === 0) return 'vence hoy'
  if (dias === 1) return 'vence mañana'
  if (dias > 1) return `faltan ${dias} días`
  return dias === -1 ? 'venció ayer' : `venció hace ${-dias} días`
}

function TemporadaBadge({ temporada }: { temporada: Temporada }) {
  return <span className={`season season--${temporada}`}>{nombreTemporada[temporada]}</span>
}

/** Las próximas cuotas como barras: se ve de un vistazo que el monto sigue la temporada del negocio. */
function RitmoCuotas({ cronograma }: { cronograma: Cuota[] }) {
  const proximas = cronograma.filter(item => item.estado !== 'pagada').slice(0, 12)
  if (proximas.length < 2) return null
  const mayor = Math.max(...proximas.map(item => item.cuota), 1)
  const iguales = proximas.every(item => Math.abs(item.cuota - proximas[0].cuota) < 1)
  return (
    <div className="due-card__ritmo">
      <div className="due-card__ritmo-barras" aria-hidden="true">
        {proximas.map((item, i) => (
          <span
            key={item.numero}
            className={i === 0 ? 'actual' : undefined}
            style={{ '--h': Math.max(item.cuota / mayor, 0.08), '--i': i } as React.CSSProperties}
          />
        ))}
      </div>
      <p>{iguales
        ? `Tus próximas ${proximas.length} cuotas son del mismo monto.`
        : `Tus próximas ${proximas.length} cuotas suben y bajan con tu temporada.`}</p>
    </div>
  )
}

/** Fila tocable de una cuota (inicio y pago): mes, vencimiento y monto. */
function FilaCuota({ cuota, onAbrir }: { cuota: Cuota; onAbrir: (numero: number) => void }) {
  return (
    <li>
      <button type="button" className="mini-row" onClick={() => onAbrir(cuota.numero)}>
        <span className="mini-row__fecha" aria-hidden="true">
          <b>{leerFecha(cuota.fecha)?.getDate() ?? ''}</b>
          <span>{MES_CORTO[(leerFecha(cuota.fecha)?.getMonth() ?? 0)]}</span>
        </span>
        <span className="mini-row__texto">
          <strong>{mesCompleto(cuota.mes)}</strong>
          <span>Cuota {cuota.numero}</span>
        </span>
        <span className="mini-row__monto">
          <strong>{soles(cuota.cuota)}</strong>
          <TemporadaBadge temporada={cuota.temporada} />
        </span>
        <ChevronRight className="mini-row__flecha" size={18} aria-hidden="true" />
      </button>
    </li>
  )
}

interface InicioProps {
  prestamo: Prestamo
  bloqueado: boolean
  accion: string | null
  onCronograma: () => void
  onPagar: () => void
  onAplazar: () => void
  onAlivio: () => void
  onDetalle: (numero: number) => void
}

// Fase 4 (FAQ del NEG-01): aplazar cuotas o pedir alivio de El Niño en un crédito vigente es reprogramación,
// fuera del alcance del reto. Se oculta sin borrar el código; El Niño se considera al diseñar el plan.
export const MOSTRAR_CREDITO_VIGENTE = false

export function Inicio({
  prestamo, bloqueado, accion, onCronograma, onPagar, onAplazar, onAlivio, onDetalle,
}: InicioProps) {
  const cuota = prestamo.proximaCuota
  const nombre = prestamo.nombre?.trim().split(/\s+/)[0]
  const activo = prestamo.estado === 'Active'
  const resumen = prestamo.resumen
  const alerta = MOSTRAR_CREDITO_VIGENTE && prestamo.elNino.activo && prestamo.clausulaElNino && cuota
  const puedeAplazar = MOSTRAR_CREDITO_VIGENTE && activo && prestamo.aplazamientosRestantes > 0
    && prestamo.cronograma.some(item => item.estado !== 'pagada' && item.numero < prestamo.totalCuotas)
  const siguientes = prestamo.cronograma.filter(item => item.estado === 'pendiente').slice(0, 3)
  const dias = cuota ? diasHasta(cuota.fecha) : null
  const avance = resumen.totalAPagar > 0 ? Math.min(resumen.totalPagado / resumen.totalAPagar, 1) : 0

  return (
    <>
      <div className="welcome">
        <h1>{nombre ? `Hola, ${nombre}` : 'Hola, qué gusto verte'}</h1>
        <p>{nombreProducto[prestamo.producto] ?? 'Tu crédito Thinku'}</p>
      </div>
      {alerta && (
        <section className="alert-card" aria-label="Alerta El Niño">
          <TriangleAlert aria-hidden="true" size={21} />
          <div>
            <h2>Alerta El Niño activa</h2>
            <p>{prestamo.elNino.puedeAplicar
              ? 'Puedes pagar solo la cuota mínima este mes.'
              : 'Revisa tu próxima cuota y el alivio disponible en tu crédito.'}</p>
            {prestamo.elNino.puedeAplicar && (
              <button className="button button--small" onClick={onAlivio} disabled={bloqueado}>
                {accion === 'alivio' ? 'Aplicando alivio…' : 'Usar alivio'}
              </button>
            )}
          </div>
        </section>
      )}
      {cuota ? (
        <section className="due-card" aria-label="Próxima cuota">
          <div className="due-card__heading">
            <span><CalendarDays size={18} aria-hidden="true" /> Próxima cuota</span>
            <span className="due-card__number">Cuota {cuota.numero} de {prestamo.totalCuotas}</span>
          </div>
          <p className="due-card__amount">{soles(cuota.monto)}</p>
          <p className="due-card__vence">
            Vence el {fechaMedia(cuota.fecha)}{dias !== null && <span>{plazoTexto(dias)}</span>}
          </p>
          <RitmoCuotas cronograma={prestamo.cronograma} />
          <div className="due-card__footer">
            <TemporadaBadge temporada={cuota.temporada} />
            <button type="button" className="due-card__detalle" onClick={() => onDetalle(cuota.numero)}>
              Ver detalle<ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>
        </section>
      ) : (
        <section className="surface completed-card">
          <CheckCircle2 size={24} aria-hidden="true" />
          <div>
            <h2>{prestamo.totalCuotas > 0 ? '¡Terminaste de pagar tu crédito!' : 'Aún no hay cuotas por pagar'}</h2>
            <p>{prestamo.totalCuotas > 0 ? 'Puedes consultar tus pagos en el cronograma.' : 'Consulta tu crédito con tu asesor.'}</p>
          </div>
        </section>
      )}
      {prestamo.totalCuotas > 0 && (
        <section className="surface progress-card" aria-label="Avance de tu crédito">
          <div className="progress-card__heading">
            <h2>Avance de tu crédito</h2>
            <span>{prestamo.cuotasPagadas} de {prestamo.totalCuotas} cuotas</span>
          </div>
          <progress
            aria-label={`${prestamo.cuotasPagadas} de ${prestamo.totalCuotas} cuotas pagadas`}
            value={prestamo.cuotasPagadas}
            max={prestamo.totalCuotas}
          />
          <dl className="progress-card__montos">
            <div>
              <dt>Ya pagaste</dt>
              <dd>{soles(resumen.totalPagado)}</dd>
            </div>
            <div>
              <dt>Te falta pagar</dt>
              <dd>{soles(resumen.porPagar)}</dd>
            </div>
          </dl>
          <p className="progress-card__nota">Llevas el {Math.round(avance * 100)}% del total de tu crédito.</p>
        </section>
      )}
      {siguientes.length > 0 && (
        <section className="home-block" aria-labelledby="lo-que-sigue">
          <div className="home-block__heading">
            <h2 id="lo-que-sigue">Lo que sigue</h2>
            <button type="button" className="link-button" onClick={onCronograma} disabled={bloqueado}>Ver todo</button>
          </div>
          <ul className="mini-list">
            {siguientes.map(item => <FilaCuota key={item.numero} cuota={item} onAbrir={onDetalle} />)}
          </ul>
        </section>
      )}
      {prestamo.totalCuotas > 0 && (
        <section className="home-block" aria-labelledby="en-cifras">
          <h2 id="en-cifras">Tu crédito en cifras</h2>
          <dl className="stats">
            <div className="stat">
              <dt>Saldo de capital</dt>
              <dd>{soles(resumen.saldoCapital)}</dd>
              <span>de {solesRedondo(prestamo.principal)} prestados</span>
            </div>
            <div className="stat">
              <dt>Intereses del crédito</dt>
              <dd>{soles(resumen.interesesTotales)}</dd>
              <span>TEA {porcentaje(prestamo.tea)}</span>
            </div>
            {resumen.cuotaMayor && (
              <div className="stat">
                <dt>Tu cuota más alta</dt>
                <dd>{soles(resumen.cuotaMayor.monto)}</dd>
                <span>en {mesCompleto(resumen.cuotaMayor.mes).toLowerCase()}</span>
              </div>
            )}
            {resumen.cuotaMenor && (
              <div className="stat">
                <dt>Tu cuota más baja</dt>
                <dd>{soles(resumen.cuotaMenor.monto)}</dd>
                <span>en {mesCompleto(resumen.cuotaMenor.mes).toLowerCase()}</span>
              </div>
            )}
          </dl>
        </section>
      )}
      <div className="home-actions">
        {cuota && activo && (
          <button className="button button--primary" disabled={bloqueado} onClick={onPagar}>
            <CreditCard size={20} aria-hidden="true" />
            Pagar una cuota (demo)
          </button>
        )}
        <button className="button" disabled={bloqueado} onClick={onCronograma}>
          <CalendarDays size={20} aria-hidden="true" />
          Ver mi cronograma
        </button>
        {puedeAplazar && (
          <button className="button" disabled={bloqueado} onClick={onAplazar}>
            <CalendarPlus size={20} aria-hidden="true" />
            Necesito aplazar una cuota
          </button>
        )}
      </div>
    </>
  )
}

/** Cronograma completo para exportar (PDF, Excel, CSV, JSON o texto). */
function documentoCronograma(prestamo: Prestamo): Documento {
  const estado = { pagada: 'Pagada', proxima: 'Próxima', pendiente: 'Pendiente' }
  return {
    archivo: `cronograma-credito-${prestamo.loanId}`,
    titulo: `Mi cronograma, crédito N° ${prestamo.loanId}`,
    subtitulo: [prestamo.nombre, nombreProducto[prestamo.producto] ?? prestamo.producto].filter(Boolean).join(', '),
    resumen: [
      { etiqueta: 'Monto prestado', valor: prestamo.principal, tipo: 'moneda' },
      { etiqueta: 'Tasa (TEA)', valor: prestamo.tea, tipo: 'porcentaje' },
      { etiqueta: 'Plazo (cuotas)', valor: prestamo.totalCuotas, tipo: 'entero' },
      { etiqueta: 'Desembolso', valor: prestamo.fechaDesembolso, tipo: 'fecha' },
      { etiqueta: 'Cuotas pagadas', valor: prestamo.cuotasPagadas, tipo: 'entero' },
      { etiqueta: 'Ya pagaste', valor: prestamo.resumen.totalPagado, tipo: 'moneda' },
      { etiqueta: 'Te falta pagar', valor: prestamo.resumen.porPagar, tipo: 'moneda' },
      { etiqueta: 'Saldo de capital', valor: prestamo.resumen.saldoCapital, tipo: 'moneda' },
    ],
    tablas: [{
      titulo: 'Cronograma',
      columnas: [
        { clave: 'numero', titulo: 'N°', tipo: 'entero' },
        { clave: 'mes', titulo: 'Mes' },
        { clave: 'fecha', titulo: 'Vence', tipo: 'fecha' },
        { clave: 'cuota', titulo: 'Cuota', tipo: 'moneda' },
        { clave: 'capital', titulo: 'Capital', tipo: 'moneda' },
        { clave: 'interes', titulo: 'Interés', tipo: 'moneda' },
        { clave: 'saldo', titulo: 'Saldo', tipo: 'moneda' },
        { clave: 'temporada', titulo: 'Temporada' },
        { clave: 'estado', titulo: 'Estado' },
        { clave: 'fechaPago', titulo: 'Pagada el', tipo: 'fecha' },
      ],
      filas: prestamo.cronograma.map(c => ({
        ...c,
        mes: mesCompleto(c.mes),
        temporada: nombreTemporada[c.temporada],
        estado: estado[c.estado],
      })),
    }],
    notas: ['Las cuotas siguen la temporada de tu negocio: más altas en los meses de más ventas y más bajas en los de menos ventas.'],
  }
}

export function Cronograma({
  prestamo, actualizado, onInicio, bloqueado, onDetalle,
}: {
  prestamo: Prestamo
  actualizado: boolean
  onInicio: () => void
  bloqueado: boolean
  onDetalle: (numero: number) => void
}) {
  return (
    <>
      <div className="screen-heading">
        <h1>{actualizado ? 'Cronograma actualizado' : 'Mi cronograma'}</h1>
        {prestamo.cronograma.length > 0 && (
          <MenuExportar documento={() => documentoCronograma(prestamo)} etiqueta="Descargar" />
        )}
      </div>
      {actualizado ? (
        <div className="feedback feedback--success" role="status">
          <CheckCircle2 aria-hidden="true" size={21} />
          <span>Aplazamiento confirmado. Estos son tus nuevos montos.</span>
        </div>
      ) : (
        <p className="screen-intro">{prestamo.producto === 'estacional'
          ? 'Tus cuotas son más altas en tus meses de más ventas y más bajas en los de menos ventas. Toca una cuota para ver su detalle.'
          : 'Revisa lo que ya pagaste y las cuotas que tienes por delante. Toca una cuota para ver su detalle.'}</p>
      )}
      {prestamo.cronograma.length ? (
        <ol className="schedule" aria-label="Cuotas del crédito">
          {prestamo.cronograma.map(cuota => {
            const { nombre, Icono } = estados[cuota.estado]
            return (
              <li
                className={`schedule-row schedule-row--${cuota.estado}`}
                key={cuota.numero}
                aria-current={cuota.estado === 'proxima' ? 'step' : undefined}
              >
                <button type="button" className="schedule-row__boton" onClick={() => onDetalle(cuota.numero)}>
                  <span className={`schedule-row__status schedule-row__status--${cuota.estado}`}>
                    <Icono aria-hidden="true" size={19} />
                  </span>
                  <span className="schedule-row__main">
                    <strong>{mesCompleto(cuota.mes)}</strong>
                    <span className="schedule-row__label">Cuota {cuota.numero} · {nombre}</span>
                    <span className="schedule-row__fecha">
                      {cuota.estado === 'pagada' && cuota.fechaPago
                        ? `Pagada el ${fechaCorta(cuota.fechaPago)}`
                        : `Vence el ${fechaCorta(cuota.fecha)}`}
                    </span>
                  </span>
                  <span className="schedule-row__value">
                    <strong>{soles(cuota.cuota)}</strong>
                    <TemporadaBadge temporada={cuota.temporada} />
                  </span>
                  <ChevronRight className="schedule-row__flecha" size={18} aria-hidden="true" />
                </button>
              </li>
            )
          })}
        </ol>
      ) : <p>El cronograma aparecerá cuando haya cuotas disponibles.</p>}
      {actualizado && (
        <button className="button" disabled={bloqueado} onClick={onInicio}>Volver al inicio</button>
      )}
    </>
  )
}

/** Hoja con el detalle de una cuota: vencimiento, desglose, temporada y comparación con una cuota fija. */
export function DetalleCuota({
  prestamo, numero, puedePagar, onCerrar, onPagar,
}: {
  prestamo: Prestamo
  numero: number | null
  puedePagar: boolean
  onCerrar: () => void
  onPagar: (numero: number) => void
}) {
  const hoja = useRef<HTMLDialogElement>(null)
  const cuota = numero === null ? undefined : prestamo.cronograma.find(item => item.numero === numero)

  useEffect(() => {
    const dialogo = hoja.current
    if (!dialogo) return
    if (cuota && !dialogo.open) dialogo.showModal()
    if (!cuota && dialogo.open) dialogo.close()
  }, [cuota])

  useEffect(() => {
    const dialogo = hoja.current
    if (!dialogo) return
    dialogo.addEventListener('close', onCerrar)
    return () => dialogo.removeEventListener('close', onCerrar)
  }, [onCerrar])

  const total = cuota ? cuota.capital + cuota.interes : 0
  const parteCapital = cuota && total > 0 ? (cuota.capital / total) * 100 : 0
  const diferencia = cuota ? cuota.cuota - prestamo.cuotaFijaReferencia : 0
  const dias = cuota ? diasHasta(cuota.fecha) : null

  return (
    <dialog
      ref={hoja}
      className="sheet"
      aria-labelledby="detalle-cuota-titulo"
      onClick={event => { if (event.target === event.currentTarget) event.currentTarget.close() }}
    >
      {cuota && (
        <div className="sheet__cuerpo">
          <div className="sheet__asa" aria-hidden="true" />
          <div className="sheet__cabecera">
            <div>
              <h2 id="detalle-cuota-titulo">Cuota {cuota.numero} de {prestamo.totalCuotas}</h2>
              <p>{mesCompleto(cuota.mes)} {leerFecha(cuota.fecha)?.getFullYear()}</p>
            </div>
            <button type="button" className="sheet__cerrar" aria-label="Cerrar detalle" onClick={() => hoja.current?.close()}>
              <X size={20} aria-hidden="true" />
            </button>
          </div>
          <p className="sheet__monto">{soles(cuota.cuota)}</p>
          <p className={`sheet__estado sheet__estado--${cuota.estado}`}>
            {cuota.estado === 'pagada'
              ? <>Pagada el {fechaLarga(cuota.fechaPago)}</>
              : <>Vence el {fechaLarga(cuota.fecha)}{dias !== null && <span> · {plazoTexto(dias)}</span>}</>}
          </p>

          <div className="sheet__barra" role="img"
            aria-label={`De esta cuota, ${soles(cuota.capital)} van a capital y ${soles(cuota.interes)} a intereses.`}>
            <span className="sheet__barra-capital" style={{ inlineSize: `${parteCapital}%` }} />
            <span className="sheet__barra-interes" />
          </div>
          <dl className="sheet__datos">
            <div>
              <dt><i className="punto punto--capital" aria-hidden="true" />Capital</dt>
              <dd>{soles(cuota.capital)}</dd>
            </div>
            <div>
              <dt><i className="punto punto--interes" aria-hidden="true" />Intereses</dt>
              <dd>{soles(cuota.interes)}</dd>
            </div>
            <div>
              <dt>Saldo después de esta cuota</dt>
              <dd>{soles(Math.max(cuota.saldo, 0))}</dd>
            </div>
            <div>
              <dt>Frente a una cuota fija de <span className="sin-corte">{soles(prestamo.cuotaFijaReferencia)}</span></dt>
              <dd>{Math.abs(diferencia) < 1 ? 'Igual' : `${soles(Math.abs(diferencia))} ${diferencia > 0 ? 'más' : 'menos'}`}</dd>
            </div>
          </dl>
          <div className="sheet__temporada">
            <TemporadaBadge temporada={cuota.temporada} />
            <p>{explicacionTemporada[cuota.temporada]}</p>
          </div>
          <div className="sheet__acciones">
            {puedePagar && cuota.estado !== 'pagada' && (
              <button type="button" className="button button--primary" onClick={() => onPagar(cuota.numero)}>
                <CreditCard size={20} aria-hidden="true" />
                Pagar esta cuota (demo)
              </button>
            )}
            <button type="button" className="button button--quiet" onClick={() => hoja.current?.close()}>Cerrar</button>
          </div>
        </div>
      )}
    </dialog>
  )
}

/** Elegir qué cuota pagar: la próxima viene marcada, pero se puede adelantar cualquier otra. */
export function PagarCuota({
  prestamo, inicial, bloqueado, accion, onPagar, onCancelar, onDetalle,
}: {
  prestamo: Prestamo
  inicial: number | null
  bloqueado: boolean
  accion: string | null
  onPagar: (numero: number) => void
  onCancelar: () => void
  onDetalle: (numero: number) => void
}) {
  const pendientes = prestamo.cronograma.filter(item => item.estado !== 'pagada')
  const proxima = pendientes.find(item => item.estado === 'proxima') ?? pendientes[0]
  const [elegida, setElegida] = useState<number | null>(
    pendientes.some(item => item.numero === inicial) ? inicial : proxima?.numero ?? null,
  )
  const cuota = pendientes.find(item => item.numero === elegida)
  const adelanta = cuota && proxima && cuota.numero !== proxima.numero

  return (
    <>
      <h1>Pagar una cuota</h1>
      <p className="screen-intro">
        Elige la cuota que vas a pagar. Si adelantas una, la próxima sigue siendo la del mes más cercano.
      </p>
      {pendientes.length === 0 ? (
        <section className="surface completed-card">
          <CheckCircle2 size={24} aria-hidden="true" />
          <div><h2>No tienes cuotas por pagar</h2></div>
        </section>
      ) : (
        <form onSubmit={event => { event.preventDefault(); if (cuota) onPagar(cuota.numero) }}>
          <fieldset className="pay-options" disabled={bloqueado}>
            <legend>Cuotas por pagar</legend>
            {pendientes.map(item => (
              <label key={item.numero} className="pay-option">
                <input
                  type="radio"
                  name="cuota-a-pagar"
                  value={item.numero}
                  checked={elegida === item.numero}
                  onChange={() => setElegida(item.numero)}
                />
                <span className="pay-option__marca" aria-hidden="true" />
                <span className="pay-option__texto">
                  <strong>{mesCompleto(item.mes)}</strong>
                  <span>Cuota {item.numero} · vence el {fechaCorta(item.fecha)}</span>
                </span>
                <span className="pay-option__monto">
                  <strong>{soles(item.cuota)}</strong>
                  {item.estado === 'proxima' && <span className="pay-option__tag">Próxima</span>}
                </span>
              </label>
            ))}
          </fieldset>
          {cuota && (
            <section className="pay-summary" aria-live="polite" aria-label="Pago elegido">
              <span>Vas a pagar</span>
              <strong>{soles(cuota.cuota)}</strong>
              <span>Cuota {cuota.numero} de {mesCompleto(cuota.mes).toLowerCase()}, vence el {fechaMedia(cuota.fecha)}</span>
              {adelanta && (
                <p className="pay-summary__nota">
                  Estás adelantando esta cuota. Tu cuota de {mesCompleto(proxima.mes).toLowerCase()} sigue pendiente.
                </p>
              )}
              <button type="button" className="link-button" onClick={() => onDetalle(cuota.numero)}>
                Ver el detalle de esta cuota
              </button>
            </section>
          )}
          <div className="home-actions">
            <button className="button button--primary" type="submit" disabled={bloqueado || !cuota}>
              <CreditCard size={20} aria-hidden="true" />
              {accion === 'pago' ? 'Registrando pago…' : cuota ? `Pagar ${soles(cuota.cuota)} (demo)` : 'Elige una cuota'}
            </button>
            <button className="button button--quiet" type="button" onClick={onCancelar} disabled={bloqueado}>Cancelar</button>
          </div>
        </form>
      )}
    </>
  )
}

/** Perfil: quién entró, el crédito que consulta, el tema de la app y la sesión. */
export function PerfilCliente({
  prestamo, onInicio,
}: {
  prestamo: Prestamo | null
  onInicio?: () => void
}) {
  const usuario = usuarioSesion('cliente')
  const [perfil, setPerfil] = useState<Perfil | null>(null)
  const enDespliegue = import.meta.env.BASE_URL !== '/'

  useEffect(() => {
    const control = new AbortController()
    perfilSesion('cliente', control.signal)
      .then(datos => { if (!control.signal.aborted) setPerfil(datos) })
      .catch(() => { if (!control.signal.aborted) setPerfil({ sesion: usuario !== null }) })
    return () => control.abort()
  }, [usuario !== null])

  const nombre = perfil?.nombre ?? usuario?.nombre ?? prestamo?.nombre ?? null
  const sesion = usuario !== null
  const metodo = perfil?.metodo ?? (usuario?.nombre ? 'cuenta' : 'pin')

  return (
    <>
      <div className="profile-head">
        <span className="profile-head__avatar" aria-hidden="true">{nombre ? iniciales(nombre) : '•'}</span>
        <div>
          <h1>{nombre ?? 'Mi perfil'}</h1>
          <p>{!sesion ? 'Modo demo, sin iniciar sesión' : metodo === 'cuenta' ? 'Cliente con cuenta Thinku' : 'Entraste con el PIN de cliente'}</p>
        </div>
      </div>

      <section className="surface profile-card" aria-labelledby="perfil-datos">
        <h2 id="perfil-datos">Tus datos</h2>
        <dl className="kv">
          <div><dt>Nombre</dt><dd>{nombre ?? '—'}</dd></div>
          {perfil?.correo && <div><dt>Correo</dt><dd>{perfil.correo}</dd></div>}
          {perfil?.creado && <div><dt>Cliente desde</dt><dd>{fechaMedia(perfil.creado)}</dd></div>}
          <div>
            <dt>Forma de ingreso</dt>
            <dd>{!sesion ? 'Sin sesión (demo local)' : metodo === 'cuenta' ? 'Correo y contraseña' : 'PIN de cliente'}</dd>
          </div>
        </dl>
      </section>

      {prestamo && (
        <section className="surface profile-card" aria-labelledby="perfil-credito">
          <h2 id="perfil-credito">Tu crédito</h2>
          <dl className="kv">
            <div><dt>N° de crédito</dt><dd>{prestamo.loanId}</dd></div>
            {prestamo.nombre && <div><dt>Titular</dt><dd>{prestamo.nombre}</dd></div>}
            <div><dt>Producto</dt><dd>{nombreProducto[prestamo.producto] ?? prestamo.producto}</dd></div>
            <div><dt>Monto prestado</dt><dd>{soles(prestamo.principal)}</dd></div>
            <div><dt>Tasa (TEA)</dt><dd>{porcentaje(prestamo.tea)}</dd></div>
            <div><dt>Plazo</dt><dd>{prestamo.totalCuotas} meses</dd></div>
            {prestamo.fechaDesembolso && <div><dt>Desembolso</dt><dd>{fechaMedia(prestamo.fechaDesembolso)}</dd></div>}
            <div><dt>Estado</dt><dd>{prestamo.estado === 'Active' ? 'Vigente' : prestamo.estado}</dd></div>
          </dl>
        </section>
      )}

      <section className="surface profile-card" aria-labelledby="perfil-apariencia">
        <h2 id="perfil-apariencia">Apariencia</h2>
        <p className="profile-card__nota">Automático sigue el tema de tu celular o computadora.</p>
        <SelectorTema />
      </section>

      {(sesion || enDespliegue || onInicio) && (
        <div className="home-actions profile-actions">
          {enDespliegue && (
            <a className="button" href="/"><Repeat size={20} aria-hidden="true" /> Cambiar de rol</a>
          )}
          {sesion && (
            <button type="button" className="button" onClick={() => cerrarSesion('cliente')}>
              <LogOut size={20} aria-hidden="true" /> Cerrar sesión
            </button>
          )}
          {onInicio && <button type="button" className="button button--quiet" onClick={onInicio}>Volver al inicio</button>}
        </div>
      )}
    </>
  )
}

interface AplazamientoProps {
  cronograma: Cuota[]
  restantes: number
  seleccionada: number | null
  preview: VistaPrevia | null
  bloqueado: boolean
  accion: string | null
  onSeleccionar: (numero: number) => void
  onVistaPrevia: () => void
  onConfirmar: () => void
  onCambiar: () => void
  onCancelar: () => void
}

export function Aplazamiento({
  cronograma, restantes, seleccionada, preview, bloqueado, accion,
  onSeleccionar, onVistaPrevia, onConfirmar, onCambiar, onCancelar,
}: AplazamientoProps) {
  const opciones = cronograma.filter(cuota => cuota.estado !== 'pagada' && cuota.numero < cronograma.length)
  const cuota = opciones.find(item => item.numero === seleccionada)
  const saldo = Math.max(restantes - 1, 0)

  return (
    <>
      <h1>Aplazar una cuota</h1>
      <p className="screen-intro">{preview && cuota
        ? `Revisa cómo cambia tu cuota de ${mesCompleto(cuota.mes).toLowerCase()}.`
        : 'Elige una cuota para conocer el costo antes de confirmar.'}</p>
      {preview ? (
        <>
          <section className="surface defer-summary" aria-label="Detalle del aplazamiento">
            <span className="defer-summary__label">Pagarías esta cuota</span>
            <strong className="defer-summary__amount">{soles(preview.nuevaCuota)}</strong>
            <p>En lugar de {soles(preview.cuotaActual)}</p>
            <dl>
              <div>
                <dt>Aumento por cada cuota siguiente</dt>
                <dd>{soles(preview.incrementoCuotasSiguientes)}</dd>
              </div>
              <div>
                <dt>Costo adicional total</dt>
                <dd>{soles(preview.costoAdicionalTotal)}</dd>
              </div>
            </dl>
          </section>
          <p className="defer-note">Te quedarían <strong>{saldo} {saldo === 1 ? 'aplazamiento' : 'aplazamientos'}</strong>.</p>
          <div className="home-actions">
            <button className="button button--primary" onClick={onConfirmar} disabled={bloqueado}>
              {accion === 'confirmar' ? 'Confirmando…' : 'Confirmar aplazamiento'}
            </button>
            <button className="button" onClick={onCambiar} disabled={bloqueado}>Elegir otra cuota</button>
            <button className="button button--quiet" onClick={onCancelar} disabled={bloqueado}>Cancelar</button>
          </div>
        </>
      ) : (
        <form onSubmit={event => { event.preventDefault(); onVistaPrevia() }}>
          <label className="select-label" htmlFor="cuota">Cuota que quieres aplazar</label>
          <div className="select-wrap">
            <select
              id="cuota"
              value={seleccionada ?? ''}
              onChange={event => onSeleccionar(Number(event.target.value))}
              disabled={bloqueado || opciones.length === 0}
              required
            >
              <option value="" disabled>Elige una cuota</option>
              {opciones.map(item => (
                <option key={item.numero} value={item.numero}>
                  {mesCompleto(item.mes)} · {soles(item.cuota)} (cuota {item.numero})
                </option>
              ))}
            </select>
            <ChevronDown aria-hidden="true" size={19} />
          </div>
          <p className="defer-note">Tienes <strong>{restantes} {restantes === 1 ? 'aplazamiento disponible' : 'aplazamientos disponibles'}</strong>.</p>
          <div className="home-actions">
            <button className="button button--primary" disabled={bloqueado || !cuota || restantes < 1}>
              {accion === 'preview' ? 'Calculando el costo…' : 'Ver costo del aplazamiento'}
            </button>
            <button className="button button--quiet" type="button" onClick={onCancelar} disabled={bloqueado}>Cancelar</button>
          </div>
        </form>
      )}
    </>
  )
}

const preguntasFrecuentes = [
  {
    pregunta: '¿Por qué mis cuotas cambian según el mes?',
    respuesta: 'Tus cuotas siguen el ritmo de tu negocio: son más bajas en los meses flojos y más altas cuando vendes más. Nunca pasan de lo que puedes pagar cada mes.',
  },
  {
    pregunta: '¿Puedo pagar una cuota por adelantado?',
    respuesta: 'Sí. En "Pagar una cuota" elige la que quieras. Tu próxima cuota sigue siendo la del mes más cercano hasta que la pagues.',
  },
  {
    pregunta: '¿Mi cronograma puede cambiar después?',
    respuesta: 'No. Tu plan se definió antes del desembolso y se mantiene igual hasta el final. Lo que ves en "Cronograma" es lo que pagarás.',
  },
  {
    pregunta: '¿Qué pasa si hay El Niño?',
    respuesta: 'Tu plan ya se revisó pensando en un año El Niño y otros meses difíciles. Si aun así tienes problemas para pagar, habla con tu asesor.',
  },
  {
    pregunta: '¿Cuánto me cuesta?',
    respuesta: 'Pagas intereses según la tasa (TEA) y los seguros de tu crédito. Toca una cuota en "Cronograma" para ver cuánto va a capital y cuánto a intereses.',
  },
]

export function Ayuda({ explicacion }: { explicacion: string }) {
  const explicacionCliente = explicacion
    .replace('Puede pagar solo la cuota mínima', 'Puedes pagar solo la cuota mínima')
    .replace('si mantiene sus pagos al día', 'si mantienes tus pagos al día')
    .replace('Incluye alivio automático si el ENFEN declara alerta de El Niño costero.', '')
    .replace('Cronograma diseñado contra el escenario conservador (p25) de ingresos.',
      'Las cuotas se calcularon pensando en meses de menores ingresos.')

  return (
    <>
      <h1>Ayuda con mi crédito</h1>
      {explicacion && (
        <section className="surface explanation">
          <h2>Sobre tu crédito</h2>
          <p>{explicacionCliente}</p>
        </section>
      )}
      <section className="faqs">
        <h2>Preguntas frecuentes</h2>
        {preguntasFrecuentes.map(({ pregunta, respuesta }) => (
          <details key={pregunta}>
            <summary>{pregunta}<ChevronDown aria-hidden="true" size={18} /></summary>
            <p>{respuesta}</p>
          </details>
        ))}
      </section>
    </>
  )
}
