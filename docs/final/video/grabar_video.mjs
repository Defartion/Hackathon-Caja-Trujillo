#!/usr/bin/env node
// Video de respaldo de CuotaFlex (1920x1080, ~3 min): asesor → chat → core → cliente → alerta ENFEN → tablero.
//
// Requisitos (todo local y con datos sintéticos):
//   API:   ENFEN_MODO=oficial PYTHONPATH=src uvicorn cuotaflex.api.main:app --port 8000
//          (con ENFEN_MODO=demo también funciona: activa la alerta de demo antes de la app del cliente)
//   Apps:  en web/asesor, web/cliente y web/tablero: npm run build && npx vite preview --port 5173 | 5174 | 5175
//   Edge o Chrome instalados y ffmpeg en el PATH.
//
// Uso:  node docs/final/video/grabar_video.mjs [--salida ~/Videos/CuotaFlex] [--asesor C00006] [--chat C00006] [--cliente C00003]
//       Tras la integración de la fase 3: --asesor E001 --chat E003 --cliente E002 (casos estrella del lote B).
//
// Graba con el Chrome DevTools Protocol (Page.startScreencast), arma el MP4 con ffmpeg y le incrusta los
// subtítulos; deja el .srt al lado. Las cifras de los subtítulos se leen de la pantalla al grabar.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as esperar } from 'node:timers/promises';
import { parseArgs } from 'node:util';

const { values: op } = parseArgs({
  options: {
    salida: { type: 'string', default: join(homedir(), 'Videos', 'CuotaFlex') },
    nombre: { type: 'string', default: 'cuotaflex-video-respaldo' },
    asesor: { type: 'string', default: 'C00006' }, // ficha: pronóstico, selección por simulación y riesgo
    chat: { type: 'string' }, // solicitud del chat (por defecto, la misma de la ficha)
    cliente: { type: 'string', default: 'C00003' }, // se registra en el core y se ve en la app del cliente
    api: { type: 'string', default: 'http://127.0.0.1:8000' },
    navegador: { type: 'string' },
    conservar: { type: 'boolean', default: false }, // deja los fotogramas para revisar
  },
});
const APPS = { asesor: 'http://localhost:5173', cliente: 'http://localhost:5174', tablero: 'http://localhost:5175' };
const ANCHO = 1920;
const ALTO = 1080;
const ALTO_PAGINA = 940; // los 140 px de abajo son la franja de subtítulos: nunca tapan la interfaz
const PUERTO_CDP = 9335;
const PRODUCTO = { fija: 'la cuota fija', aplazamiento: 'la cuota fija con aplazamientos', estacional: 'cuotas estacionales' };

// ---------------------------------------------------------------- API y servicios

async function api(metodo, ruta, cuerpo) {
  const r = await fetch(op.api + ruta, {
    method: metodo,
    headers: cuerpo ? { 'Content-Type': 'application/json' } : undefined,
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  if (!r.ok) throw new Error(`${metodo} ${ruta} respondió ${r.status}`);
  return r.json();
}

async function verificarServicios() {
  for (const [nombre, url] of [['API', op.api + '/alertas/enfen'], ...Object.entries(APPS)]) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(String(r.status));
    } catch (e) {
      throw new Error(`${nombre} no responde en ${url} (${e.message}). Revisa los requisitos al inicio del archivo.`);
    }
  }
  if (spawnSync('ffmpeg', ['-version']).status !== 0) throw new Error('Falta ffmpeg en el PATH.');
}

function rutaNavegador() {
  if (op.navegador) return op.navegador;
  const candidatos = {
    win32: ['C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
      'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'],
    darwin: ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'],
  }[process.platform] ?? ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge'];
  const ruta = candidatos.find((c) => existsSync(c));
  if (!ruta) throw new Error('No encontré Edge ni Chrome: indica la ruta con --navegador');
  return ruta;
}

// ---------------------------------------------------------------- Chrome DevTools Protocol

let ws;
let siguiente = 0;
const pendientes = new Map();
const cuadros = [];
let t0 = null;
let carpetaCuadros;
const reloj = () => (performance.now() - t0) / 1000;

function cdp(method, params = {}) {
  return new Promise((ok, mal) => {
    const id = ++siguiente;
    pendientes.set(id, (d) => (d.error ? mal(new Error(`${method}: ${JSON.stringify(d.error)}`)) : ok(d.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function alMensaje(m) {
  const d = JSON.parse(m.data);
  if (d.id && pendientes.has(d.id)) {
    pendientes.get(d.id)(d);
    pendientes.delete(d.id);
  } else if (d.method === 'Page.screencastFrame') {
    const archivo = `f${String(cuadros.length).padStart(6, '0')}.jpg`;
    writeFileSync(join(carpetaCuadros, archivo), Buffer.from(d.params.data, 'base64'));
    cuadros.push({ archivo, t: reloj() });
    ws.send(JSON.stringify({ id: ++siguiente, method: 'Page.screencastFrameAck', params: { sessionId: d.params.sessionId } }));
  }
}

async function conectar(puerto) {
  for (let i = 0; i < 100; i++) {
    try {
      const lista = await (await fetch(`http://127.0.0.1:${puerto}/json/list`)).json();
      const pagina = lista.find((t) => t.type === 'page');
      if (pagina) {
        ws = new WebSocket(pagina.webSocketDebuggerUrl);
        await new Promise((ok, mal) => {
          ws.addEventListener('open', ok, { once: true });
          ws.addEventListener('error', mal, { once: true });
        });
        ws.addEventListener('message', alMensaje);
        return;
      }
    } catch { /* el navegador aún no abre el puerto */ }
    await esperar(200);
  }
  throw new Error('El navegador no respondió por CDP');
}

async function evaluar(expresion) {
  const r = await cdp('Runtime.evaluate', { expression: expresion, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`Error en la página: ${r.exceptionDetails.text} (${expresion.slice(0, 80)})`);
  return r.result.value;
}

async function esperarA(expresion, ms = 30000) {
  const fin = Date.now() + ms;
  while (Date.now() < fin) {
    try {
      if (await evaluar(expresion)) return;
    } catch { /* la página aún carga */ }
    await esperar(200);
  }
  throw new Error(`Se agotó la espera: ${expresion}`);
}

async function metricas(ancho, alto, escala) {
  await cdp('Emulation.setDeviceMetricsOverride', { width: ancho, height: alto, deviceScaleFactor: escala, mobile: false });
}

async function ir(url, condicion) {
  await cdp('Page.navigate', { url });
  await esperarA("document.readyState === 'complete' && !!window.__cf", 60000);
  if (condicion) await esperarA(condicion, 90000);
  await evaluar('__cf.instalar()');
}

// Ayudantes dentro de cada página: cursor visible, resaltes y rótulos de sección.
const AYUDANTES = String.raw`(() => {
  const css = '#cf-cursor{position:fixed;left:0;top:0;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;' +
    'border:3px solid #C8102E;background:rgba(200,16,46,.15);z-index:2147483647;pointer-events:none;' +
    'transition:transform .7s cubic-bezier(.2,.7,.2,1);box-shadow:0 2px 8px rgba(0,0,0,.25)}' +
    '#cf-cursor.pulso{animation:cfpulso .5s ease-out}' +
    '@keyframes cfpulso{0%{box-shadow:0 0 0 0 rgba(200,16,46,.65)}100%{box-shadow:0 0 0 26px rgba(200,16,46,0)}}' +
    '.cf-resalte{position:fixed;border:4px solid #C8102E;border-radius:14px;z-index:2147483646;pointer-events:none;transition:opacity .5s}' +
    '#cf-rotulo{position:fixed;left:50%;top:18px;transform:translateX(-50%);background:#1F2328;color:#fff;font:600 26px Inter,Segoe UI,Arial,sans-serif;' +
    'padding:12px 28px;border-radius:999px;border-bottom:4px solid #C8102E;z-index:2147483647;pointer-events:none;transition:opacity .6s}';
  const instalar = () => {
    if (!document.body || document.getElementById('cf-cursor')) return;
    const estilo = document.createElement('style');
    estilo.textContent = css;
    document.head.appendChild(estilo);
    const c = document.createElement('div');
    c.id = 'cf-cursor';
    c.style.transform = 'translate(' + Math.round(innerWidth * 0.55) + 'px,' + Math.round(innerHeight * 0.55) + 'px)';
    document.body.appendChild(c);
  };
  document.addEventListener('DOMContentLoaded', instalar);
  const limpio = (s) => (s || '').replace(/\s+/g, ' ').trim();
  window.__cf = {
    instalar,
    buscar(texto, selector) {
      const lista = [...document.querySelectorAll(selector || 'button,a,summary,tr,[role=button],h1,h2,h3,label')];
      return lista.find((e) => e.getClientRects().length > 0 && limpio(e.textContent).includes(texto)) || null;
    },
    tarjeta(texto) {
      const h = window.__cf.buscar(texto, 'h1,h2,h3,summary');
      return h ? (h.closest('.tarjeta,section,aside,details') || h.parentElement) : null;
    },
    centro(e) {
      const r = e.getBoundingClientRect();
      return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
    },
    mover(x, y) {
      instalar();
      document.getElementById('cf-cursor').style.transform = 'translate(' + x + 'px,' + y + 'px)';
    },
    pulso() {
      const c = document.getElementById('cf-cursor');
      c.classList.remove('pulso');
      void c.offsetWidth;
      c.classList.add('pulso');
    },
    resaltar(e, ms) {
      if (!e) return false;
      const r = e.getBoundingClientRect();
      const d = document.createElement('div');
      d.className = 'cf-resalte';
      Object.assign(d.style, { left: r.left - 8 + 'px', top: r.top - 8 + 'px', width: r.width + 16 + 'px', height: r.height + 16 + 'px' });
      document.body.appendChild(d);
      setTimeout(() => { d.style.opacity = '0'; setTimeout(() => d.remove(), 600); }, ms || 3000);
      return true;
    },
    rotulo(texto, ms) {
      document.getElementById('cf-rotulo')?.remove();
      const d = document.createElement('div');
      d.id = 'cf-rotulo';
      d.textContent = texto;
      document.body.appendChild(d);
      setTimeout(() => { d.style.opacity = '0'; setTimeout(() => d.remove(), 700); }, ms || 3200);
    },
  };
})();`;

const js = (valor) => JSON.stringify(valor);

async function desplazar(texto, selector = 'h1,h2,h3,summary', bloque = 'start') {
  const ok = await evaluar(`(() => { const e = __cf.buscar(${js(texto)}, ${js(selector)}); if (!e) return false;
    const y = e.getBoundingClientRect().top + scrollY - 90;
    window.scrollTo({ top: ${js(bloque)} === 'center' ? y - innerHeight / 3 : y, behavior: 'smooth' }); return true; })()`);
  if (!ok) throw new Error(`No encontré «${texto}» para desplazarme`);
  await esperar(1300);
}

async function clic(texto, selector) {
  const existe = await evaluar(`(() => { const e = __cf.buscar(${js(texto)}, ${js(selector)}); if (!e) return false;
    e.scrollIntoView({ behavior: 'smooth', block: 'center' }); return true; })()`);
  if (!existe) throw new Error(`No encontré «${texto}» (${selector})`);
  await esperar(900);
  const p = await evaluar(`(() => { const c = __cf.centro(__cf.buscar(${js(texto)}, ${js(selector)})); __cf.mover(c.x, c.y); return c; })()`);
  await esperar(800);
  await evaluar('__cf.pulso()');
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
    await cdp('Input.dispatchMouseEvent', { type, x: p.x, y: p.y, button: type === 'mouseMoved' ? 'none' : 'left', clickCount: 1 });
  }
  await esperar(400);
}

async function clicSelector(selector) {
  const p = await evaluar(`(() => { const e = document.querySelector(${js(selector)}); if (!e) return null;
    e.scrollIntoView({ block: 'nearest' }); const c = __cf.centro(e); __cf.mover(c.x, c.y); return c; })()`);
  if (!p) throw new Error(`No encontré ${selector}`);
  await esperar(800);
  await evaluar('__cf.pulso()');
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
    await cdp('Input.dispatchMouseEvent', { type, x: p.x, y: p.y, button: type === 'mouseMoved' ? 'none' : 'left', clickCount: 1 });
  }
  await esperar(400);
}

async function escribir(texto) {
  for (const letra of texto) {
    await cdp('Input.insertText', { text: letra });
    await esperar(70);
  }
}

async function resaltar(texto, ms = 3200, selector = 'h1,h2,h3,summary') {
  await evaluar(`__cf.resaltar(__cf.tarjeta(${js(texto)}) || __cf.buscar(${js(texto)}, ${js(selector)}), ${ms})`);
}

const rotulo = (texto) => evaluar(`__cf.rotulo(${js(texto)}, 3200)`);

function tarjetaTitulo(titulo, subtitulo, nota) {
  const html = `<!doctype html><meta charset="utf-8"><body style="margin:0;height:100vh;display:grid;place-items:center;
    background:#fff;font-family:Inter,'Segoe UI',Arial,sans-serif;color:#1F2328"><div style="text-align:center">
    <div style="font-size:96px;font-weight:600;letter-spacing:-1px">Cuota<b style="color:#C8102E">Flex</b></div>
    <div style="font-size:44px;margin-top:18px;font-weight:600">${titulo}</div>
    <div style="font-size:30px;margin-top:14px;color:#57606A">${subtitulo}</div>
    <div style="height:7px;width:240px;background:#C8102E;margin:34px auto 0;border-radius:4px"></div>
    <div style="font-size:22px;margin-top:26px;color:#57606A">${nota}</div></div></body>`;
  return 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
}

// ---------------------------------------------------------------- subtítulos

const cues = [];
function subtitulo(texto) {
  const t = reloj();
  const ultimo = cues.at(-1);
  if (ultimo && ultimo.fin === null) ultimo.fin = t;
  if (texto) cues.push({ inicio: t, fin: null, texto });
}

function srt(desplazamiento, fin) {
  const hora = (s) => {
    const ms = Math.max(0, Math.round((s - desplazamiento) * 1000));
    const p = (n, l = 2) => String(n).padStart(l, '0');
    return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
  };
  return cues.map((c, i) => `${i + 1}\n${hora(c.inicio)} --> ${hora(c.fin ?? fin)}\n${c.texto}\n`).join('\n');
}

// ---------------------------------------------------------------- lectura de cifras en pantalla

const texto = () => evaluar('document.body.innerText');

async function leerFicha() {
  const t = await texto();
  const m = (re) => (t.match(re) || [])[1];
  return {
    producto: m(/Propuesta del agente\s*\n\s*(\w+)/),
    aprobado: m(/Monto aprobado\s*S\/ ([\d,]+)/),
    plazo: m(/Monto aprobado\s*S\/ [\d,]+\s*Plazo\s*(\d+) meses/),
    defaultFija: m(/Default \(3 cuotas impagas\)\s*([\d.]+%)/),
    defaultFlex: m(/Default \(3 cuotas impagas\)\s*[\d.]+%\s*→\s*([\d.]+%)/),
  };
}

async function leerIndicadores() {
  const t = await texto();
  const r = t.match(/Default \(3 cuotas impagas\)[\s\S]{0,60}?Fija\s*([\d.,]+\s?%)[\s\S]{0,40}?CuotaFlex\s*([\d.,]+\s?%)/);
  return r ? { fija: r[1].replace(/\s/g, ''), flex: r[2].replace(/\s/g, '') } : null;
}

const soles = (n) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
const NOMBRE_RUBRO = { agricultura: 'negocio agrícola', pesca: 'pescador artesanal', bodega: 'bodega',
  comercio_campana: 'comercio de campaña', calzado: 'taller de calzado', servicios: 'negocio de servicios' };

// ---------------------------------------------------------------- guion

async function guion(cartera, enfen) {
  const idChat = op.chat ?? op.asesor;
  const pedido = cartera.find((c) => c.cliente_id === op.asesor);
  const pedidoChat = cartera.find((c) => c.cliente_id === idChat);
  const pedido2 = cartera.find((c) => c.cliente_id === op.cliente);
  if (!pedido || !pedidoChat || !pedido2) throw new Error(`No encontré ${op.asesor}, ${idChat} o ${op.cliente} en /motor/cartera-demo`);

  subtitulo('Recorrido de respaldo de la demo: asesor, agente, core, app del cliente, alerta del ENFEN y tablero.');
  await esperar(5000);

  // 1. Asesor: pronóstico, selección por simulación y propuesta
  await ir(`${APPS.asesor}/`, `!!__cf.buscar(${js(op.asesor)}, 'tr')`);
  await rotulo('1 · El asesor revisa la solicitud');
  subtitulo('La bandeja del asesor: solicitudes de microempresarios de La Libertad (datos sintéticos).');
  await esperar(4000);
  await clic(op.asesor, 'tr');
  await esperarA("!!__cf.buscar('Riesgo simulado', 'h1,h2,h3')", 90000);
  const ficha = await leerFicha();
  subtitulo(`Un ${NOMBRE_RUBRO[pedido.rubro] ?? pedido.rubro} en ${pedido.region} pide S/ ${soles(pedido.principal)} a ${pedido.plazo} meses.`);
  await esperar(4000);
  await desplazar('Ventas: histórico y pronóstico');
  subtitulo('El motor pronostica sus ventas con incertidumbre (banda p10–p90) a partir de su historial.');
  await esperar(4500);
  await resaltar('Propuesta del agente');
  subtitulo(ficha.aprobado && ficha.aprobado !== soles(pedido.principal)
    ? `Propone S/ ${ficha.aprobado} a ${ficha.plazo} meses: así la cuota no supera su capacidad de pago en el escenario conservador.`
    : `Propone ${PRODUCTO[ficha.producto] ?? ficha.producto} dentro de su capacidad de pago.`);
  await esperar(6000);
  await desplazar('Bitácora del agente');
  await resaltar('Bitácora del agente', 3500);
  subtitulo(`Selección por simulación: compara cuota fija, aplazamientos y estacional; aquí elige ${PRODUCTO[ficha.producto] ?? ficha.producto}.`);
  await esperar(6500);
  await desplazar('Riesgo simulado');
  await resaltar('Riesgo simulado', 3500);
  subtitulo(ficha.defaultFija
    ? `Default simulado: ${ficha.defaultFija} con la cuota fija → ${ficha.defaultFlex} con CuotaFlex, en los mismos escenarios.`
    : 'El riesgo simulado baja frente a la cuota fija, en los mismos escenarios.');
  await esperar(6000);

  // 2. Chat del agente
  if (idChat !== op.asesor) {
    await ir(`${APPS.asesor}/cliente/${idChat}`, "!!__cf.buscar('Riesgo simulado', 'h1,h2,h3')");
    const fichaChat = await leerFicha();
    subtitulo(`Otra solicitud: un ${NOMBRE_RUBRO[pedidoChat.rubro] ?? pedidoChat.rubro} en ${pedidoChat.region} pide S/ ${soles(pedidoChat.principal)}; el agente propone S/ ${fichaChat.aprobado}.`);
    await esperar(4500);
  }
  await evaluar('window.scrollTo({ top: 0, behavior: "smooth" })');
  await esperar(1000);
  await rotulo('2 · El agente explica y recalcula');
  await clic('Pregúntale al agente', 'summary');
  subtitulo('El asesor le pregunta al agente: responde con las herramientas del motor y verifica cada cifra.');
  await esperar(2500);
  await clic('¿Por qué bajó el monto?', 'button');
  await esperarA("document.querySelectorAll('.chat-agente-turno').length >= 1 && !document.querySelector('.chat-agente-estado')", 60000);
  await evaluar("document.querySelector('.chat-agente-turno:last-child')?.scrollIntoView({ behavior: 'smooth', block: 'center' })");
  subtitulo('«¿Por qué bajó el monto?»: lo explica con la bitácora y marca «Cifras verificadas».');
  await esperar(7500);
  await clicSelector('.chat-agente-formulario input, .chat-agente-formulario textarea');
  subtitulo('También acepta preguntas libres, por ejemplo otro plazo.');
  const plazoPedido = pedidoChat.plazo === 24 ? 18 : pedidoChat.plazo;
  await escribir(`¿Y a ${plazoPedido} meses?`);
  await esperar(600);
  await clic('Enviar', 'button');
  await esperarA("document.querySelectorAll('.chat-agente-turno').length >= 2 && !document.querySelector('.chat-agente-estado')", 60000);
  await evaluar("document.querySelector('.chat-agente-turno:last-child')?.scrollIntoView({ behavior: 'smooth', block: 'center' })");
  const respuesta = await evaluar("document.querySelector('.chat-agente-turno:last-child .chat-agente-respuesta')?.innerText || ''");
  const plazoRespuesta = Number((respuesta.match(/a (\d+) meses/) || [])[1]);
  subtitulo(plazoRespuesta && plazoRespuesta !== plazoPedido
    ? `Pide ${plazoPedido} meses y el motor mantiene ${plazoRespuesta}: a ${plazoPedido} la cuota no cabría en su capacidad de pago.`
    : `Recalcula la propuesta a ${plazoPedido} meses con el motor, sin inventar cifras.`);
  await esperar(7500);

  // 3. Del asesor al core
  await ir(`${APPS.asesor}/cliente/${op.cliente}`, "!!__cf.buscar('Riesgo simulado', 'h1,h2,h3')");
  await rotulo('3 · Del asesor al core');
  const ficha2 = await leerFicha();
  subtitulo(`Otro caso: un ${NOMBRE_RUBRO[pedido2.rubro] ?? pedido2.rubro} en ${pedido2.region}. El motor elige ${PRODUCTO[ficha2.producto] ?? ficha2.producto}.`);
  await esperar(3500);
  await desplazar('Cuota vs. capacidad de pago');
  subtitulo({
    estacional: 'Las cuotas suben en temporada alta y bajan en temporada baja, siempre bajo su capacidad de pago.',
    aplazamiento: 'Cuota fija con hasta dos aplazamientos si está al día, dentro de su capacidad de pago.',
  }[ficha2.producto] ?? 'La cuota queda dentro de su capacidad de pago en el escenario conservador.');
  await esperar(5500);
  await evaluar("document.body.insertAdjacentHTML('beforeend', '<div style=\"height:45vh\"></div>')"); // para centrar el registro
  await desplazar('Registro en el core', 'h1,h2,h3', 'center');
  subtitulo('Se registra en el core compatible con Fineract: solicitud, aprobación y desembolso.');
  await clic('Registrar solicitud', 'button');
  await esperarA("(() => { const b = __cf.buscar('Aprobar', 'button'); return b && !b.disabled; })()", 60000);
  const prestamo = await evaluar("(document.body.innerText.match(/Préstamo\\s*#(\\d+)/) || [])[1]");
  await esperar(1000);
  await clic('Aprobar', 'button');
  await esperarA("(() => { const b = __cf.buscar('Desembolsar', 'button'); return b && !b.disabled; })()", 30000);
  await esperar(800);
  await clic('Desembolsar', 'button');
  await esperarA("(() => { const b = __cf.buscar('Desembolsar', 'button'); return b && b.disabled; })()", 30000);
  await esperar(3000);
  if (!prestamo) throw new Error('No pude leer el número del préstamo registrado');

  // 4. App del cliente (con la alerta del ENFEN vigente)
  if (enfen.modo === 'demo') await api('POST', '/alertas/enfen/demo', { estado: 'ALERTA_NINO' });
  await metricas(ANCHO / 2, ALTO_PAGINA / 2, 2);
  await ir(`${APPS.cliente}/?loanId=${prestamo}`, "!!__cf.buscar('Próxima cuota', 'section,span,h2')");
  await rotulo('4 · La app del cliente');
  subtitulo('El cliente ve su próxima cuota y si es temporada alta o baja.');
  await esperar(4500);
  const conBanner = await evaluar("!!__cf.buscar('Usar alivio', 'button')");
  if (conBanner) {
    await evaluar("__cf.resaltar(__cf.buscar('Alerta El Niño activa', 'section'), 3500)");
    subtitulo(enfen.modo === 'demo'
      ? 'Con la alerta de El Niño activa (modo demo), la app le ofrece el alivio.'
      : 'El ENFEN mantiene la Alerta de El Niño Costero: como su crédito tiene la cláusula, la app le ofrece el alivio.');
    await esperar(5500);
    await clic('Usar alivio', 'button');
    await esperarA("document.body.innerText.includes('Alivio aplicado')", 30000);
    subtitulo('Con un toque paga solo la cuota mínima este mes; la diferencia se reparte, con interés, en las siguientes.');
    await esperar(6500);
  }
  await clic('Cronograma', 'button');
  subtitulo('Su cronograma muestra las temporadas y lo que ya pagó.');
  await esperar(5000);

  // 5. Alerta oficial del ENFEN en el tablero
  await metricas(ANCHO, ALTO_PAGINA, 1);
  await ir(`${APPS.tablero}/`, "!!document.querySelector('.enfen-boton:not([disabled])')");
  await rotulo('5 · La alerta oficial del ENFEN');
  const estado = await api('GET', '/alertas/enfen');
  await evaluar("__cf.resaltar(document.querySelector('.enfen-distintivo'), 4000)");
  subtitulo(estado.modo === 'oficial'
    ? `El estado se lee del comunicado oficial del ENFEN en PDF: ${estado.etiqueta} (N° ${estado.numero}).`
    : `Modo demo: ${estado.etiqueta}. En producción se lee del comunicado oficial del ENFEN.`);
  await esperar(6000);
  await clicSelector('.enfen-boton');
  await esperarA("!!document.querySelector('.enfen-panel table, .enfen-vacio')", 30000);
  subtitulo('Impacto en la cartera: créditos con cláusula, saldo cubierto y cuotas de alivio por rubro y región.');
  await esperar(7000);
  await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await cdp('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });

  // 6. Toda la cartera (600 créditos × 200 escenarios, precalculada antes de grabar: el tablero dice "desde caché")
  await rotulo('6 · ¿Y en toda la cartera?');
  await clic('Completo', '[aria-labelledby="lbl-tam"] button');
  await clic('Base', 'button.btn-esc');
  subtitulo('Simulación de la cartera: cuota fija contra CuotaFlex con las mismas trayectorias de ventas y El Niño.');
  await esperarA("document.body.innerText.includes('Corrida #1') && !document.querySelector('.resultados.cargando')", 300000);
  await esperar(2500);
  const base = await leerIndicadores();
  subtitulo(base ? `600 créditos × 200 escenarios: default de ${base.fija} con la cuota fija → ${base.flex} con CuotaFlex.`
    : 'El default de la cartera baja con CuotaFlex.');
  await esperar(6500);
  await clic('Año El Niño', 'button.btn-esc');
  await esperarA("document.body.innerText.includes('Corrida #2') && !document.querySelector('.resultados.cargando')", 300000);
  await esperar(2500);
  const nino = await leerIndicadores();
  subtitulo(nino ? `Si hubiera El Niño todos los años: ${nino.fija} con la cuota fija → ${nino.flex} con CuotaFlex.`
    : 'Aun con El Niño, CuotaFlex reduce el default.');
  await esperar(6500);

  subtitulo(null);
  await ir(tarjetaTitulo('Cuotas que se adaptan al flujo del negocio', 'Cajatón 2026 · Caja Trujillo · Reto NEG-01',
    'Datos sintéticos · resultados de la simulación calibrada de la fase 2'));
  await esperar(5000);
}

// ---------------------------------------------------------------- armado del video

function armar(tFinal) {
  const inicio = cuadros[0].t;
  const lista = ['ffconcat version 1.0'];
  cuadros.forEach((c, i) => {
    const fin = i + 1 < cuadros.length ? cuadros[i + 1].t : tFinal;
    lista.push(`file '${c.archivo}'`, `duration ${Math.max(fin - c.t, 0.001).toFixed(3)}`);
  });
  lista.push(`file '${cuadros.at(-1).archivo}'`);
  writeFileSync(join(carpetaCuadros, 'cuadros.txt'), lista.join('\n') + '\n');
  const subtitulos = srt(inicio, tFinal);
  writeFileSync(join(carpetaCuadros, 'subtitulos.srt'), subtitulos);
  mkdirSync(op.salida, { recursive: true });
  const mp4 = join(op.salida, `${op.nombre}.mp4`);
  writeFileSync(join(op.salida, `${op.nombre}.srt`), subtitulos);
  const estilo = 'FontName=Arial,FontSize=11,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=0,Shadow=0,MarginV=7,MarginL=16,MarginR=16';
  const filtro = `scale=${ANCHO}:${ALTO_PAGINA}:force_original_aspect_ratio=decrease,` +
    `pad=${ANCHO}:${ALTO_PAGINA}:(ow-iw)/2:(oh-ih)/2:color=white,pad=${ANCHO}:${ALTO}:0:0:color=0x1F2328,` +
    `subtitles=subtitulos.srt:force_style='${estilo}'`;
  const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'cuadros.txt', '-vf', filtro,
    '-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4],
  { cwd: carpetaCuadros, stdio: 'inherit' });
  if (r.status !== 0) throw new Error('ffmpeg no pudo armar el video');
  return { mp4, duracion: tFinal - inicio };
}

async function principal() {
  await verificarServicios();
  const enfen = await api('GET', '/alertas/enfen');
  const cartera = await api('GET', '/motor/cartera-demo?n=30&semilla=7');
  await api('POST', '/alertas/demo/cartera?n=20'); // para que el impacto en la cartera tenga datos
  // La cartera completa tarda en calcularse: se precalcula para que el tablero la sirva desde su caché.
  const escenarios = await api('GET', '/simulacion/escenarios');
  for (const id of ['base', 'el_nino']) {
    const cambios = escenarios.find((e) => e.id === id)?.cambios ?? {};
    console.log(`Precalculando el escenario ${id} (600 × 200)…`);
    await api('POST', '/simulacion/correr', { n_clientes: 600, n_escenarios: 200, semilla: 2026, replanificar: true, cambios });
  }
  carpetaCuadros = mkdtempSync(join(tmpdir(), 'cuotaflex-cuadros-'));
  const perfil = mkdtempSync(join(tmpdir(), 'cuotaflex-perfil-'));
  const navegador = spawn(rutaNavegador(), ['--headless=new', `--remote-debugging-port=${PUERTO_CDP}`, `--user-data-dir=${perfil}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--hide-scrollbars', '--mute-audio',
    '--force-color-profile=srgb', `--window-size=${ANCHO},${ALTO}`, '--lang=es-PE', 'about:blank'], { stdio: 'ignore' });
  try {
    await conectar(PUERTO_CDP);
    await cdp('Page.enable');
    await cdp('Runtime.enable');
    await cdp('Page.addScriptToEvaluateOnNewDocument', { source: AYUDANTES });
    await metricas(ANCHO, ALTO_PAGINA, 1);
    await ir(tarjetaTitulo('Cuotas que se adaptan al flujo del negocio', 'Asesor · agente · cliente · alerta del ENFEN · tablero',
      'Video de respaldo · versión de la fase 2 · datos 100 % sintéticos'));
    t0 = performance.now();
    await cdp('Page.startScreencast', { format: 'jpeg', quality: 90, maxWidth: ANCHO, maxHeight: ALTO_PAGINA, everyNthFrame: 1 });
    await guion(cartera, enfen);
    const tFinal = reloj();
    await cdp('Page.stopScreencast');
    const { mp4, duracion } = armar(tFinal);
    console.log(`Listo: ${mp4} (${duracion.toFixed(0)} s, ${cuadros.length} fotogramas, ${cues.length} subtítulos)`);
  } finally {
    ws?.close();
    navegador.kill();
    await esperar(500);
    rmSync(perfil, { recursive: true, force: true });
    if (!op.conservar && carpetaCuadros) rmSync(carpetaCuadros, { recursive: true, force: true });
    else if (carpetaCuadros) console.log(`Fotogramas en ${carpetaCuadros}`);
  }
}

principal().catch((e) => {
  console.error(`No se pudo grabar: ${e.message}`);
  process.exit(1);
});
