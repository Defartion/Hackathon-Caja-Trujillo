import { ReactNode, useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import Marca from "./marca";
import { BotonTema } from "./apariencia";
import { cerrarSesion, iniciales, usuarioSesion } from "./sesion";

const ICONOS: Record<string, string> = {
  bandeja: "M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6z",
  nueva: "M12 5v14M5 12h14",
  prestamos: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
  comite: "M4 12l5 5L20 6",
  simular: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  alerta: "M12 3l10 18H2zM12 10v5M12 18v.5",
  avisos: "M4 5h16v11H8l-4 4z",
  reiniciar: "M4 12a8 8 0 1 0 3-6.2M4 4v4h4",
  salir: "M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l4-4-4-4M14 12H4",
  rol: "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3",
};

export function Icono({ nombre }: { nombre: string }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONOS[nombre] ?? ""} />
    </svg>
  );
}

export interface Opcion {
  ruta: string;
  texto: string;
  icono: string;
  ayuda: string;
  /** true mientras la pantalla no esté integrada (se muestra como "pronto"). */
  pronto?: boolean;
  /** Rutas hijas que también marcan la opción como activa. */
  incluye?: string[];
}

/** Lo que puede hacer el Asesor de Negocios. Para habilitar una opción, quita `pronto`. */
export const OPCIONES_ASESOR: Opcion[] = [
  { ruta: "/", texto: "Bandeja de solicitudes", icono: "bandeja", ayuda: "Revisa y propone", incluye: ["/cliente/"] },
  { ruta: "/nueva", texto: "Nueva solicitud", icono: "nueva", ayuda: "Ciclo del negocio y plan de cuotas" },
  { ruta: "/prestamos", texto: "Préstamos registrados", icono: "prestamos", ayuda: "Aprueba y desembolsa" },
  { ruta: "/comite", texto: "Comité de créditos", icono: "comite", ayuda: "Validar e imprimir expedientes" },
];

export default function Lateral({ rol, opciones, children }: { rol: string; opciones: Opcion[]; children: ReactNode }) {
  const [abierto, setAbierto] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setAbierto(false), [pathname]);
  const usuario = usuarioSesion("asesor");

  const activa = (o: Opcion) =>
    o.ruta === "/" ? pathname === "/" || (o.incluye ?? []).some((r) => pathname.startsWith(r)) : pathname.startsWith(o.ruta);

  return (
    <div className={`shell ${abierto ? "menu-abierto" : ""}`}>
      <header className="barra-movil">
        <button type="button" className="btn-menu" aria-label="Abrir menú" aria-expanded={abierto} onClick={() => setAbierto(!abierto)}>
          ☰
        </button>
        <Marca tam={28} />
        <span className="rol-mini">{usuario?.nombre ?? rol}</span>
      </header>

      <aside className="lateral" aria-label="Menú principal">
        <div className="lateral-cab">
          <Marca />
          <div className="rol">{rol}</div>
        </div>
        <nav>
          <ul>
            {opciones.map((o) =>
              o.pronto ? (
                <li key={o.ruta}>
                  <span className="opcion deshabilitada" aria-disabled="true" title="Disponible al integrar la fase 4">
                    <span className="icono"><Icono nombre={o.icono} /></span>
                    <span className="textos">
                      <span className="t">{o.texto}</span>
                      <span className="a">{o.ayuda}</span>
                    </span>
                    <span className="pronto">pronto</span>
                  </span>
                </li>
              ) : (
                <li key={o.ruta}>
                  <NavLink to={o.ruta} className={() => `opcion ${activa(o) ? "activa" : ""}`} aria-current={activa(o) ? "page" : undefined}>
                    <span className="icono"><Icono nombre={o.icono} /></span>
                    <span className="textos">
                      <span className="t">{o.texto}</span>
                      <span className="a">{o.ayuda}</span>
                    </span>
                  </NavLink>
                </li>
              ),
            )}
          </ul>
        </nav>
        <div className="lateral-pie">
          {usuario && (
            <div className="usuario">
              <span className={`usuario__avatar ${usuario.nombre ? "" : "pin"}`} aria-hidden="true">
                {iniciales(usuario.nombre)}
              </span>
              <span className="usuario__datos">
                <b>{usuario.nombre ?? "Sesión con PIN"}</b>
                <span>{rol}</span>
              </span>
            </div>
          )}
          <BotonTema className="opcion-sec" texto />
          {import.meta.env.BASE_URL !== "/" && (
            <a className="opcion-sec" href="/">
              <Icono nombre="rol" /> Cambiar de rol
            </a>
          )}
          {usuario && (
            <button type="button" className="opcion-sec" onClick={() => cerrarSesion("asesor")}>
              <Icono nombre="salir" /> Salir
            </button>
          )}
          <div className="nota-pie">Datos 100% sintéticos</div>
        </div>
      </aside>
      <div className="velo" onClick={() => setAbierto(false)} aria-hidden="true" />

      <main className="contenido">{children}</main>
    </div>
  );
}
