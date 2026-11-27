// Sesión por rol (fase 3) con tres formas de entrar: cuenta (correo y contraseña), cuenta nueva o PIN del rol.
// Solo se activa si la API responde {"auth": true} en /auth/config. Copia idéntica en las 3 apps
// (tests/test_web_tema.py lo verifica). Instala un envoltorio de fetch que agrega el token a toda llamada
// a la API, incluidas las de componentes que no usan api.ts (chat del agente, indicador del ENFEN).
import { FormEvent, KeyboardEvent, ReactNode, useEffect, useRef, useState } from "react";
import Marca, { Ritmo } from "./marca";
import { BotonTema } from "./apariencia";

type Rol = "asesor" | "cliente" | "supervisor";
type Regla = "libre" | "codigo" | "no";

const API = ((import.meta.env.VITE_API_URL as string | undefined) || "http://127.0.0.1:8000").replace(/\/+$/, "");
// Una sesión por rol: las tres apps comparten dominio en el despliegue y no deben reusar el token de otro rol.
const PREFIJO = "cuotaflex_token.";
let CLAVE = `${PREFIJO}sin-rol`;
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

/** Quién tiene la sesión abierta en esta pestaña. `nombre` es null si entró con el PIN del rol. */
export interface Usuario {
  rol: Rol;
  nombre: string | null;
  /** Fase 4: préstamo al que está atada la sesión del cliente (código del préstamo o cuenta vinculada). */
  prestamo: number | null;
  /** Fase 4: usuario personal del asesor o supervisor. */
  usuario: string | null;
}

export function usuarioSesion(rol: Rol): Usuario | null {
  try {
    const token = sessionStorage.getItem(`${PREFIJO}${rol}`);
    if (!token) return null;
    const cuerpo = token.split(".")[0].replace(/-/g, "+").replace(/_/g, "/");
    const datos = JSON.parse(atob(cuerpo + "=".repeat((4 - (cuerpo.length % 4)) % 4)));
    return {
      rol,
      nombre: typeof datos.nombre === "string" && datos.nombre.trim() ? datos.nombre : null,
      prestamo: typeof datos.prestamo === "number" ? datos.prestamo : null,
      usuario: typeof datos.usuario === "string" ? datos.usuario : null,
    };
  } catch {
    return null;
  }
}

/** Lo que la API sabe de la sesión (GET /auth/yo). Sin token no se consulta nada. */
export interface Perfil {
  sesion: boolean;
  rol?: Rol;
  metodo?: "cuenta" | "pin" | "personal" | "codigo";
  usuario?: string | null;
  prestamo?: number | null;
  nombre?: string | null;
  correo?: string | null;
  creado?: string | null;
  expira?: number;
}

export async function perfilSesion(rol: Rol, signal?: AbortSignal): Promise<Perfil> {
  let token: string | null = null;
  try {
    token = sessionStorage.getItem(`${PREFIJO}${rol}`);
  } catch {
    token = null;
  }
  if (!token) return { sesion: false };
  const r = await fetch(`${API}/auth/yo`, { headers: { Authorization: `Bearer ${token}` }, signal });
  return r.ok ? ((await r.json()) as Perfil) : { sesion: false };
}

export function iniciales(nombre: string | null): string {
  if (!nombre) return "PIN";
  const partes = nombre.trim().split(/\s+/);
  return ((partes[0]?.[0] ?? "") + (partes.length > 1 ? partes[partes.length - 1][0] : "")).toUpperCase();
}

/** Fase 4: una cuenta de cliente (correo) se liga a su préstamo con el código que dio el asesor. */
export async function vincularPrestamo(prestamo: number, codigo: string): Promise<void> {
  const r = await fetch(`${API}/auth/vincular`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prestamo, codigo }),
  });
  const datos = await r.json().catch(() => null);
  if (!r.ok) throw new Error(typeof datos?.detail === "string" ? datos.detail : `Error ${r.status}. Intenta de nuevo.`);
  guardarToken(datos.token);
}

export function cerrarSesion(rol: Rol) {
  try {
    sessionStorage.removeItem(`${PREFIJO}${rol}`);
  } catch {
    /* sin almacenamiento */
  }
  window.location.reload();
}

type Estado = "cargando" | "login" | "listo";

export function ConSesion({ rol, titulo, children }: { rol: Rol; titulo: string; children: ReactNode }) {
  CLAVE = `${PREFIJO}${rol}`;
  const [estado, setEstado] = useState<Estado>("cargando");
  const [regla, setRegla] = useState<Regla>("no");
  const [pinGeneral, setPinGeneral] = useState(true);
  useEffect(() => {
    instalarFetch();
    let vivo = true;
    fetch(`${API}/auth/config`)
      .then((r) => (r.ok ? r.json() : { auth: false }))
      .catch(() => ({ auth: false })) // sin API: la app muestra su propio mensaje de error
      .then((c: { auth?: boolean; registro?: Partial<Record<Rol, Regla>>; pin_general?: boolean }) => {
        if (!vivo) return;
        setRegla(c.registro?.[rol] ?? "no");
        setPinGeneral(c.pin_general !== false);
        setEstado(c.auth && !leerToken() ? "login" : "listo");
      });
    const expirar = () => setEstado("login");
    window.addEventListener(EXPIRADA, expirar);
    return () => {
      vivo = false;
      window.removeEventListener(EXPIRADA, expirar);
    };
  }, [rol]);
  if (estado === "cargando") return null;
  if (estado === "login")
    return <Acceso rol={rol} titulo={titulo} regla={regla} pinGeneral={pinGeneral} alEntrar={() => setEstado("listo")} />;
  return <>{children}</>;
}

// ------------------------------------------------------------------ pantalla de acceso

// "llave" (fase 4): el cliente entra con número de préstamo + código; asesor y supervisor, con usuario + PIN personal.
type Modo = "llave" | "ingresar" | "crear" | "pin";
type Campo = "ident" | "nombre" | "correo" | "contrasena" | "codigo" | "pin";
type Errores = Partial<Record<Campo, string>>;

const ROTULO: Record<Rol, string> = { asesor: "Asesor de negocios", cliente: "Cliente", supervisor: "Supervisor" };
const LEMA: Record<Rol, string> = {
  asesor: "Evalúa solicitudes y arma planes de cuotas que siguen la temporada de cada negocio.",
  cliente: "Consulta tu próxima cuota y tu cronograma cuando quieras, desde el celular.",
  supervisor: "Compara la cuota fija con Thinku en miles de escenarios, con El Niño incluido.",
};
const CABECERA: Record<Modo, string> = {
  llave: "Ingresa con tu usuario",
  ingresar: "Ingresa a tu cuenta",
  crear: "Crea tu cuenta",
  pin: "Entra con el PIN general",
};
const cabecera = (modo: Modo, rol: Rol) => (modo === "llave" && rol === "cliente" ? "Entra con tu código" : CABECERA[modo]);
const RE_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const NIVELES = ["", "Débil", "Aceptable", "Buena", "Fuerte"];

function nivelClave(c: string): number {
  if (!c) return 0;
  let n = 0;
  if (c.length >= 8) n++;
  if (/\p{L}/u.test(c) && /\d/.test(c)) n++;
  if (c.length >= 12) n++;
  if (/[^\p{L}\d]/u.test(c) || (/\p{Lu}/u.test(c) && /\p{Ll}/u.test(c))) n++;
  return Math.max(1, n);
}

function validar(modo: Modo, v: Record<Campo, string>, pideCodigo: boolean, rol: Rol): Errores {
  const e: Errores = {};
  if (modo === "llave") {
    if (rol === "cliente") {
      if (!/^\d+$/.test(v.ident.trim()) || Number(v.ident) < 1) e.ident = "Escribe el número de tu préstamo.";
      if (!/^\d{6}$/.test(v.pin)) e.pin = "El código tiene 6 dígitos.";
    } else {
      if (!v.ident.trim()) e.ident = "Escribe tu usuario.";
      if (!/^\d{6}$/.test(v.pin)) e.pin = "El PIN personal tiene 6 dígitos.";
    }
    return e;
  }
  if (modo === "pin") {
    if (!v.pin.trim()) e.pin = "Escribe el PIN.";
    return e;
  }
  if (modo === "crear") {
    const nombre = v.nombre.trim();
    if (nombre.length < 3 || (nombre.match(/\p{L}/gu) ?? []).length < 2) e.nombre = "Escribe tu nombre completo.";
  }
  if (!RE_CORREO.test(v.correo.trim())) e.correo = "Escribe un correo válido, por ejemplo nombre@correo.com.";
  if (modo === "ingresar") {
    if (!v.contrasena) e.contrasena = "Escribe tu contraseña.";
  } else {
    if (v.contrasena.length < 8) e.contrasena = "La contraseña necesita al menos 8 caracteres.";
    else if (!/\p{L}/u.test(v.contrasena) || !/\d/.test(v.contrasena)) e.contrasena = "Usa letras y números en la contraseña.";
    if (pideCodigo && !v.codigo.trim()) e.codigo = "Escribe el código de autorización.";
  }
  return e;
}

async function enviar(ruta: string, cuerpo: object): Promise<{ token: string }> {
  let r: Response;
  try {
    r = await fetch(`${API}${ruta}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
  } catch {
    throw new ErrorAcceso(0, "No se pudo conectar con la API. Revisa tu conexión e intenta de nuevo.");
  }
  const datos = await r.json().catch(() => null);
  if (!r.ok) {
    const detalle = typeof datos?.detail === "string" ? datos.detail : `Error ${r.status}. Intenta de nuevo.`;
    throw new ErrorAcceso(r.status, detalle, datos?.campo ?? undefined);
  }
  return datos;
}

class ErrorAcceso extends Error {
  constructor(public readonly estado: number, message: string, public readonly campo?: Campo) {
    super(message);
  }
}

function Acceso({
  rol, titulo, regla, pinGeneral, alEntrar,
}: { rol: Rol; titulo: string; regla: Regla; pinGeneral: boolean; alEntrar: () => void }) {
  const [modo, setModo] = useState<Modo>("llave");
  const [v, setV] = useState<Record<Campo, string>>({ ident: "", nombre: "", correo: "", contrasena: "", codigo: "", pin: "" });
  const [errores, setErrores] = useState<Errores>({});
  const [intento, setIntento] = useState(false);
  const [general, setGeneral] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [verClave, setVerClave] = useState(false);
  const [sacude, setSacude] = useState(false);
  const [focoPin, setFocoPin] = useState(false);
  const pideCodigo = modo === "crear" && regla === "codigo";
  const refs = {
    ident: useRef<HTMLInputElement>(null),
    nombre: useRef<HTMLInputElement>(null),
    correo: useRef<HTMLInputElement>(null),
    contrasena: useRef<HTMLInputElement>(null),
    codigo: useRef<HTMLInputElement>(null),
    pin: useRef<HTMLInputElement>(null),
  };
  const primerCambio = useRef(true);
  const focoEnPestanas = useRef(false);

  // Al cambiar de modo, el foco va al primer dato (salvo si se navega entre pestañas con las flechas).
  // Al abrir, solo en equipos con mouse: en el celular abriría el teclado encima de la pantalla.
  useEffect(() => {
    const primero =
      modo === "llave" ? refs.ident : modo === "crear" ? refs.nombre : modo === "pin" ? refs.pin : refs.correo;
    if (focoEnPestanas.current) focoEnPestanas.current = false;
    else if (!primerCambio.current || window.matchMedia("(pointer: fine)").matches) primero.current?.focus();
    primerCambio.current = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modo]);

  const cambiarModo = (m: Modo) => {
    setModo(m);
    setErrores({});
    setIntento(false);
    setGeneral(null);
  };

  const escribir = (campo: Campo, valor: string) => {
    const nuevo = { ...v, [campo]: valor };
    setV(nuevo);
    if (intento) setErrores(validar(modo, nuevo, pideCodigo, rol)); // el error se va apenas se corrige
  };

  async function entrar(e: FormEvent) {
    e.preventDefault();
    if (ocupado) return;
    setIntento(true);
    setGeneral(null);
    const encontrados = validar(modo, v, pideCodigo, rol);
    setErrores(encontrados);
    const primero = (Object.keys(refs) as Campo[]).find((c) => encontrados[c]);
    if (primero) {
      refs[primero].current?.focus();
      return;
    }
    setOcupado(true);
    try {
      const datos =
        modo === "llave"
          ? rol === "cliente"
            ? await enviar("/auth/cliente", { prestamo: Number(v.ident.trim()), codigo: v.pin })
            : await enviar("/auth/personal", { usuario: v.ident.trim(), pin: v.pin, rol })
          : modo === "pin"
          ? await enviar("/auth/login", { rol, pin: v.pin.trim() })
          : modo === "ingresar"
            ? await enviar("/auth/ingresar", { correo: v.correo.trim(), contrasena: v.contrasena, rol })
            : await enviar("/auth/registro", {
                rol,
                nombre: v.nombre.trim(),
                correo: v.correo.trim(),
                contrasena: v.contrasena,
                codigo: pideCodigo ? v.codigo.trim() : null,
              });
      guardarToken(datos.token);
      alEntrar();
    } catch (err) {
      const fallo = err instanceof ErrorAcceso ? err : new ErrorAcceso(0, "Algo salió mal. Intenta de nuevo.");
      if (fallo.estado === 401 && (modo === "pin" || modo === "llave")) {
        setErrores({ pin: modo === "pin" ? "PIN incorrecto. Revísalo e intenta de nuevo." : fallo.message });
        setV((x) => ({ ...x, pin: "" }));
        refs.pin.current?.focus();
      } else if (fallo.campo && fallo.campo in refs) {
        setErrores({ [fallo.campo]: fallo.message });
        refs[fallo.campo].current?.focus();
      } else {
        setGeneral(fallo.message);
      }
      if (fallo.estado === 401) setSacude(true);
    } finally {
      setOcupado(false);
    }
  }

  const ayudaError = (campo: Campo) =>
    errores[campo] ? (
      <span className="acc-error" id={`acc-${campo}-error`}>
        {errores[campo]}
      </span>
    ) : null;

  const props = (campo: Campo, ayuda?: string) => ({
    id: `acc-${campo}`,
    ref: refs[campo],
    name: campo,
    value: v[campo],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => escribir(campo, e.target.value),
    "aria-invalid": errores[campo] ? true : undefined,
    "aria-describedby": errores[campo] ? `acc-${campo}-error` : ayuda,
  });

  const nivel = nivelClave(v.contrasena);
  const casillas = modo === "llave" ? 6 : Math.max(4, v.pin.length);
  const textoBoton = ocupado
    ? { llave: "Entrando…", ingresar: "Ingresando…", crear: "Creando tu cuenta…", pin: "Entrando…" }[modo]
    : { llave: "Entrar", ingresar: "Ingresar", crear: "Crear cuenta", pin: "Entrar" }[modo];
  const cuentas = modo === "ingresar" || modo === "crear";

  const subtitulo =
    modo === "llave"
      ? rol === "cliente"
        ? "Usa el número de tu préstamo y el código de 6 dígitos que te envió tu asesor."
        : "Usa el usuario y el PIN personal que te dio tu supervisor."
      : modo === "pin"
      ? `PIN general de demostración: lo comparte todo el equipo de ${rol}.`
      : modo === "crear"
        ? regla === "codigo"
          ? `Para una cuenta de ${rol} necesitas el código de autorización de tu equipo.`
          : rol === "cliente"
            ? "Solo toma un minuto. Al terminar entras directo a tu crédito."
            : "Solo toma un minuto. Al terminar entras directo a la app."
        : `Usa el correo y la contraseña de tu cuenta de ${rol}.`;

  const teclaPestana = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const otro = modo === "ingresar" ? "crear" : "ingresar";
    focoEnPestanas.current = true;
    cambiarModo(otro);
    document.getElementById(`acc-tab-${otro}`)?.focus();
  };

  return (
    <div className="acc">
      <aside className="acc-marca">
        <div className="acc-marca__cab">
          <Marca invertida />
          <small>Cajathón 2026, Caja Trujillo</small>
        </div>
        <div className="acc-marca__texto">
          <h1>{titulo}</h1>
          <p className="acc-marca__lema">{LEMA[rol]}</p>
        </div>
        <Ritmo />
      </aside>

      <main className="acc-panel">
        <BotonTema />
        <div
          className={`acc-caja ${sacude ? "sacude" : ""}`}
          onAnimationEnd={(e) => e.animationName === "acc-sacude" && setSacude(false)}
        >
          <span className="acc-rol">{ROTULO[rol]}</span>
          <div className="acc-cab">
            <h2>{cabecera(modo, rol)}</h2>
            <p>{subtitulo}</p>
          </div>

          {cuentas && regla !== "no" && (
            <div className="acc-pestanas" role="tablist" aria-label="Elige cómo entrar" data-activa={modo === "crear" ? 1 : 0}>
              <span className="acc-pestanas__indicador" aria-hidden="true" />
              {(["ingresar", "crear"] as const).map((m) => (
                <button
                  key={m}
                  id={`acc-tab-${m}`}
                  type="button"
                  role="tab"
                  aria-selected={modo === m}
                  aria-controls="acc-formulario"
                  tabIndex={modo === m ? 0 : -1}
                  onClick={() => cambiarModo(m)}
                  onKeyDown={teclaPestana}
                >
                  {m === "ingresar" ? "Ingresar" : "Crear cuenta"}
                </button>
              ))}
            </div>
          )}

          <form
            id="acc-formulario"
            className="acc-form"
            role={cuentas && regla !== "no" ? "tabpanel" : undefined}
            aria-labelledby={cuentas && regla !== "no" ? `acc-tab-${modo}` : undefined}
            onSubmit={entrar}
            noValidate
          >
            {general && (
              <div className="acc-alerta" role="alert">
                {general}
              </div>
            )}

            {modo === "crear" && (
              <div className="acc-campo">
                <label htmlFor="acc-nombre">Nombre completo</label>
                <input {...props("nombre")} type="text" autoComplete="name" placeholder="Ej.: Rosa Quispe Vela…" />
                {ayudaError("nombre")}
              </div>
            )}

            {modo === "llave" && (
              <div className="acc-campo">
                <label htmlFor="acc-ident">{rol === "cliente" ? "Número de préstamo" : "Usuario"}</label>
                <input
                  {...props("ident", "acc-ident-ayuda")}
                  type="text"
                  inputMode={rol === "cliente" ? "numeric" : "text"}
                  autoComplete={rol === "cliente" ? "off" : "username"}
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder={rol === "cliente" ? "Ej.: 12…" : "Ej.: ana.torres…"}
                />
                {errores.ident ? (
                  ayudaError("ident")
                ) : (
                  <span className="acc-ayuda" id="acc-ident-ayuda">
                    {rol === "cliente" ? "Está en el mensaje que te envió tu asesor." : "Te lo da tu supervisor."}
                  </span>
                )}
              </div>
            )}

            {cuentas && (
              <div className="acc-campo">
                <label htmlFor="acc-correo">Correo</label>
                <input
                  {...props("correo")}
                  type="email"
                  inputMode="email"
                  autoComplete={modo === "crear" ? "email" : "username"}
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder="nombre@correo.com…"
                />
                {ayudaError("correo")}
              </div>
            )}

            {cuentas && (
              <div className="acc-campo">
                <label htmlFor="acc-contrasena">Contraseña</label>
                <div className="acc-clave">
                  <input
                    {...props("contrasena", modo === "crear" ? "acc-fuerza" : undefined)}
                    type={verClave ? "text" : "password"}
                    autoComplete={modo === "crear" ? "new-password" : "current-password"}
                    autoCapitalize="none"
                    spellCheck={false}
                  />
                  <button
                    type="button"
                    aria-pressed={verClave}
                    aria-controls="acc-contrasena"
                    aria-label={verClave ? "Ocultar contraseña" : "Mostrar contraseña"}
                    onClick={() => setVerClave(!verClave)}
                  >
                    {verClave ? "Ocultar" : "Mostrar"}
                  </button>
                </div>
                {ayudaError("contrasena")}
                {modo === "crear" && (
                  <div className="acc-fuerza" id="acc-fuerza" data-nivel={nivel}>
                    <div className="acc-fuerza__barras" aria-hidden="true">
                      <span /><span /><span /><span />
                    </div>
                    <ul className="acc-fuerza__reglas">
                      <li className={v.contrasena.length >= 8 ? "ok" : ""}>Al menos 8 caracteres</li>
                      <li className={/\p{L}/u.test(v.contrasena) && /\d/.test(v.contrasena) ? "ok" : ""}>Letras y números</li>
                      {nivel > 0 && <li className="nivel" aria-live="polite">Seguridad: {NIVELES[nivel].toLowerCase()}</li>}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {pideCodigo && (
              <div className="acc-campo">
                <label htmlFor="acc-codigo">Código de autorización</label>
                <input
                  {...props("codigo", "acc-codigo-ayuda")}
                  type="password"
                  inputMode="numeric"
                  autoComplete="off"
                />
                {errores.codigo ? (
                  ayudaError("codigo")
                ) : (
                  <span className="acc-ayuda" id="acc-codigo-ayuda">
                    Es el PIN de {rol} que te dio tu equipo. Solo se pide al crear la cuenta.
                  </span>
                )}
              </div>
            )}

            {(modo === "pin" || modo === "llave") && (
              <div className="acc-campo">
                <label htmlFor="acc-pin">
                  {modo === "pin" ? `PIN general de ${rol}` : rol === "cliente" ? "Código de acceso" : "PIN personal"}
                </label>
                <div className="acc-pin" data-casillas={casillas} data-error={errores.pin ? true : undefined}>
                  <input
                    {...props("pin")}
                    className="acc-pin__input"
                    type="password"
                    inputMode="numeric"
                    autoComplete="off"
                    maxLength={modo === "llave" ? 6 : 12}
                    onChange={(e) => escribir("pin", e.target.value.replace(modo === "llave" ? /\D/g : /\s/g, ""))}
                    onFocus={() => setFocoPin(true)}
                    onBlur={() => setFocoPin(false)}
                  />
                  {Array.from({ length: casillas }, (_, i) => (
                    <span
                      key={i}
                      aria-hidden="true"
                      className={`acc-pin__casilla ${i < v.pin.length ? "llena" : ""} ${
                        focoPin && i === Math.min(v.pin.length, casillas - 1) ? "activa" : ""
                      }`}
                    />
                  ))}
                </div>
                {ayudaError("pin")}
              </div>
            )}

            <button type="submit" className="acc-boton" disabled={ocupado}>
              {ocupado && <span className="acc-giro" aria-hidden="true" />}
              {textoBoton}
            </button>
          </form>

          {(modo !== "llave" || regla !== "no" || pinGeneral) && <div className="acc-o">o</div>}
          {modo !== "llave" ? (
            <button type="button" className="acc-boton acc-boton--sec" onClick={() => cambiarModo("llave")}>
              {rol === "cliente" ? "Entrar con mi código" : "Entrar con mi usuario y PIN"}
            </button>
          ) : (
            regla !== "no" && (
              <button type="button" className="acc-boton acc-boton--sec" onClick={() => cambiarModo("ingresar")}>
                Ingresar con correo y contraseña
              </button>
            )
          )}
          {modo === "pin" && regla !== "no" && (
            <button type="button" className="acc-enlace" onClick={() => cambiarModo("ingresar")}>
              Ingresar con correo y contraseña
            </button>
          )}
          {modo !== "pin" && pinGeneral && (
            <button type="button" className="acc-enlace" onClick={() => cambiarModo("pin")}>
              Entrar con el PIN general de {rol} (demo)
            </button>
          )}
          <p className="acc-nota">Demo con datos 100% sintéticos.</p>
        </div>
      </main>
    </div>
  );
}
