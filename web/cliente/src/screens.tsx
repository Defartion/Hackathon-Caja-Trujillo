import {
  CalendarDays, CalendarPlus, Check, CheckCircle2, ChevronDown,
  Circle, CircleDot, CreditCard, TriangleAlert,
} from 'lucide-react'
import type { Cuota, Prestamo, Temporada, VistaPrevia } from './api'

const meses: Record<string, string> = {
  ene: 'Enero', feb: 'Febrero', mar: 'Marzo', abr: 'Abril', may: 'Mayo', jun: 'Junio',
  jul: 'Julio', ago: 'Agosto', set: 'Septiembre', sep: 'Septiembre', oct: 'Octubre',
  nov: 'Noviembre', dic: 'Diciembre',
}

const moneda = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const soles = (monto: number) => `S/ ${moneda.format(monto)}`
const mesCompleto = (mes: string) => meses[mes.toLowerCase()] ?? mes
const nombreTemporada: Record<Temporada, string> = {
  alta: 'Temporada alta',
  baja: 'Temporada baja',
  normal: 'Temporada regular',
}
const estados = {
  pagada: { nombre: 'Pagada', Icono: Check },
  proxima: { nombre: 'Próxima', Icono: CircleDot },
  pendiente: { nombre: 'Pendiente', Icono: Circle },
}
const nombreProducto: Record<string, string> = {
  fija: 'Crédito de cuota fija',
  aplazamiento: 'Crédito con opción de aplazar',
  estacional: 'Crédito con cuotas por temporada',
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

interface InicioProps {
  prestamo: Prestamo
  bloqueado: boolean
  accion: string | null
  onCronograma: () => void
  onPagar: () => void
  onAplazar: () => void
  onAlivio: () => void
}

// Fase 4 (FAQ del NEG-01): aplazar cuotas o pedir alivio de El Niño en un crédito vigente es reprogramación,
// fuera del alcance del reto. Se oculta sin borrar el código; El Niño se considera al diseñar el plan.
export const MOSTRAR_CREDITO_VIGENTE = false

export function Inicio({
  prestamo, bloqueado, accion, onCronograma, onPagar, onAplazar, onAlivio,
}: InicioProps) {
  const cuota = prestamo.proximaCuota
  const nombre = prestamo.nombre?.trim().split(/\s+/)[0]
  const activo = prestamo.estado === 'Active'
  const alerta = MOSTRAR_CREDITO_VIGENTE && prestamo.elNino.activo && prestamo.clausulaElNino && cuota
  const puedeAplazar = MOSTRAR_CREDITO_VIGENTE && activo && prestamo.aplazamientosRestantes > 0
    && prestamo.cronograma.some(item => item.estado !== 'pagada' && item.numero < prestamo.totalCuotas)

  return (
    <>
      <div className="welcome">
        <h1>{nombre ? `Hola, ${nombre}` : 'Hola, qué gusto verte'}</h1>
        <p>{nombreProducto[prestamo.producto] ?? 'Tu crédito CuotaFlex'}</p>
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
          <RitmoCuotas cronograma={prestamo.cronograma} />
          <div className="due-card__footer">
            <span>{mesCompleto(cuota.mes)}</span>
            <TemporadaBadge temporada={cuota.temporada} />
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
            <span>{prestamo.cuotasPagadas} de {prestamo.totalCuotas}</span>
          </div>
          <progress
            aria-label={`${prestamo.cuotasPagadas} de ${prestamo.totalCuotas} cuotas pagadas`}
            value={prestamo.cuotasPagadas}
            max={prestamo.totalCuotas}
          />
        </section>
      )}
      <div className="home-actions">
        {cuota && activo && (
          <button className="button button--primary" disabled={bloqueado} onClick={onPagar}>
            <CreditCard size={20} aria-hidden="true" />
            {accion === 'pago' ? 'Registrando pago…' : 'Pagar cuota (demo)'}
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

export function Cronograma({
  prestamo, actualizado, onInicio, bloqueado,
}: {
  prestamo: Prestamo
  actualizado: boolean
  onInicio: () => void
  bloqueado: boolean
}) {
  return (
    <>
      <h1>{actualizado ? 'Cronograma actualizado' : 'Mi cronograma'}</h1>
      {actualizado ? (
        <div className="feedback feedback--success" role="status">
          <CheckCircle2 aria-hidden="true" size={21} />
          <span>Aplazamiento confirmado. Estos son tus nuevos montos.</span>
        </div>
      ) : (
        <p className="screen-intro">{prestamo.producto === 'estacional'
          ? 'Tus cuotas son más altas en tus meses de más ventas y más bajas en los de menos ventas.'
          : 'Revisa lo que ya pagaste y las cuotas que tienes por delante.'}</p>
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
                <span className={`schedule-row__status schedule-row__status--${cuota.estado}`}>
                  <Icono aria-hidden="true" size={19} />
                </span>
                <div>
                  <strong>{mesCompleto(cuota.mes)}</strong>
                  <span className="schedule-row__label">Cuota {cuota.numero} · {nombre}</span>
                </div>
                <div className="schedule-row__value">
                  <strong>{soles(cuota.cuota)}</strong>
                  <TemporadaBadge temporada={cuota.temporada} />
                </div>
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
    pregunta: '¿Mi cronograma puede cambiar después?',
    respuesta: 'No. Tu plan se definió antes del desembolso y se mantiene igual hasta el final. Lo que ves en "Cronograma" es lo que pagarás.',
  },
  {
    pregunta: '¿Qué pasa si hay El Niño?',
    respuesta: 'Tu plan ya se revisó pensando en un año El Niño y otros meses difíciles. Si aun así tienes problemas para pagar, habla con tu asesor.',
  },
  {
    pregunta: '¿Cuánto me cuesta?',
    respuesta: 'Pagas intereses según la tasa (TEA) y los seguros de tu crédito. En "Cronograma" ves cuánto pagas cada mes y cuánto va a capital e intereses.',
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
