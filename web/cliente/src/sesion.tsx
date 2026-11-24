// Sesión por rol con PIN (fase 3). Solo se activa si la API responde {"auth": true} en /auth/config.
// Instala un envoltorio de fetch que agrega el token a toda llamada a la API, incluidas las de
// componentes que no usan api.ts (chat del agente, indicador del ENFEN).
import { FormEvent, ReactNode, useEffect, useState } from "react";

const API = ((import.meta.env.VITE_API_URL as string | undefined) || "http://127.0.0.1:8000").replace(/\/+$/, "");
const CLAVE = "cuotaflex_token";
const EXPIRADA = "cuotaflex-sesion-expirada";

function leerToken(): string | null {
  try {
    return sessionStorage.getItem(CLAVE);
  } catch {
    return null;
  }
}

function guardarToken(t: string | null) {
  try {
    if (t) sessionStorage.setItem(CLAVE, t);
    else sessionStorage.removeItem(CLAVE);
  } catch {
    /* almacenamiento no disponible: la sesión dura lo que la pestaña */
  }
}

let instalado = false;
function instalarFetch() {
  if (instalado) return;
  instalado = true;
  const original = window.fetch.bind(window);
  window.fetch = async (entrada: RequestInfo | URL, init: RequestInit = {}) => {
    const url = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
    const t = leerToken();
    const haciaApi = url.startsWith(API) && !url.startsWith(`${API}/auth/`);
    if (t && haciaApi) {
      const headers = new Headers(init.headers ?? (entrada instanceof Request ? entrada.headers : undefined));
      headers.set("Authorization", `Bearer ${t}`);
      init = { ...init, headers };
    }
    const r = await original(entrada, init);
    if (r.status === 401 && haciaApi) {
      guardarToken(null);
      window.dispatchEvent(new Event(EXPIRADA));
    }
    return r;
  };
}

type Estado = "cargando" | "login" | "listo";

export function ConSesion({ rol, titulo, children }: { rol: "asesor" | "cliente" | "supervisor"; titulo: string; children: ReactNode }) {
  const [estado, setEstado] = useState<Estado>("cargando");
  useEffect(() => {
    instalarFetch();
    let vivo = true;
    fetch(`${API}/auth/config`)
      .then((r) => (r.ok ? r.json() : { auth: false }))
      .catch(() => ({ auth: false })) // sin API: la app muestra su propio mensaje de error
      .then((c: { auth?: boolean }) => vivo && setEstado(c.auth && !leerToken() ? "login" : "listo"));
    const expirar = () => setEstado("login");
    window.addEventListener(EXPIRADA, expirar);
    return () => {
      vivo = false;
      window.removeEventListener(EXPIRADA, expirar);
    };
  }, []);
  if (estado === "cargando") return null;
  if (estado === "login") return <Login rol={rol} titulo={titulo} alEntrar={() => setEstado("listo")} />;
  return <>{children}</>;
}

function Login({ rol, titulo, alEntrar }: { rol: string; titulo: string; alEntrar: () => void }) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setOcupado(true);
    setError(null);
    try {
      const r = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rol, pin }),
      });
      if (!r.ok) throw new Error(r.status === 401 ? "PIN incorrecto." : `Error ${r.status}`);
      guardarToken((await r.json()).token);
      alEntrar();
    } catch (err) {
      setError(err instanceof TypeError ? "No se pudo conectar con la API." : (err as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "var(--cf-fondo, #F7F7F8)", padding: 16 }}>
      <form onSubmit={entrar} style={{ background: "#fff", border: "1px solid var(--cf-gris-200, #E5E7EB)", borderTop: "4px solid var(--cf-rojo, #C8102E)", borderRadius: "var(--cf-radio, 10px)", padding: 28, width: "min(360px, 100%)", fontFamily: "var(--cf-fuente, system-ui)" }}>
        <div style={{ fontWeight: 800, fontSize: 22 }}>
          Cuota<span style={{ color: "var(--cf-rojo, #C8102E)" }}>Flex</span>
        </div>
        <div style={{ color: "var(--cf-gris-600, #57606A)", margin: "4px 0 20px" }}>{titulo}</div>
        <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14 }}>
          PIN de {rol}
          <input type="password" inputMode="numeric" autoFocus value={pin} onChange={(e) => setPin(e.target.value)}
            style={{ font: "inherit", fontSize: 18, padding: "10px 12px", border: "1px solid var(--cf-gris-200, #E5E7EB)", borderRadius: 8, letterSpacing: 4 }} />
        </label>
        {error && <div role="alert" style={{ color: "var(--cf-rojo-osc, #8E0B20)", marginTop: 10 }}>{error}</div>}
        <button type="submit" disabled={ocupado || !pin}
          style={{ marginTop: 18, width: "100%", minHeight: 44, border: 0, borderRadius: 8, background: "var(--cf-rojo, #C8102E)", color: "#fff", fontWeight: 600, fontSize: 16, cursor: "pointer", opacity: ocupado || !pin ? 0.6 : 1 }}>
          {ocupado ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
