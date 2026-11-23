"""Disparador ENFEN: estado oficial del sistema de alerta ante El Niño y La Niña costeros.

La Comisión Multisectorial ENFEN publica un comunicado oficial en PDF cada 15 días, más o menos. En la
primera página aparece el estado del sistema de alerta: "No Activo", "Vigilancia de El Niño Costero",
"Alerta de El Niño Costero" o sus equivalentes para La Niña.

Cómo se obtiene el último comunicado (`obtener_ultimo_comunicado`):
  1. Se lee la página de la colección de comunicados de cada fuente oficial (gob.pe/SENAMHI y
     enfen.imarpe.gob.pe) y se elige el comunicado más reciente que liste cualquiera de ellas.
  2. Se descarga ese PDF.
  3. Se extrae el texto con pypdf.
  4. Se reconoce el estado con expresiones regulares que no dependen de tildes, mayúsculas ni saltos
     de línea. Hay dos formatos: "Estado del sistema de alerta: Alerta de El Niño Costero" (hasta el
     N° 16-2026) y la línea suelta "Alerta de El Niño Costero" debajo de la fecha (desde el N° 17-2026).

`estado_actual()` guarda la lectura en `data/enfen_cache.json` durante 6 h. Si la red falla, devuelve la
última lectura marcada como desactualizada. Con `ENFEN_MODO=demo` (el valor por defecto) no se usa
internet: el estado lo fija `POST /alertas/enfen/demo`. Fuentes y URLs: `README_ENFEN.md`.
"""
from __future__ import annotations

import html as html_lib
import io
import json
import logging
import os
import re
import threading
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from itertools import count
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from ..config import RAIZ

log = logging.getLogger(__name__)

RUTA_CACHE = RAIZ / "data" / "enfen_cache.json"
VIGENCIA_CACHE = timedelta(hours=6)
ESPERA_TRAS_FALLO = timedelta(minutes=10)  # no reintenta en cada solicitud si la red está caída
TAMANO_MAXIMO_PDF = 20 * 1024 * 1024
TIEMPO_ESPERA = httpx.Timeout(20.0, connect=8.0)
AGENTE_HTTP = "Mozilla/5.0 (compatible; lector-enfen/1.0)"

URL_GOBPE = "https://www.gob.pe/institucion/senamhi/colecciones/1308-comunicados-enfen"
URL_IMARPE = "https://enfen.imarpe.gob.pe/comunicados/"
FUENTE_GOBPE = "gob.pe · SENAMHI"
FUENTE_IMARPE = "enfen.imarpe.gob.pe"


class EstadoAlerta(str, Enum):
    NO_ACTIVO = "NO_ACTIVO"
    VIGILANCIA_NINO = "VIGILANCIA_NINO"
    ALERTA_NINO = "ALERTA_NINO"
    VIGILANCIA_NINA = "VIGILANCIA_NINA"
    ALERTA_NINA = "ALERTA_NINA"

    @property
    def etiqueta(self) -> str:
        return ETIQUETAS[self]


ETIQUETAS = {
    EstadoAlerta.NO_ACTIVO: "No Activo",
    EstadoAlerta.VIGILANCIA_NINO: "Vigilancia de El Niño Costero",
    EstadoAlerta.ALERTA_NINO: "Alerta de El Niño Costero",
    EstadoAlerta.VIGILANCIA_NINA: "Vigilancia de La Niña Costera",
    EstadoAlerta.ALERTA_NINA: "Alerta de La Niña Costera",
}
MAGNITUDES = ("débil", "moderada", "fuerte", "extraordinaria")


class ErrorEnfen(Exception):
    """No se pudo obtener o interpretar un comunicado del ENFEN."""


class ComunicadoIlegible(ErrorEnfen):
    """La página o el PDF no tienen el formato esperado."""


class EnfenNoDisponible(ErrorEnfen):
    """No hay lectura oficial: la red falló y la caché está vacía."""


@dataclass(frozen=True)
class Comunicado:
    numero: str                  # "20-2026"
    fecha: date
    estado: EstadoAlerta
    magnitud: str | None         # débil, moderada, fuerte o extraordinaria, si el comunicado la menciona
    url_fuente: str
    obtenido_en: datetime
    titulo: str = ""             # "Comunicado Oficial ENFEN N° 20-2026"
    fuente: str = ""             # nombre de la fuente oficial
    advertencias: tuple[str, ...] = ()

    @property
    def orden(self) -> tuple[date, int, int]:
        """Clave para saber cuál de dos comunicados es el más reciente."""
        numero, anio = self.numero.split("-")
        return self.fecha, int(anio), int(numero)

    def a_dict(self) -> dict:
        return {"numero": self.numero, "titulo": self.titulo, "fecha": self.fecha.isoformat(),
                "estado": self.estado.value, "etiqueta": self.estado.etiqueta, "magnitud": self.magnitud,
                "fuente": self.fuente, "url_fuente": self.url_fuente,
                "obtenido_en": self.obtenido_en.isoformat(timespec="seconds"),
                "advertencias": list(self.advertencias)}

    @classmethod
    def desde_dict(cls, d: dict) -> Comunicado:
        return cls(numero=d["numero"], fecha=date.fromisoformat(d["fecha"]), estado=EstadoAlerta(d["estado"]),
                   magnitud=d.get("magnitud"), url_fuente=d["url_fuente"],
                   obtenido_en=_con_zona(datetime.fromisoformat(d["obtenido_en"])), titulo=d.get("titulo", ""),
                   fuente=d.get("fuente", ""), advertencias=tuple(d.get("advertencias", ())))


@dataclass(frozen=True)
class EstadoEnfen:
    """Estado vigente del sistema de alerta, tal como lo usa la API."""

    modo: str                        # "oficial" o "demo"
    estado: EstadoAlerta
    magnitud: str | None = None
    comunicado: Comunicado | None = None
    desde: date | None = None        # desde cuándo rige este estado, según nuestras lecturas
    leido_en: datetime | None = None
    desactualizado: bool = False
    error: str | None = None

    @property
    def activo(self) -> bool:
        """Solo la Alerta de El Niño Costero habilita el alivio de la cláusula."""
        return self.estado is EstadoAlerta.ALERTA_NINO

    @property
    def vigilancia(self) -> bool:
        """Vigilancia de El Niño Costero: aviso preventivo, sin alivio."""
        return self.estado is EstadoAlerta.VIGILANCIA_NINO

    def a_dict(self) -> dict:
        c = self.comunicado
        fecha = c.fecha if c else self.desde
        return {
            "modo": self.modo, "estado": self.estado.value, "etiqueta": self.estado.etiqueta,
            "activo": self.activo, "vigilancia": self.vigilancia, "magnitud": self.magnitud,
            "numero": c.numero if c else None, "titulo": c.titulo if c else None,
            "fecha": fecha.isoformat() if fecha else None,
            "fuente": c.fuente if c else "Modo demo", "url_fuente": c.url_fuente if c else None,
            "obtenido_en": self.leido_en.isoformat(timespec="seconds") if self.leido_en else None,
            "desde": self.desde.isoformat() if self.desde else None,
            "desactualizado": self.desactualizado, "error": self.error,
            "advertencias": list(c.advertencias) if c else [],
        }


@dataclass(frozen=True)
class Cambio:
    """Cambio del estado vigente. Lo reciben las funciones registradas con `suscribir`."""

    id: int
    anterior: EstadoAlerta
    actual: EstadoEnfen
    origen: str                      # "revisión manual", "tarea programada", "demo", "app del cliente"…
    fecha: datetime


# ---------------------------------------------------------------- lectura del PDF

def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con un solo espacio: así no importan las tildes ni los saltos de línea."""
    texto = texto.replace("­", "")
    texto = re.sub(r"([^\W\d_])-[ \t]*\r?\n[ \t]*([^\W\d_])", r"\1\2", texto)  # palabra cortada con guion
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def _frase(*palabras: str) -> str:
    return r"\s*".join(palabras)  # pypdf a veces junta palabras ("ElNiño") o las separa en dos líneas


_FRASES_ESTADO = {
    EstadoAlerta.VIGILANCIA_NINO: _frase("vigilancia", "de", "el", "nino", "costero"),
    EstadoAlerta.ALERTA_NINO: _frase("alerta", "de", "el", "nino", "costero"),
    EstadoAlerta.VIGILANCIA_NINA: _frase("vigilancia", "de", "la", "nina", "costera"),
    EstadoAlerta.ALERTA_NINA: _frase("alerta", "de", "la", "nina", "costera"),
    EstadoAlerta.NO_ACTIVO: _frase("no", "activo"),
}
_ESTADO = ("(?<![a-z])(?:" + "|".join(f"(?P<{e.value}>{p})" for e, p in _FRASES_ESTADO.items())
           + ")(?![a-z])")  # admite la llamada a nota pegada: "Costero1"
# Hasta el N° 16-2026: "Estado del sistema de alerta: Alerta de El Niño Costero"
_RE_ETIQUETA = re.compile(r"estado\s*del\s*sistema\s*de\s*alerta\s*[:.\-]?\s*[\"'“”«»]?\s*" + _ESTADO)
# Desde el N° 17-2026: la línea "Alerta de El Niño Costero" justo debajo del número y la fecha
_RE_ESTADO = re.compile(_ESTADO)
_VENTANA_ESTADO = 250  # caracteres después del número del comunicado

_RE_NUMERO = re.compile(
    r"comunicado\s*(?:(?P<tipo>oficial|extraordinario)\s*)?(?:del?\s*)?enfen\s*n\s*(?:ro)?\s*[°o.]*\s*"
    r"(?P<num>\d{1,2})\s*-\s*(?P<anio>20\d{2})")
_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "setiembre": 9, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_RE_FECHA = re.compile(r"(?P<dia>\d{1,2})\s*(?:de\s*)?(?P<mes>" + "|".join(_MESES)
                       + r")\s*,?\s*(?:del?\s*)?(?P<anio>20\d{2})")
_RE_MAGNITUD = re.compile(
    r"magnitud(?:es)?\s*(?:mas\s*probables?\s*)?(?:de\s*)?(?:entre\s*)?(?:(?:frias?|frios?|calidas?|calidos?)\s*)?"
    r"(?P<m>debil|moderada|fuerte|extraordinaria)(?![a-z])"
    r"|evento\s*(?:frio|calido)\s*(?P<m2>debil|moderado|fuerte|extraordinario)(?![a-z])")
_MAGNITUD = {"debil": "débil", "moderada": "moderada", "moderado": "moderada", "fuerte": "fuerte",
             "extraordinaria": "extraordinaria", "extraordinario": "extraordinaria"}


def interpretar_texto(texto: str, *, url_fuente: str, fuente: str = "", fecha_publicacion: date | None = None,
                      obtenido_en: datetime | None = None) -> Comunicado:
    """Reconoce número, fecha, estado y magnitud en el texto de la primera página de un comunicado."""
    obtenido_en = obtenido_en or _ahora()
    t = normalizar(texto)
    m_numero = _RE_NUMERO.search(t)
    if m_numero is None:
        raise ComunicadoIlegible("No se encontró el número del comunicado.")
    fin = m_numero.end()
    m_estado = _RE_ETIQUETA.search(t) or _RE_ESTADO.search(t, fin, fin + _VENTANA_ESTADO)
    if m_estado is None:
        raise ComunicadoIlegible("No se encontró el estado del sistema de alerta.")
    estado = EstadoAlerta(next(nombre for nombre, valor in m_estado.groupdict().items() if valor))
    advertencias: list[str] = []
    fecha = _fecha_del_comunicado(t, fin, int(m_numero["anio"]), fecha_publicacion, obtenido_en.date(),
                                  advertencias)
    magnitud = None
    if estado is not EstadoAlerta.NO_ACTIVO:
        m_magnitud = _RE_MAGNITUD.search(t, m_estado.end())
        if m_magnitud:
            magnitud = _MAGNITUD[m_magnitud["m"] or m_magnitud["m2"]]
    numero = f"{int(m_numero['num']):02d}-{m_numero['anio']}"
    tipo = "Extraordinario" if m_numero["tipo"] == "extraordinario" else "Oficial"
    return Comunicado(numero=numero, fecha=fecha, estado=estado, magnitud=magnitud, url_fuente=url_fuente,
                      obtenido_en=obtenido_en, titulo=f"Comunicado {tipo} ENFEN N° {numero}", fuente=fuente,
                      advertencias=tuple(advertencias))


def _fecha_del_comunicado(t: str, desde: int, anio_numero: int, fecha_publicacion: date | None, hoy: date,
                          advertencias: list[str]) -> date:
    m = _RE_FECHA.search(t, desde, desde + 60)
    if m is None:
        if fecha_publicacion is None:
            raise ComunicadoIlegible("No se encontró la fecha del comunicado.")
        advertencias.append("El PDF no trae una fecha legible; se usó la fecha de publicación.")
        return fecha_publicacion
    try:
        fecha = date(int(m["anio"]), _MESES[m["mes"]], int(m["dia"]))
    except ValueError as e:
        raise ComunicadoIlegible(f"Fecha inválida en el comunicado: «{m.group(0)}».") from e
    if fecha > hoy and fecha.year != anio_numero:
        # Errata real: el N° 17-2026 dice "28 septiembre 2027". Se corrige con el año del número.
        try:
            corregida = fecha.replace(year=anio_numero)
        except ValueError:  # 29 de febrero
            corregida = fecha_publicacion or fecha
        advertencias.append(f"El PDF dice «{m.group(0)}», una fecha futura; se usó {corregida.isoformat()} "
                            "(año del número del comunicado).")
        return corregida
    return fecha


def texto_del_pdf(datos: bytes, paginas: int = 1) -> str:
    """Texto de las primeras páginas del PDF."""
    try:
        from pypdf import PdfReader
    except ImportError as e:  # dependencia del lote C: requirements-lote-c-enfen.txt
        raise ErrorEnfen("Falta pypdf: pip install -r requirements-lote-c-enfen.txt") from e
    if b"%PDF" not in datos[:1024]:
        raise ComunicadoIlegible("La descarga no es un PDF.")
    try:
        lector = PdfReader(io.BytesIO(datos))
        return "\n".join(pagina.extract_text() or "" for pagina in lector.pages[:paginas])
    except Exception as e:  # pypdf lanza varios tipos de error con archivos dañados
        raise ComunicadoIlegible(f"No se pudo leer el PDF: {e}") from e


def interpretar_pdf(datos: bytes, **datos_fuente) -> Comunicado:
    """El estado está en la primera página; si no aparece ahí, se prueba con las dos primeras."""
    try:
        return interpretar_texto(texto_del_pdf(datos, 1), **datos_fuente)
    except ComunicadoIlegible:
        return interpretar_texto(texto_del_pdf(datos, 2), **datos_fuente)


# ---------------------------------------------------------------- fuentes oficiales

@dataclass(frozen=True)
class Candidato:
    """Comunicado listado en una fuente, antes de descargar su PDF."""

    numero: int
    anio: int
    fecha: date | None
    url: str  # ficha con el enlace al PDF (gob.pe) o descarga directa (IMARPE)

    @property
    def orden(self) -> tuple[date, int, int]:
        return self.fecha or date.min, self.anio, self.numero


_RE_ENLACE = re.compile(r'<a\b[^>]*?\bhref="(?P<href>[^"]+)"[^>]*>(?P<texto>.*?)</a>', re.I | re.S)


def _texto_plano(fragmento: str) -> str:
    return normalizar(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragmento)))


def _fecha_previa(html: str, posicion: int) -> date | None:
    """Última fecha escrita antes de un enlace (la de su tarjeta en el listado)."""
    fechas = list(_RE_FECHA.finditer(_texto_plano(html[max(0, posicion - 400):posicion])))
    if not fechas:
        return None
    m = fechas[-1]
    try:
        return date(int(m["anio"]), _MESES[m["mes"]], int(m["dia"]))
    except ValueError:
        return None


def candidatos_gobpe(html: str, base: str) -> list[Candidato]:
    """Tarjetas de la colección "Comunicados oficiales del ENFEN" de gob.pe (más reciente primero)."""
    candidatos: dict[str, Candidato] = {}
    for m in _RE_ENLACE.finditer(html):
        href = html_lib.unescape(m["href"])
        if "informes-publicaciones" not in href or "comunicado" not in href.lower():
            continue
        numero = re.search(r"enfen-n-?(\d{1,2})-(20\d{2})", href, re.I) or re.search(
            r"n\D{0,3}(\d{1,2})\s*-\s*(20\d{2})", _texto_plano(m["texto"]))
        if numero:
            url = urljoin(base, href)
            candidatos.setdefault(url, Candidato(int(numero[1]), int(numero[2]), _fecha_previa(html, m.start()), url))
    return list(candidatos.values())


def pdf_en_ficha(html: str, base: str) -> str:
    """Enlace al PDF dentro de la ficha de un comunicado en gob.pe."""
    enlaces = [html_lib.unescape(h) for h in re.findall(r'href="([^"]+?\.pdf(?:\?[^"]*)?)"', html, re.I)]
    if not enlaces:
        raise ComunicadoIlegible("La ficha del comunicado no tiene un PDF.")
    preferidos = [e for e in enlaces if "enfen" in e.lower() or "comunicado" in e.lower()]
    return urljoin(base, (preferidos or enlaces)[0])


def candidatos_imarpe(html: str, base: str) -> list[Candidato]:
    """Enlaces de descarga directa ("Ver Comunicado") de enfen.imarpe.gob.pe/comunicados."""
    candidatos: dict[str, Candidato] = {}
    patron = r'href="(?P<href>[^"]*/download/comunicado[^"]*?enfen-n-?(?P<num>\d{1,2})-(?P<anio>20\d{2})[^"]*)"'
    for m in re.finditer(patron, html, re.I):
        href = html_lib.unescape(m["href"])
        if "wpdmdl=" in href:  # solo los enlaces que entregan el PDF
            url = urljoin(base, href)
            candidatos.setdefault(url, Candidato(int(m["num"]), int(m["anio"]), _fecha_previa(html, m.start()), url))
    return list(candidatos.values())


def _sin_consulta(url: str) -> str:
    """La descarga de IMARPE lleva un token temporal; para mostrar se usa la página estable."""
    partes = urlsplit(url)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))


@dataclass(frozen=True)
class Fuente:
    nombre: str
    url: str
    candidatos: Callable[[str, str], list[Candidato]]
    con_ficha: bool                    # el candidato apunta a una ficha que enlaza el PDF
    url_publica: Callable[[str], str] = lambda url: url


FUENTES = (
    Fuente(FUENTE_GOBPE, URL_GOBPE, candidatos_gobpe, con_ficha=True),
    Fuente(FUENTE_IMARPE, URL_IMARPE, candidatos_imarpe, con_ficha=False, url_publica=_sin_consulta),
)


def nuevo_cliente_http() -> httpx.Client:
    return httpx.Client(timeout=TIEMPO_ESPERA, follow_redirects=True, headers={"User-Agent": AGENTE_HTTP})


@contextmanager
def _cliente_http(cliente: httpx.Client | None) -> Iterator[httpx.Client]:
    if cliente is not None:
        yield cliente
        return
    with nuevo_cliente_http() as http:
        yield http


def _pedir(http: httpx.Client, url: str) -> httpx.Response:
    respuesta = http.get(url)
    respuesta.raise_for_status()
    return respuesta


def _descargar_pdf(http: httpx.Client, url: str) -> bytes:
    with http.stream("GET", url) as respuesta:
        respuesta.raise_for_status()
        partes, total = [], 0
        for bloque in respuesta.iter_bytes():
            total += len(bloque)
            if total > TAMANO_MAXIMO_PDF:
                raise ComunicadoIlegible("El PDF supera el tamaño máximo permitido.")
            partes.append(bloque)
    return b"".join(partes)


def _motivo(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}"
    if isinstance(error, httpx.TimeoutException):
        return "tiempo de espera agotado"
    if isinstance(error, httpx.HTTPError):
        return f"sin conexión ({type(error).__name__})"
    return str(error)


def obtener_ultimo_comunicado(cliente: httpx.Client | None = None) -> Comunicado:
    """Último comunicado oficial: consulta todas las fuentes y descarga el más reciente que listen.

    Si la descarga del más reciente falla, prueba con lo que liste la otra fuente.
    """
    errores: list[str] = []
    with _cliente_http(cliente) as http:
        listados = []
        for prioridad, fuente in enumerate(FUENTES):
            try:
                pagina = _pedir(http, fuente.url)
                candidatos = fuente.candidatos(pagina.text, str(pagina.url))
                if not candidatos:
                    raise ComunicadoIlegible("la página no lista comunicados")
                listados.append((max(candidatos, key=lambda c: c.orden), prioridad, fuente))
            except Exception as e:  # una fuente caída no debe impedir leer la otra
                if not isinstance(e, (httpx.HTTPError, ErrorEnfen)):
                    log.exception("Error inesperado al leer %s", fuente.nombre)
                errores.append(f"{fuente.nombre}: {_motivo(e)}")
        # Primero el comunicado más reciente; si dos fuentes listan el mismo, gana la de mayor prioridad.
        listados.sort(key=lambda x: (x[0].orden, -x[1]), reverse=True)
        for candidato, _, fuente in listados:
            try:
                url_pdf = candidato.url
                if fuente.con_ficha:
                    ficha = _pedir(http, candidato.url)
                    url_pdf = pdf_en_ficha(ficha.text, str(ficha.url))
                return interpretar_pdf(_descargar_pdf(http, url_pdf), url_fuente=fuente.url_publica(url_pdf),
                                       fuente=fuente.nombre, fecha_publicacion=candidato.fecha)
            except Exception as e:
                if not isinstance(e, (httpx.HTTPError, ErrorEnfen)):
                    log.exception("Error inesperado al interpretar el comunicado de %s", fuente.nombre)
                errores.append(f"{fuente.nombre} (N° {candidato.numero:02d}-{candidato.anio}): {_motivo(e)}")
    raise ErrorEnfen("No se pudo leer el último comunicado del ENFEN. " + "; ".join(errores))


# ---------------------------------------------------------------- estado vigente, caché y modo demo

@dataclass(frozen=True)
class _Lectura:
    comunicado: Comunicado
    leido_en: datetime
    desde: date


_lock = threading.RLock()
_lock_lectura = threading.Lock()  # una sola descarga a la vez
_demo: dict = {"estado": EstadoAlerta.NO_ACTIVO, "magnitud": None, "desde": None}
_suscriptores: list[Callable[[Cambio], None]] = []
_ids_cambio = count(1)
_ultimo_fallo: datetime | None = None
_ultimo_error: str | None = None
_interruptor_visto: dict | None = None


def _ahora() -> datetime:
    return datetime.now().astimezone()


def _con_zona(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.astimezone()


def modo() -> str:
    """`ENFEN_MODO=oficial` lee el comunicado real. Sin la variable (o con otro valor) se usa el modo demo."""
    return "oficial" if os.getenv("ENFEN_MODO", "demo").strip().lower() == "oficial" else "demo"


def suscribir(funcion: Callable[[Cambio], None]) -> None:
    """Registra una función que se llama cada vez que cambia el estado vigente, en cualquier modo."""
    with _lock:
        if funcion not in _suscriptores:
            _suscriptores.append(funcion)


def _avisar(cambio: Cambio) -> None:
    for funcion in list(_suscriptores):
        try:
            funcion(cambio)
        except Exception:  # un suscriptor con errores no debe impedir el cambio de estado
            log.exception("Error al procesar el cambio de estado del ENFEN")


def _leer_cache() -> _Lectura | None:
    try:
        d = json.loads(RUTA_CACHE.read_text(encoding="utf-8"))
        return _Lectura(Comunicado.desde_dict(d["comunicado"]), _con_zona(datetime.fromisoformat(d["leido_en"])),
                        date.fromisoformat(d["desde"]))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning("Caché del ENFEN ilegible (%s); se ignora.", e)
        return None


def _guardar_cache(lectura: _Lectura) -> None:
    contenido = {"version": 1, "comunicado": lectura.comunicado.a_dict(),
                 "leido_en": lectura.leido_en.isoformat(timespec="seconds"), "desde": lectura.desde.isoformat()}
    RUTA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporal = RUTA_CACHE.with_suffix(".tmp")
    temporal.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, RUTA_CACHE)


def _desde_lectura(lectura: _Lectura, *, desactualizado: bool = False, error: str | None = None) -> EstadoEnfen:
    c = lectura.comunicado
    return EstadoEnfen("oficial", c.estado, c.magnitud, c, lectura.desde, lectura.leido_en, desactualizado, error)


def _registrar_lectura(nuevo: Comunicado, anterior: _Lectura | None) -> _Lectura:
    if anterior is not None and nuevo.orden < anterior.comunicado.orden:
        log.warning("La fuente devolvió el N° %s, más antiguo que el N° %s de la caché; se conserva el último.",
                    nuevo.numero, anterior.comunicado.numero)
        nuevo = anterior.comunicado
    mismo_estado = anterior is not None and anterior.comunicado.estado is nuevo.estado
    lectura = _Lectura(nuevo, _ahora(), anterior.desde if mismo_estado else nuevo.fecha)
    _guardar_cache(lectura)
    return lectura


def _estado_oficial(*, forzar: bool, origen: str, cliente: httpx.Client | None) -> tuple[EstadoEnfen, Cambio | None]:
    global _ultimo_fallo, _ultimo_error
    lectura = _leer_cache()
    ahora = _ahora()
    if not forzar and lectura is not None:
        if ahora - lectura.leido_en < VIGENCIA_CACHE:
            return _desde_lectura(lectura), None
        if _ultimo_fallo is not None and ahora - _ultimo_fallo < ESPERA_TRAS_FALLO:
            return _desde_lectura(lectura, desactualizado=True, error=_ultimo_error), None
    # Quien solo consulta y ya tiene caché no espera a que otra solicitud termine de descargar.
    if not _lock_lectura.acquire(blocking=forzar or lectura is None):
        return _desde_lectura(lectura, desactualizado=ahora - lectura.leido_en >= VIGENCIA_CACHE), None
    try:
        anterior = _leer_cache()
        if not forzar and anterior is not None and _ahora() - anterior.leido_en < VIGENCIA_CACHE:
            return _desde_lectura(anterior), None  # otra solicitud la refrescó mientras esperábamos
        try:
            nuevo = obtener_ultimo_comunicado(cliente)
        except ErrorEnfen as e:
            _ultimo_fallo, _ultimo_error = _ahora(), str(e)
            log.warning("ENFEN sin respuesta; se usa la caché. %s", e)
            if anterior is None:
                raise EnfenNoDisponible(f"No hay lectura del ENFEN: la red falló y la caché está vacía. {e}") from e
            return _desde_lectura(anterior, desactualizado=True, error=str(e)), None
        _ultimo_fallo = _ultimo_error = None
        lectura = _registrar_lectura(nuevo, anterior)
    finally:
        _lock_lectura.release()
    estado = _desde_lectura(lectura)
    # La primera lectura es la línea base: sin estado previo no hay cambio que avisar.
    if anterior is None or anterior.comunicado.estado is estado.estado:
        return estado, None
    cambio = Cambio(next(_ids_cambio), anterior.comunicado.estado, estado, origen, _ahora())
    _avisar(cambio)
    return estado, cambio


def _estado_demo() -> EstadoEnfen:
    with _lock:
        return EstadoEnfen("demo", _demo["estado"], _demo["magnitud"], desde=_demo["desde"])


def estado_actual(*, cliente: httpx.Client | None = None) -> EstadoEnfen:
    """Estado vigente. En modo oficial usa la caché de 6 h; si la red falla, la marca como desactualizada.

    Lanza EnfenNoDisponible si no hay internet ni caché (solo en modo oficial).
    """
    if modo() == "demo":
        return _estado_demo()
    return _estado_oficial(forzar=False, origen="lectura", cliente=cliente)[0]


def revisar(*, origen: str = "revisión manual", cliente: httpx.Client | None = None) -> tuple[EstadoEnfen, Cambio | None]:
    """Fuerza una lectura del comunicado oficial. En modo demo devuelve el estado fijado."""
    if modo() == "demo":
        return _estado_demo(), None
    return _estado_oficial(forzar=True, origen=origen, cliente=cliente)


def fijar_demo(estado: EstadoAlerta | str, magnitud: str | None = None, *,
               origen: str = "demo") -> tuple[EstadoEnfen, Cambio | None]:
    """Fija el estado del modo demo (para mostrar el cambio en vivo)."""
    estado = EstadoAlerta(estado)
    if magnitud is not None and magnitud not in MAGNITUDES:
        raise ValueError(f"magnitud debe ser una de {MAGNITUDES}")
    if estado is EstadoAlerta.NO_ACTIVO:
        magnitud = None
    with _lock:
        anterior = _demo["estado"]
        if estado is not anterior:
            _demo["desde"] = _ahora().date()
        _demo.update(estado=estado, magnitud=magnitud)
        actual = _estado_demo()
    if estado is anterior:
        return actual, None
    cambio = Cambio(next(_ids_cambio), anterior, actual, origen, _ahora())
    _avisar(cambio)
    return actual, cambio


def sincronizar_interruptor(interruptor: dict) -> None:
    """Puente con el interruptor de la fase 1 (POST /cliente/el-nino) en modo demo.

    Ese endpoint guarda {"activo", "desde", "fuente"} en un dict nuevo cada vez que cambia la alerta. Si el
    dict es distinto del último visto, alguien movió el interruptor: activo pasa a ALERTA_NINO e inactivo a
    NO_ACTIVO. El primero que se ve es la línea base y no cambia nada.
    """
    global _interruptor_visto
    with _lock:
        movido = _interruptor_visto is not None and interruptor is not _interruptor_visto
        _interruptor_visto = interruptor
    if movido:
        fijar_demo(EstadoAlerta.ALERTA_NINO if interruptor.get("activo") else EstadoAlerta.NO_ACTIVO,
                   origen="app del cliente")


def reiniciar() -> None:
    """Estado inicial (pruebas): demo en NO_ACTIVO y sin fallos de red recordados."""
    global _ultimo_fallo, _ultimo_error, _interruptor_visto
    with _lock:
        _demo.update(estado=EstadoAlerta.NO_ACTIVO, magnitud=None, desde=None)
        _ultimo_fallo = _ultimo_error = None
        _interruptor_visto = None
