import { useEffect, useRef, useState } from 'react'
import { LogOut, Menu, Repeat, X } from 'lucide-react'

const CLAVE_TOKEN = 'cuotaflex_token.cliente'

function haySesion() {
  try {
    return !!sessionStorage.getItem(CLAVE_TOKEN)
  } catch {
    return false
  }
}

/** Menú secundario (☰): lo que no se usa a diario. Lo frecuente sigue en la barra inferior. */
export default function MenuCliente({ prestamoId }: { prestamoId: number | null }) {
  const [abierto, setAbierto] = useState(false)
  const caja = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!abierto) return
    const cerrar = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !caja.current?.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener('mousedown', cerrar)
    document.addEventListener('keydown', cerrar)
    return () => {
      document.removeEventListener('mousedown', cerrar)
      document.removeEventListener('keydown', cerrar)
    }
  }, [abierto])

  const salir = () => {
    try {
      sessionStorage.removeItem(CLAVE_TOKEN)
    } catch {
      /* sin almacenamiento */
    }
    window.location.reload()
  }

  const enDespliegue = import.meta.env.BASE_URL !== '/'
  const sesion = haySesion()

  return (
    <div className="menu-cli" ref={caja}>
      <button
        type="button"
        className="menu-cli__boton"
        aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
        aria-expanded={abierto}
        onClick={() => setAbierto(!abierto)}
      >
        {abierto ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
      </button>
      {abierto && (
        <div className="menu-cli__panel" role="menu">
          <div className="menu-cli__titulo">
            Mi crédito{prestamoId !== null ? ` · N° ${prestamoId}` : ''}
          </div>
          {enDespliegue && (
            <a className="menu-cli__op" role="menuitem" href="/">
              <Repeat size={18} aria-hidden="true" /> Cambiar de rol
            </a>
          )}
          {sesion && (
            <button type="button" className="menu-cli__op" role="menuitem" onClick={salir}>
              <LogOut size={18} aria-hidden="true" /> Salir
            </button>
          )}
          {!enDespliegue && !sesion && <div className="menu-cli__vacio">Sin opciones adicionales.</div>}
        </div>
      )}
    </div>
  )
}
