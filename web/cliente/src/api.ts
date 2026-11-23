export type Temporada = 'alta' | 'baja' | 'normal'
export type EstadoCuota = 'pagada' | 'proxima' | 'pendiente'
export type ProductoDemo = 'estacional' | 'aplazamiento'

export interface Cuota {
  numero: number
  mes: string
  cuota: number
  estado: EstadoCuota
  temporada: Temporada
}

export interface Prestamo {
  loanId: number
  nombre?: string
  producto: string
  descripcion: string
  estado: string
  principal: number
  proximaCuota: { numero: number; mes: string; monto: number; temporada: Temporada } | null
  cuotasPagadas: number
  totalCuotas: number
  aplazamientosRestantes: number
  clausulaElNino: boolean
  elNino: { activo: boolean; alivioDisponible: number; puedeAplicar: boolean }
  cronograma: Cuota[]
  explicacion: string
}

export interface VistaPrevia {
  cuotaActual: number
  nuevaCuota: number
  incrementoCuotasSiguientes: number
  costoAdicionalTotal: number
  revision: string
}

export class ErrorApi extends Error {
  constructor(public readonly estado: number, message: string) {
    super(message)
  }
}

const baseUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

async function solicitar<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(`${baseUrl}/cliente${ruta}`, opciones)
  } catch (error) {
    if (opciones?.signal?.aborted) throw error
    throw new Error('No pudimos conectar con la app de pagos. Intenta de nuevo.')
  }

  if (!respuesta.ok) {
    const contenido = await respuesta.json().catch(() => null)
    let detalle = 'No pudimos completar la acción. Intenta de nuevo.'
    if (respuesta.status === 404) {
      detalle = 'No encontramos ese crédito. Puedes cargar otro o crear uno de demo.'
    } else if (respuesta.status < 500 && typeof contenido?.detail === 'string') {
      const texto: string = contenido.detail
      detalle = texto.charAt(0).toUpperCase() + texto.slice(1)
    }
    throw new ErrorApi(respuesta.status, detalle)
  }

  return respuesta.json()
}

function enviar<T>(ruta: string, cuerpo?: object): Promise<T> {
  return solicitar<T>(ruta, {
    method: 'POST',
    ...(cuerpo && {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cuerpo),
    }),
  })
}

export const api = {
  crearDemo: (producto: ProductoDemo) =>
    enviar<{ loanId: number }>(producto === 'aplazamiento' ? '/demo-seed?producto=aplazamiento' : '/demo-seed'),
  prestamo: (id: number, signal?: AbortSignal) =>
    solicitar<Prestamo>(`/prestamos/${id}`, { signal }),
  pagar: (id: number) => enviar(`/prestamos/${id}/pagar`),
  previsualizar: (id: number, installment: number) =>
    enviar<VistaPrevia>(`/prestamos/${id}/aplazamiento/preview`, { installment }),
  aplazar: (id: number, installment: number, revision: string) =>
    enviar(`/prestamos/${id}/aplazamiento`, { installment, revision }),
  estadoElNino: (signal?: AbortSignal) =>
    solicitar<{ activo: boolean }>('/el-nino', { signal }),
  cambiarAlerta: (activo: boolean) => enviar<{ activo: boolean }>('/el-nino', { activo }),
  usarAlivio: (id: number) => enviar(`/prestamos/${id}/alivio-el-nino`),
}

const clavePrestamo = 'cuotaflex.cliente.loanId'

export function prestamoEnUrl(): number | null {
  const url = new URLSearchParams(window.location.search)
  const idEnUrl = Number(url.get('loanId'))
  return Number.isSafeInteger(idEnUrl) && idEnUrl > 0 ? idEnUrl : null
}

export function leerPrestamo(): number | null {
  try {
    const guardado = Number(localStorage.getItem(clavePrestamo))
    return Number.isSafeInteger(guardado) && guardado > 0 ? guardado : null
  } catch {
    return null
  }
}

export function guardarPrestamo(id: number | null): void {
  try {
    if (id === null) localStorage.removeItem(clavePrestamo)
    else localStorage.setItem(clavePrestamo, String(id))
  } catch {
    // El crédito se puede consultar durante la sesión aunque el navegador bloquee el almacenamiento.
  }
}

export function quitarPrestamoDeUrl(): void {
  const url = new URL(window.location.href)
  if (!url.searchParams.has('loanId')) return
  url.searchParams.delete('loanId')
  window.history.replaceState(null, '', url)
}
