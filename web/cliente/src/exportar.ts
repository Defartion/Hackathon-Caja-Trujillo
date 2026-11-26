// Exportar tablas a PDF, Excel (.xlsx), CSV, JSON y texto, todo en el navegador y sin dependencias.
// Copia idéntica en las tres apps (tests/test_web_tema.py lo verifica).
//  - PDF: Helvetica estándar (WinAnsi, sin incrustar fuentes), A4 vertical u horizontal según las columnas.
//  - XLSX: Office Open XML mínimo dentro de un ZIP sin comprimir; una hoja de resumen y una por tabla.
//  - CSV: solo la primera tabla, UTF-8 con BOM para que Excel lea las tildes.
//  - JSON: valores sin formato (números, fechas ISO, porcentajes como fracción) y la descripción de columnas.

export type Formato = "pdf" | "xlsx" | "csv" | "json" | "txt";
export type TipoDato = "texto" | "entero" | "decimal" | "moneda" | "porcentaje" | "fecha";

export interface Columna {
  clave: string;
  titulo: string;
  tipo?: TipoDato;
}

export interface Tabla {
  titulo: string;
  columnas: Columna[];
  filas: Record<string, unknown>[];
}

export interface Dato {
  etiqueta: string;
  valor: unknown;
  tipo?: TipoDato;
}

export interface Documento {
  /** Nombre del archivo sin extensión ni fecha, p. ej. "cronograma-prestamo-2". */
  archivo: string;
  titulo: string;
  subtitulo?: string;
  resumen?: Dato[];
  tablas: Tabla[];
  notas?: string[];
}

export const FORMATOS: { formato: Formato; nombre: string; detalle: string }[] = [
  { formato: "pdf", nombre: "PDF", detalle: "Para imprimir o compartir" },
  { formato: "xlsx", nombre: "Excel (.xlsx)", detalle: "Una hoja por tabla" },
  { formato: "csv", nombre: "CSV", detalle: "Tabla principal, para otras apps" },
  { formato: "json", nombre: "JSON", detalle: "Datos con su estructura" },
  { formato: "txt", nombre: "Texto (.txt)", detalle: "Columnas alineadas" },
];

const MIME: Record<Formato, string> = {
  pdf: "application/pdf",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  csv: "text/csv;charset=utf-8",
  json: "application/json;charset=utf-8",
  txt: "text/plain;charset=utf-8",
};

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];
const NUMERO = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ENTERO = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const NOTA_DATOS = "Datos 100% sintéticos · CuotaFlex, Cajathón 2026";

const dos = (n: number) => String(n).padStart(2, "0");
const vacio = (v: unknown) => v === null || v === undefined || v === "" || (typeof v === "number" && !Number.isFinite(v));

function numero(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
  return null;
}

/** "2026-11-30" (o un Date) a fecha local, sin el desfase de zona horaria de `new Date("2026-11-30")`. */
function fecha(v: unknown): Date | null {
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v;
  if (typeof v !== "string") return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) ? null : d;
}

const iso = (d: Date) => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
const marcaTiempo = (d = new Date()) =>
  `${dos(d.getDate())}/${dos(d.getMonth() + 1)}/${d.getFullYear()} ${dos(d.getHours())}:${dos(d.getMinutes())}`;

/** Valor legible para PDF y texto: S/ 1,102.07 · 45.00% · 30 nov 2026. */
export function formatear(v: unknown, tipo: TipoDato = "texto"): string {
  if (vacio(v)) return "—";
  const n = numero(v);
  switch (tipo) {
    case "moneda":
      return n === null ? String(v) : `${n < 0 ? "-" : ""}S/ ${NUMERO.format(Math.abs(n))}`;
    case "decimal":
      return n === null ? String(v) : NUMERO.format(n);
    case "entero":
      return n === null ? String(v) : ENTERO.format(n);
    case "porcentaje":
      return n === null ? String(v) : `${NUMERO.format(n * 100)}%`;
    case "fecha": {
      const d = fecha(v);
      return d ? `${d.getDate()} ${MESES[d.getMonth()]} ${d.getFullYear()}` : String(v);
    }
    default:
      return typeof v === "boolean" ? (v ? "Sí" : "No") : String(v);
  }
}

/** Valor sin adornos para CSV (números con punto decimal, fechas ISO). */
function crudo(v: unknown, tipo: TipoDato = "texto"): string {
  if (vacio(v)) return "";
  const n = numero(v);
  if (tipo === "moneda" || tipo === "decimal") return n === null ? String(v) : n.toFixed(2);
  if (tipo === "entero") return n === null ? String(v) : String(Math.round(n));
  if (tipo === "porcentaje") return n === null ? String(v) : `${(n * 100).toFixed(2)}%`;
  if (tipo === "fecha") {
    const d = fecha(v);
    return d ? iso(d) : String(v);
  }
  return typeof v === "boolean" ? (v ? "Sí" : "No") : String(v);
}

function valorJson(v: unknown, tipo: TipoDato = "texto"): unknown {
  if (vacio(v)) return null;
  if (tipo === "fecha") {
    const d = fecha(v);
    return d ? iso(d) : v;
  }
  if (tipo !== "texto") return numero(v) ?? v;
  return v;
}

const numerico = (tipo?: TipoDato) => tipo !== undefined && tipo !== "texto" && tipo !== "fecha";

// ---------------------------------------------------------------- CSV, JSON y texto

function csv(doc: Documento): string {
  const tabla = doc.tablas[0];
  if (!tabla) return "";
  // Un texto que empieza con = + - @ se abre como fórmula en Excel: se antepone un apóstrofo.
  const celda = (valor: string, tipo?: TipoDato) => {
    const s = !numerico(tipo) && /^[=+\-@\t\r]/.test(valor) ? `'${valor}` : valor;
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lineas = [tabla.columnas.map((c) => celda(c.titulo)).join(",")];
  for (const fila of tabla.filas) {
    lineas.push(tabla.columnas.map((c) => celda(crudo(fila[c.clave], c.tipo), c.tipo)).join(","));
  }
  return "﻿" + lineas.join("\r\n") + "\r\n";
}

function json(doc: Documento): string {
  const ahora = new Date();
  return JSON.stringify({
    titulo: doc.titulo,
    subtitulo: doc.subtitulo ?? null,
    generado: ahora.toISOString(),
    fuente: NOTA_DATOS,
    resumen: (doc.resumen ?? []).map((d) => ({ etiqueta: d.etiqueta, valor: valorJson(d.valor, d.tipo), tipo: d.tipo ?? "texto" })),
    tablas: doc.tablas.map((t) => ({
      titulo: t.titulo,
      columnas: t.columnas.map((c) => ({ clave: c.clave, titulo: c.titulo, tipo: c.tipo ?? "texto" })),
      filas: t.filas.map((f) => Object.fromEntries(t.columnas.map((c) => [c.clave, valorJson(f[c.clave], c.tipo)]))),
    })),
    notas: doc.notas ?? [],
  }, null, 2) + "\n";
}

function txt(doc: Documento): string {
  const out: string[] = [doc.titulo];
  if (doc.subtitulo) out.push(doc.subtitulo);
  out.push(`Generado el ${marcaTiempo()}. ${NOTA_DATOS}.`, "");
  if (doc.resumen?.length) {
    const ancho = Math.max(...doc.resumen.map((d) => d.etiqueta.length)) + 3;
    out.push("Resumen");
    for (const d of doc.resumen) out.push(`  ${(d.etiqueta + " ").padEnd(ancho, ".")} ${formatear(d.valor, d.tipo)}`);
    out.push("");
  }
  for (const t of doc.tablas) {
    out.push(`${t.titulo} (${t.filas.length} ${t.filas.length === 1 ? "fila" : "filas"})`);
    const celdas = t.filas.map((f) => t.columnas.map((c) => formatear(f[c.clave], c.tipo)));
    const anchos = t.columnas.map((c, i) => Math.max(c.titulo.length, ...celdas.map((r) => r[i].length)));
    const linea = (r: string[]) =>
      r.map((s, i) => (numerico(t.columnas[i].tipo) ? s.padStart(anchos[i]) : s.padEnd(anchos[i]))).join("  ").trimEnd();
    out.push(linea(t.columnas.map((c) => c.titulo)), anchos.map((a) => "-".repeat(a)).join("  "));
    for (const r of celdas) out.push(linea(r));
    out.push("");
  }
  for (const n of doc.notas ?? []) out.push(n);
  return out.join("\n").trimEnd() + "\n";
}

// ---------------------------------------------------------------- XLSX (Office Open XML en un ZIP)

const xml = (s: string) =>
  s.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function columnaExcel(i: number): string {
  let s = "";
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

const ESTILO: Record<TipoDato | "cabecera" | "titulo" | "etiqueta", number> = {
  texto: 0, cabecera: 1, moneda: 2, entero: 3, porcentaje: 4, fecha: 5, decimal: 6, titulo: 7, etiqueta: 8,
};

function celdaXlsx(ref: string, v: unknown, tipo: TipoDato = "texto", estilo?: number): string {
  if (vacio(v)) return "";
  const s = estilo ?? ESTILO[tipo];
  if (tipo === "fecha") {
    const d = fecha(v);
    if (d) {
      const serial = (Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - Date.UTC(1899, 11, 30)) / 86400000;
      return `<c r="${ref}" s="${s}"><v>${serial}</v></c>`;
    }
  } else if (tipo !== "texto") {
    const n = numero(v);
    if (n !== null) return `<c r="${ref}" s="${s}"><v>${n}</v></c>`;
  }
  const texto = typeof v === "boolean" ? (v ? "Sí" : "No") : String(v);
  return `<c r="${ref}" t="inlineStr" s="${s === ESTILO[tipo] ? 0 : s}"><is><t xml:space="preserve">${xml(texto)}</t></is></c>`;
}

function hoja(filas: string[][], anchos: number[], opciones: { congelar?: boolean; filtro?: string } = {}): string {
  const cols = anchos.map((a, i) => `<col min="${i + 1}" max="${i + 1}" width="${Math.min(Math.max(a, 8), 60).toFixed(1)}" customWidth="1"/>`).join("");
  const vista = opciones.congelar
    ? '<sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView>'
    : '<sheetView workbookViewId="0"/>';
  const datos = filas.map((celdas, i) => `<row r="${i + 1}">${celdas.join("")}</row>`).join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews>${vista}</sheetViews><cols>${cols}</cols><sheetData>${datos}</sheetData>${opciones.filtro ? `<autoFilter ref="${opciones.filtro}"/>` : ""}</worksheet>`;
}

function nombreHoja(titulo: string, usados: Set<string>): string {
  const base = titulo.replace(/[[\]:*?/\\]/g, " ").replace(/\s+/g, " ").trim().slice(0, 28) || "Hoja";
  let nombre = base;
  for (let i = 2; usados.has(nombre.toLowerCase()); i++) nombre = `${base.slice(0, 26)} ${i}`;
  usados.add(nombre.toLowerCase());
  return nombre;
}

function xlsx(doc: Documento): Uint8Array {
  const usados = new Set<string>();
  const hojas: { nombre: string; contenido: string }[] = [];

  const resumen: string[][] = [[celdaXlsx("A1", doc.titulo, "texto", ESTILO.titulo)]];
  let r = 2;
  if (doc.subtitulo) resumen.push([celdaXlsx(`A${r++}`, doc.subtitulo)]);
  resumen.push([celdaXlsx(`A${r++}`, `Generado el ${marcaTiempo()}`)]);
  r++;
  resumen.push([]);
  for (const d of doc.resumen ?? []) {
    resumen.push([celdaXlsx(`A${r}`, d.etiqueta, "texto", ESTILO.etiqueta), celdaXlsx(`B${r}`, d.valor, d.tipo ?? "texto")]);
    r++;
  }
  for (const n of [...(doc.notas ?? []), NOTA_DATOS]) {
    resumen.push([]);
    r++;
    resumen.push([celdaXlsx(`A${r++}`, n)]);
  }
  const anchoEtiqueta = Math.max(16, ...(doc.resumen ?? []).map((d) => d.etiqueta.length + 2));
  const anchoValor = Math.max(18, ...(doc.resumen ?? []).map((d) => formatear(d.valor, d.tipo).length + 2));
  hojas.push({ nombre: nombreHoja("Resumen", usados), contenido: hoja(resumen, [anchoEtiqueta, anchoValor]) });

  for (const t of doc.tablas) {
    const filas = [t.columnas.map((c, i) => celdaXlsx(`${columnaExcel(i)}1`, c.titulo, "texto", ESTILO.cabecera))];
    t.filas.forEach((f, j) => filas.push(t.columnas.map((c, i) => celdaXlsx(`${columnaExcel(i)}${j + 2}`, f[c.clave], c.tipo))));
    const anchos = t.columnas.map((c) => Math.max(c.titulo.length + 3, ...t.filas.map((f) => formatear(f[c.clave], c.tipo).length + 2)));
    const ultima = `${columnaExcel(t.columnas.length - 1)}${Math.max(t.filas.length + 1, 1)}`;
    hojas.push({ nombre: nombreHoja(t.titulo, usados), contenido: hoja(filas, anchos, { congelar: true, filtro: `A1:${ultima}` }) });
  }

  const estilos = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="&quot;S/ &quot;#,##0.00"/><numFmt numFmtId="165" formatCode="dd/mm/yyyy"/></numFmts>
<fonts count="3"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font><font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font><font><b/><sz val="14"/><name val="Calibri"/><family val="2"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEEF1F5"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left/><right/><top/><bottom style="thin"><color rgb="FFCDD3DD"/></bottom><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="9"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;

  const archivos: [string, string][] = [
    ["[Content_Types].xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>${hojas.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("")}</Types>`],
    ["_rels/.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>`],
    ["docProps/core.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xml(doc.titulo)}</dc:title><dc:creator>CuotaFlex</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString().replace(/\.\d+Z$/, "Z")}</dcterms:created></cp:coreProperties>`],
    ["xl/workbook.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${hojas.map((h, i) => `<sheet name="${xml(h.nombre)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join("")}</sheets>${doc.tablas.length ? `<definedNames>${doc.tablas.map((t, i) => `<definedName name="_xlnm._FilterDatabase" localSheetId="${i + 1}" hidden="1">'${xml(hojas[i + 1].nombre).replace(/'/g, "''")}'!$A$1:$${columnaExcel(t.columnas.length - 1)}$${Math.max(t.filas.length + 1, 1)}</definedName>`).join("")}</definedNames>` : ""}</workbook>`],
    ["xl/_rels/workbook.xml.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${hojas.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join("")}<Relationship Id="rId${hojas.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
    ["xl/styles.xml", estilos],
    ...hojas.map((h, i) => [`xl/worksheets/sheet${i + 1}.xml`, h.contenido] as [string, string]),
  ];
  return zip(archivos);
}

const TABLA_CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(datos: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < datos.length; i++) c = TABLA_CRC[(c ^ datos[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** ZIP sin compresión (método 0): basta para un .xlsx y evita una dependencia. */
function zip(archivos: [string, string][]): Uint8Array {
  const cod = new TextEncoder();
  const ahora = new Date();
  const hora = (ahora.getHours() << 11) | (ahora.getMinutes() << 5) | (ahora.getSeconds() >> 1);
  const dia = ((ahora.getFullYear() - 1980) << 9) | ((ahora.getMonth() + 1) << 5) | ahora.getDate();
  const partes: Uint8Array[] = [];
  const directorio: Uint8Array[] = [];
  let desplazamiento = 0;
  for (const [ruta, texto] of archivos) {
    const nombre = cod.encode(ruta);
    const datos = cod.encode(texto);
    const crc = crc32(datos);
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true);
    local.setUint16(4, 20, true);
    local.setUint16(6, 0x0800, true);
    local.setUint16(8, 0, true);
    local.setUint16(10, hora, true);
    local.setUint16(12, dia, true);
    local.setUint32(14, crc, true);
    local.setUint32(18, datos.length, true);
    local.setUint32(22, datos.length, true);
    local.setUint16(26, nombre.length, true);
    local.setUint16(28, 0, true);
    partes.push(new Uint8Array(local.buffer), nombre, datos);
    const central = new DataView(new ArrayBuffer(46));
    central.setUint32(0, 0x02014b50, true);
    central.setUint16(4, 20, true);
    central.setUint16(6, 20, true);
    central.setUint16(8, 0x0800, true);
    central.setUint16(10, 0, true);
    central.setUint16(12, hora, true);
    central.setUint16(14, dia, true);
    central.setUint32(16, crc, true);
    central.setUint32(20, datos.length, true);
    central.setUint32(24, datos.length, true);
    central.setUint16(28, nombre.length, true);
    central.setUint32(42, desplazamiento, true);
    directorio.push(new Uint8Array(central.buffer), nombre);
    desplazamiento += 30 + nombre.length + datos.length;
  }
  const tamDirectorio = directorio.reduce((s, p) => s + p.length, 0);
  const fin = new DataView(new ArrayBuffer(22));
  fin.setUint32(0, 0x06054b50, true);
  fin.setUint16(8, archivos.length, true);
  fin.setUint16(10, archivos.length, true);
  fin.setUint32(12, tamDirectorio, true);
  fin.setUint32(16, desplazamiento, true);
  return unir([...partes, ...directorio, new Uint8Array(fin.buffer)]);
}

function unir(partes: Uint8Array[]): Uint8Array {
  const total = new Uint8Array(partes.reduce((s, p) => s + p.length, 0));
  let i = 0;
  for (const p of partes) {
    total.set(p, i);
    i += p.length;
  }
  return total;
}

// ---------------------------------------------------------------- PDF (Helvetica estándar, WinAnsi)

// Anchos de Helvetica y Helvetica-Bold (milésimas de em) para los caracteres 32 a 126.
const ANCHO_REGULAR = [
  278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556,
  556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
  667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556,
  556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
];
const ANCHO_NEGRITA = [
  278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556,
  556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
  667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611,
  611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584,
];
// WinAnsi fuera de Latin-1: código de Unicode -> byte.
const WIN_ANSI: Record<number, number> = {
  0x20ac: 0x80, 0x201a: 0x82, 0x0192: 0x83, 0x201e: 0x84, 0x2026: 0x85, 0x2020: 0x86, 0x2021: 0x87, 0x02c6: 0x88,
  0x2030: 0x89, 0x0160: 0x8a, 0x2039: 0x8b, 0x0152: 0x8c, 0x017d: 0x8e, 0x2018: 0x91, 0x2019: 0x92, 0x201c: 0x93,
  0x201d: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97, 0x02dc: 0x98, 0x2122: 0x99, 0x0161: 0x9a, 0x203a: 0x9b,
  0x0153: 0x9c, 0x017e: 0x9e, 0x0178: 0x9f,
};
const REEMPLAZOS: Record<string, string> = {
  "→": "->", "←": "<-", "≈": "~", "≤": "<=", "≥": ">=", "−": "-", "✓": "v",
  "✗": "x", " ": " ", " ": " ", "​": "",
};
const ANCHO_OTROS: Record<string, [number, number]> = {
  "¡": [333, 333], "¿": [611, 611], "°": [400, 400], "·": [278, 278], "«": [556, 556], "»": [556, 556], "–": [556, 556],
  "—": [1000, 1000], "…": [1000, 1000], "•": [350, 350], "€": [556, 556], "‘": [222, 278], "’": [222, 278],
  "“": [333, 500], "”": [333, 500], "×": [584, 584], "±": [584, 584], "ª": [370, 370], "º": [365, 365], " ": [278, 278],
};

function normalizarPdf(texto: string): string {
  let s = "";
  for (const ch of texto) {
    if (REEMPLAZOS[ch] !== undefined) s += REEMPLAZOS[ch];
    else {
      const c = ch.codePointAt(0) ?? 63;
      s += c < 256 || WIN_ANSI[c] ? ch : "?";
    }
  }
  return s;
}

function anchoTexto(texto: string, tam: number, negrita = false): number {
  const tabla = negrita ? ANCHO_NEGRITA : ANCHO_REGULAR;
  let total = 0;
  for (const ch of texto) {
    const c = ch.codePointAt(0) ?? 63;
    if (c >= 32 && c <= 126) total += tabla[c - 32];
    else if (ANCHO_OTROS[ch]) total += ANCHO_OTROS[ch][negrita ? 1 : 0];
    else {
      const base = ch.normalize("NFD").codePointAt(0) ?? 63;
      total += base >= 32 && base <= 126 ? tabla[base - 32] : 556;
    }
  }
  return (total * tam) / 1000;
}

function cadenaPdf(texto: string): string {
  let s = "(";
  for (const ch of texto) {
    const c = ch.codePointAt(0) ?? 63;
    if (ch === "(" || ch === ")" || ch === "\\") s += "\\" + ch;
    else if (c >= 32 && c <= 126) s += ch;
    else {
      const byte = c < 256 ? c : WIN_ANSI[c] ?? 63;
      s += "\\" + byte.toString(8).padStart(3, "0");
    }
  }
  return s + ")";
}

/** Texto del diccionario /Info en UTF-16BE (los metadatos no usan WinAnsi). */
function textoInfo(texto: string): string {
  let hex = "<FEFF";
  for (let i = 0; i < texto.length; i++) hex += texto.charCodeAt(i).toString(16).padStart(4, "0").toUpperCase();
  return hex + ">";
}

function recortar(texto: string, max: number, tam: number, negrita = false): string {
  if (anchoTexto(texto, tam, negrita) <= max) return texto;
  let s = texto;
  while (s.length > 1 && anchoTexto(s + "…", tam, negrita) > max) s = s.slice(0, -1);
  return s.trimEnd() + "…";
}

function partirLineas(texto: string, max: number, tam: number, negrita = false): string[] {
  const lineas: string[] = [];
  let actual = "";
  for (const palabra of texto.split(/\s+/).filter(Boolean)) {
    const prueba = actual ? `${actual} ${palabra}` : palabra;
    if (anchoTexto(prueba, tam, negrita) <= max || !actual) actual = prueba;
    else {
      lineas.push(actual);
      actual = palabra;
    }
  }
  if (actual) lineas.push(actual);
  return lineas.map((l) => recortar(l, max, tam, negrita));
}

type Color = [number, number, number];
const TINTA: Color = [0.09, 0.125, 0.2];
const GRIS: Color = [0.353, 0.392, 0.471];
const ROJO: Color = [0.784, 0.063, 0.18];
const FONDO_CAB: Color = [0.933, 0.945, 0.961];
const CEBRA: Color = [0.969, 0.973, 0.98];
const LINEA: Color = [0.804, 0.827, 0.867];
const c3 = (c: Color) => c.map((v) => v.toFixed(3)).join(" ");
const n2 = (v: number) => (Math.round(v * 100) / 100).toString();

function pdf(doc: Documento): Uint8Array {
  const tablas = doc.tablas.map((t) => ({
    ...t,
    celdas: t.filas.map((f) => t.columnas.map((c) => normalizarPdf(formatear(f[c.clave], c.tipo)))),
  }));
  const maxColumnas = Math.max(0, ...tablas.map((t) => t.columnas.length));
  const horizontal = maxColumnas > 6;
  const W = horizontal ? 841.89 : 595.28;
  const H = horizontal ? 595.28 : 841.89;
  const M = 40;
  const util = W - 2 * M;
  const paginas: string[][] = [];
  let ops: string[] = [];
  let y = 0;

  const texto = (s: string, x: number, yTop: number, tam: number, color: Color = TINTA, negrita = false) =>
    ops.push(`BT /${negrita ? "F2" : "F1"} ${tam} Tf ${c3(color)} rg ${n2(x)} ${n2(H - yTop)} Td ${cadenaPdf(s)} Tj ET`);
  const textoDerecha = (s: string, xDer: number, yTop: number, tam: number, color: Color = TINTA, negrita = false) =>
    texto(s, xDer - anchoTexto(s, tam, negrita), yTop, tam, color, negrita);
  const rect = (x: number, yTop: number, w: number, h: number, color: Color) =>
    ops.push(`${c3(color)} rg ${n2(x)} ${n2(H - yTop - h)} ${n2(w)} ${n2(h)} re f`);
  const linea = (x1: number, yTop: number, x2: number, color: Color = LINEA, grosor = 0.6) =>
    ops.push(`${c3(color)} RG ${grosor} w ${n2(x1)} ${n2(H - yTop)} m ${n2(x2)} ${n2(H - yTop)} l S`);

  const titulo = normalizarPdf(doc.titulo);
  const nuevaPagina = () => {
    ops = [];
    paginas.push(ops);
    if (paginas.length === 1) {
      rect(0, 0, W, 50, ROJO);
      texto("Cuota", M, 31, 17, [1, 1, 1], true);
      texto("Flex", M + anchoTexto("Cuota", 17, true), 31, 17, [1, 0.83, 0.855], true);
      textoDerecha("Caja Trujillo · Cajathón 2026", W - M, 30, 9, [1, 0.88, 0.9]);
      y = 82;
    } else {
      texto("CuotaFlex", M, 30, 9, ROJO, true);
      textoDerecha(recortar(titulo, util - 80, 9), W - M, 30, 9, GRIS);
      linea(M, 38, W - M, LINEA, 0.6);
      y = 62;
    }
  };
  const asegurar = (alto: number) => {
    if (y + alto > H - M - 18) {
      nuevaPagina();
      return true;
    }
    return false;
  };

  nuevaPagina();
  for (const l of partirLineas(titulo, util, 17, true)) {
    texto(l, M, y, 17, TINTA, true);
    y += 22;
  }
  if (doc.subtitulo) {
    for (const l of partirLineas(normalizarPdf(doc.subtitulo), util, 10.5)) {
      texto(l, M, y - 2, 10.5, GRIS);
      y += 15;
    }
  }
  texto(`Generado el ${marcaTiempo()}`, M, y + 2, 8.5, GRIS);
  y += 22;

  if (doc.resumen?.length) {
    const porFila = horizontal ? 4 : 3;
    const anchoCelda = util / porFila;
    doc.resumen.forEach((d, i) => {
      const col = i % porFila;
      if (col === 0) {
        if (i > 0) y += 34;
        asegurar(34);
      }
      const x = M + col * anchoCelda;
      texto(recortar(normalizarPdf(d.etiqueta), anchoCelda - 10, 8), x, y + 8, 8, GRIS);
      texto(recortar(normalizarPdf(formatear(d.valor, d.tipo)), anchoCelda - 10, 11.5, true), x, y + 24, 11.5, TINTA, true);
    });
    y += 46;
  }

  const tamFila = 8.5;
  const altoFila = 16;
  for (const t of tablas) {
    // Ancho de cada columna según su contenido, escalado para ocupar el ancho útil.
    const naturales = t.columnas.map((c, i) =>
      Math.min(Math.max(anchoTexto(normalizarPdf(c.titulo), tamFila, true), ...t.celdas.map((r) => anchoTexto(r[i], tamFila))) + 14, util * 0.45));
    const suma = naturales.reduce((s, v) => s + v, 0) || 1;
    const anchos = naturales.map((v) => (v * util) / suma);
    const xs = anchos.map((_, i) => M + anchos.slice(0, i).reduce((s, v) => s + v, 0));
    const cabecera = () => {
      rect(M, y, util, altoFila + 2, FONDO_CAB);
      t.columnas.forEach((c, i) => {
        const s = recortar(normalizarPdf(c.titulo), anchos[i] - 10, tamFila, true);
        if (numerico(c.tipo)) textoDerecha(s, xs[i] + anchos[i] - 6, y + 12, tamFila, [0.204, 0.247, 0.329], true);
        else texto(s, xs[i] + 6, y + 12, tamFila, [0.204, 0.247, 0.329], true);
      });
      y += altoFila + 2;
    };
    asegurar(34 + altoFila * 3);
    texto(normalizarPdf(t.titulo), M, y + 10, 11.5, TINTA, true);
    textoDerecha(`${t.filas.length} ${t.filas.length === 1 ? "fila" : "filas"}`, W - M, y + 10, 8.5, GRIS);
    y += 20;
    cabecera();
    t.celdas.forEach((r, j) => {
      if (asegurar(altoFila)) cabecera();
      if (j % 2 === 1) rect(M, y, util, altoFila, CEBRA);
      r.forEach((s, i) => {
        const v = recortar(s, anchos[i] - 10, tamFila);
        if (numerico(t.columnas[i].tipo)) textoDerecha(v, xs[i] + anchos[i] - 6, y + 11, tamFila);
        else texto(v, xs[i] + 6, y + 11, tamFila);
      });
      y += altoFila;
    });
    linea(M, y, W - M);
    y += 22;
  }

  for (const n of doc.notas ?? []) {
    for (const l of partirLineas(normalizarPdf(n), util, 8.5)) {
      asegurar(14);
      texto(l, M, y, 8.5, GRIS);
      y += 13;
    }
  }

  // Pie con número de página, ahora que se sabe el total.
  const total = paginas.length;
  paginas.forEach((p, i) => {
    ops = p;
    linea(M, H - M + 2, W - M, LINEA, 0.4);
    texto(normalizarPdf(NOTA_DATOS), M, H - M + 14, 7.5, GRIS);
    textoDerecha(`Página ${i + 1} de ${total}`, W - M, H - M + 14, 7.5, GRIS);
  });

  // Objetos: 1 catálogo, 2 páginas, 3 Helvetica, 4 Helvetica-Bold, 5 info, luego página y contenido por cada hoja.
  const objetos: string[] = [];
  const kids = paginas.map((_, i) => `${6 + i * 2} 0 R`).join(" ");
  objetos.push("<< /Type /Catalog /Pages 2 0 R >>");
  objetos.push(`<< /Type /Pages /Kids [${kids}] /Count ${total} >>`);
  objetos.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
  objetos.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
  const d = new Date();
  const fechaPdf = `D:${d.getFullYear()}${dos(d.getMonth() + 1)}${dos(d.getDate())}${dos(d.getHours())}${dos(d.getMinutes())}${dos(d.getSeconds())}`;
  objetos.push(`<< /Title ${textoInfo(doc.titulo)} /Creator (CuotaFlex) /Producer (CuotaFlex) /CreationDate (${fechaPdf}) >>`);
  paginas.forEach((p, i) => {
    const contenido = p.join("\n");
    objetos.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${W} ${H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${7 + i * 2} 0 R >>`);
    objetos.push(`<< /Length ${contenido.length} >>\nstream\n${contenido}\nendstream`);
  });
  let salida = "%PDF-1.4\n%âãÏÓ\n";
  const posiciones: number[] = [];
  objetos.forEach((o, i) => {
    posiciones.push(salida.length);
    salida += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = salida.length;
  salida += `xref\n0 ${objetos.length + 1}\n0000000000 65535 f \n`;
  salida += posiciones.map((p) => `${String(p).padStart(10, "0")} 00000 n \n`).join("");
  salida += `trailer\n<< /Size ${objetos.length + 1} /Root 1 0 R /Info 5 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  // Todo es ASCII salvo la línea binaria del encabezado: un byte por carácter.
  const bytes = new Uint8Array(salida.length);
  for (let i = 0; i < salida.length; i++) bytes[i] = salida.charCodeAt(i) & 0xff;
  return bytes;
}

// ---------------------------------------------------------------- Descarga

export function generar(doc: Documento, formato: Formato): Blob {
  const contenido: BlobPart =
    formato === "pdf" ? pdf(doc) : formato === "xlsx" ? xlsx(doc) : formato === "csv" ? csv(doc) : formato === "json" ? json(doc) : txt(doc);
  return new Blob([contenido], { type: MIME[formato] });
}

export function nombreArchivo(doc: Documento, formato: Formato): string {
  const base = doc.archivo
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "cuotaflex";
  return `cuotaflex-${base}-${iso(new Date())}.${formato}`;
}

/** Genera el archivo y lo descarga; devuelve el nombre usado. */
export function descargar(doc: Documento, formato: Formato): string {
  const nombre = nombreArchivo(doc, formato);
  const url = URL.createObjectURL(generar(doc, formato));
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.rel = "noopener";
  enlace.style.display = "none";
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
  return nombre;
}
