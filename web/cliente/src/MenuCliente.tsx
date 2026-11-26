import { useEffect, useRef, useState } from 'react'
import { LogOut, Menu, Repeat, UserRound, X } from 'lucide-react'
import { cerrarSesion, iniciales, usuarioSesion } from './sesion'
import { BotonTema } from './apariencia'

/** Menú secundario (☰): lo que no se usa a diario. Lo frecuente sigue en la barra inferior. */
export default function MenuCliente({ prestamoId, onPerfil }: { prestamoId: number | null; onPerfil: () => void }) {
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

  const enDespliegue = import.meta.env.BASE_URL !== '/'
  const usuario = usuarioSesion('cliente')
  const sesion = usuario !== null

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
          {usuario?.nombre && (
            <div className="menu-cli__usuario">
              <span className="menu-cli__avatar" aria-hidden="true">{iniciales(usuario.nombre)}</span>
              <span><b>{usuario.nombre}</b><span>Cuenta de cliente</span></span>
            </div>
          )}
          <div className="menu-cli__titulo">
            {prestamoId !== null ? `Mi crédito N° ${prestamoId}` : 'Mi crédito'}
          </div>
          <button type="button" className="menu-cli__op" role="menuitem" onClick={() => { setAbierto(false); onPerfil() }}>
            <UserRound size={18} aria-hidden="true" /> Mi perfil
          </button>
          <BotonTema className="menu-cli__op" rol="menuitemcheckbox" texto />
          {enDespliegue && (
            <a className="menu-cli__op" role="menuitem" href="/">
              <Repeat size={18} aria-hidden="true" /> Cambiar de rol
            </a>
          )}
          {sesion && (
            <button type="button" className="menu-cli__op" role="menuitem" onClick={() => cerrarSesion('cliente')}>
              <LogOut size={18} aria-hidden="true" /> Salir
            </button>
          )}
        </div>
      )}
    </div>
  )
}
