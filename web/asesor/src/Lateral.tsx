import { ReactNode, useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

const ICONOS: Record<string, string> = {
  bandeja: "M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6z",
  nueva: "M12 5v14M5 12h14",
  prestamos: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
  comite: "M4 12l5 5L20 6",
  simular: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  alerta: "M12 3l10 18H2zM12 10v5M12 18v.5",
  avisos: "M4 5h16v11H8l-4 4z",
  reiniciar: "M4 12a8 8 0 1 0 3-6.2M4 4v4h4",
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
  { ruta: "/nueva", texto: "Nueva solicitud", icono: "nueva", ayuda: "Estima el ciclo y arma el plan", pronto: true },
  { ruta: "/prestamos", texto: "Préstamos registrados", icono: "prestamos", ayuda: "Aprueba y desembolsa" },
  { ruta: "/comite", texto: "Comité de créditos", icono: "comite", ayuda: "Vista para riesgos y comité", pronto: true },
];

const CLAVE_TOKEN = "cuotaflex_token";

function haySesion() {
  try {
    return !!sessionStorage.getItem(CLAVE_TOKEN);
  } catch {
    return false;
  }
}

export default function Lateral({ rol, opciones, children }: { rol: string; opciones: Opcion[]; children: ReactNode }) {
  const [abierto, setAbierto] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setAbierto(false), [pathname]);

  const salir = () => {
    try {
      sessionStorage.removeItem(CLAVE_TOKEN);
    } catch {
      /* sin almacenamiento */
    }
    window.location.reload();
  };

  const activa = (o: Opcion) =>
    o.ruta === "/" ? pathname === "/" || (o.incluye ?? []).some((r) => pathname.startsWith(r)) : pathname.startsWith(o.ruta);

  return (
    <div className={`shell ${abierto ? "menu-abierto" : ""}`}>
      <header className="barra-movil">
        <button type="button" className="btn-menu" aria-label="Abrir menú" aria-expanded={abierto} onClick={() => setAbierto(!abierto)}>
          ☰
        </button>
        <div className="marca">
          Cuota<span>Flex</span>
        </div>
        <span className="rol-mini">{rol}</span>
      </header>

      <aside className="lateral" aria-label="Menú principal">
        <div className="lateral-cab">
          <div className="marca">
            Cuota<span>Flex</span>
          </div>
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
          {import.meta.env.BASE_URL !== "/" && (
            <a className="opcion-sec" href="/">
              Cambiar de rol
            </a>
          )}
          {haySesion() && (
            <button type="button" className="opcion-sec" onClick={salir}>
              Salir
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
