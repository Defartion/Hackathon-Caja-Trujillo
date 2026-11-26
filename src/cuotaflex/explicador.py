"""Explicaciones del motor y verificación de las cifras generadas."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import json
import logging
import math
from numbers import Real
import re
from typing import Literal, TypedDict
import unicodedata

_LOG = logging.getLogger(__name__)

_CIFRA = re.compile(
    r"(?:(?P<signo_moneda>[+\-])?\s*(?P<moneda>(?:\bs/\.?|\bpen|[$€£¥])\s*))?"
    r"(?P<numero>(?:[+\-]\s*)?(?:\d{1,3}(?: \d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)*|[.,]\d+))"
    r"(?P<porcentaje>\s*(?:%|\bpor ciento\b|\bpuntos? porcentuales?\b|\bpp\b))?"
)
_CARDINAL_ESCRITO = re.compile(
    r"\b(?:cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|"
    r"trece|catorce|quince|dieci\w+|veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|"
    r"setenta|ochenta|noventa|cien|cientos?|[a-z]+cient[oa]s|quinient[oa]s|mil|"
    r"(?:m|b|tr)illon(?:es)?|decenas?|centenas?)\b|"
    r"\b(?:un|una)\s+(?:mes|dia|ano|sol|por ciento|punto porcentual)\b|"
    r"\b(?:hasta|solo|exactamente)\s+una\s+cuota\b|"
    r"\bmedi[oa]\s+(?:mes|dia|ano|cuota|sol)\b"
)
_TASA = r"tea|tcea|tem"
_TASA_ANTES = re.compile(
    rf"\b({_TASA})\b[\s():=,]*"
    r"(?:(?:es|de|base|anual|mensual|referencial|aplicada|vigente|pactada)\s+)*$"
)
_TASA_DESPUES = re.compile(rf"^[\s(]*(?:de\s+)?({_TASA})\b")
_PROMESA = re.compile(
    r"\b(?:pre)?aprob(?:ad\w*|acion\w*|ar\w*|amos)\b|"
    r"\bgarantiz\w*\b|\bgarantia de (?:resultado|pago|exito)\w*\b|"
    r"\b(?:sin|ningun) riesgo\b|\b(?:cero|0) (?:mora|riesgo)\b|"
    r"\bno (?:habra|tendras|existe) (?:ninguna? )?(?:riesgo|mora|atrasos?)\b|"
    r"\b(?:prestamo|credito|resultado|exito) asegurad\w*\b|"
    r"\b100\s*%\s*segur\w*\b|\briesgo (?:nulo|cero)\b|"
    r"\b(?:te otorgaremos|eliminara la mora|evitaras la mora|es seguro que)\b"
)
_COSTO = re.compile(
    r"\b(?:tiene(?:n)?|genera(?:n)?|implica(?:n)?|conlleva(?:n)?|tendra(?:n)?)\s+"
    r"(?:un |el )?(?:costo(?:s)?|interes(?:es)?|recargo(?:s)?)\b|"
    r"\b(?:se cobran?|se acumulan?|sigue\w* generando|se aplica\w*)\s+"
    r"(?:un |el )?(?:costo(?:s)?|interes(?:es)?|recargo(?:s)?)\b|"
    r"\b(?:con costo|con intereses|con recargo)\b"
)
_COSTO_NEGADO = re.compile(
    r"\b(?:sin\s+(?:costo(?:s)?|interes(?:es)?|recargo(?:s)?)|gratuit\w*)\b|"
    r"\bno\s+(?:tiene\w*|genera\w*|implica\w*|conlleva\w*|se cobra\w*)\s+"
    r"(?:un |el |ningun )?(?:costo(?:s)?|interes(?:es)?|recargo(?:s)?)\b"
)
_SESION_PRIVADA = {"cliente_id", "nombre", "explicacion"}
_TASAS = {"tea", "tcea", "tem"}
_UNIDADES = {"mes": "meses", "dia": "dias", "ano": "anos"}

# Fase 4 (FAQ del NEG-01): aplazar cuotas o pedir alivio de El Niño en un crédito vigente es reprogramación,
# fuera del alcance del reto. Las explicaciones no lo ofrecen; El Niño se evalúa al diseñar el plan.
MOSTRAR_CREDITO_VIGENTE = False
_OFRECE_REPROGRAMACION = re.compile(r"\baplaz\w*|\balivio\w*|\bpostergar\w*", re.IGNORECASE)


class Explicacion(TypedDict):
    texto: str
    fuente: Literal["llm", "plantilla"]
    cifras_verificadas: bool


def normalizar(texto: str) -> str:
    """Ignora acentos y normaliza separadores Unicode en las comprobaciones."""
    texto = unicodedata.normalize("NFKC", texto).casefold().replace("−", "-").replace("⁄", "/")
    return "".join(
        caracter for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter) and unicodedata.category(caracter) != "Cf"
    )


def cumple_politica(
    texto: str, *, requiere_tasa: bool = False, requiere_costo: bool = False,
) -> bool:
    """Exige divulgaciones específicas y descarta afirmaciones de certeza."""
    limpio = normalizar(texto)
    if not limpio.strip() or _PROMESA.search(limpio):
        return False
    if requiere_tasa and not any(_tipo_mencion(limpio, cita) in {"tea", "tcea"} for cita in _CIFRA.finditer(limpio)):
        return False
    return not requiere_costo or bool(_COSTO.search(limpio) and not _COSTO_NEGADO.search(limpio))


def _formato_numero(texto: str, tipo: str) -> tuple[float, int] | None:
    """Lee decimales con coma o punto y agrupaciones habituales de miles."""
    cifra = texto.lstrip("+-").lstrip()
    signo = "-" if texto.startswith("-") else ""
    for agrupador in (" ", ",", "."):
        patron = rf"\d{{1,3}}(?:{re.escape(agrupador)}\d{{3}})+"
        separador_decimal = r"[.,]" if agrupador == " " else re.escape("." if agrupador == "," else ",")
        agrupado = re.fullmatch(rf"{patron}(?:{separador_decimal}(\d+))?", cifra)
        if agrupado:
            decimales = agrupado.group(1) or ""
            if (not decimales and tipo in _TASAS | {"porcentaje", "puntos"}
                    and re.fullmatch(r"\d{1,3}[.,]\d{3}", cifra)):
                # En tasas, un solo separador seguido de tres dígitos puede ser decimal.
                break
            entero = cifra[:-len(decimales) - 1] if decimales else cifra
            return float(signo + entero.replace(agrupador, "") + "." + decimales), len(decimales)
    if not re.fullmatch(r"\d+(?:[.,]\d+)?|[.,]\d+", cifra):
        return None
    entero, _, decimales = cifra.replace(",", ".").partition(".")
    return float(signo + entero + "." + decimales), len(decimales)


def _tipo_mencion(texto: str, cifra: re.Match[str]) -> str:
    antes, despues = texto[:cifra.start()], texto[cifra.end():]
    moneda = cifra["moneda"]
    porcentaje = cifra["porcentaje"]
    if moneda:
        es_sol = moneda.strip().startswith(("s/", "pen"))
        return "monto" if es_sol and not (porcentaje or re.match(r"[\w/]", despues)) else "invalido"
    if porcentaje:
        etiqueta = _TASA_ANTES.search(antes) or _TASA_DESPUES.match(despues)
        if re.search(r"[a-z]", porcentaje) and "por ciento" not in porcentaje:
            return "puntos"
        return etiqueta.group(1) if etiqueta else "porcentaje"
    if re.search(r"\bp$", antes):
        return "percentil"
    if re.search(r"\bmora\s*$", antes):
        return "mora"
    if re.match(r"\s*(?:sol(?:es)?|pen)\b", despues):
        return "monto"
    unidad = re.match(r"\s*(mes|dia|ano)(?:es|s)?\b", despues)
    if unidad:
        return _UNIDADES[unidad.group(1)]
    if re.match(r"\s*(?:x|veces la cuota)\b", despues):
        return "multiplicador"
    if re.match(r"\s*escenarios?\b", despues):
        return "escenarios"
    if re.match(r"\s*aplazamientos?\b", despues):
        return "aplazamientos"
    if re.match(r"\s*(?:veces|cuotas?)\b", despues):
        if re.search(r"\b(?:aplaza\w*|posterga\w*|difiere\w*|diferir)\s+(?:hasta\s+)?$", antes):
            return "aplazamientos"
        return "cuotas"
    if re.search(r"\b(?:cuota|paso)\s*(?:n(?:[.°º])?\s*)?$", antes):
        return "indice"
    if re.search(r"[\w/]$", antes) or re.match(r"[\w/]", despues):
        return "invalido"
    return "numero"


def _tipo_campo(clave: str, anterior: str) -> str:
    if clave in _TASAS:
        return clave
    if "spread" in clave:
        return "puntos"
    if clave == "tea_base" or clave.endswith("_tea"):
        return "tea"
    if clave == "max_perdida_vpn_pct":
        return "porcentaje_puntos"
    if clave == "cuantil_conservador":
        return "cuantil"
    if (
        "_pct" in clave
        or any(palabra in clave for palabra in ("probabilidad", "ratio_", "cuota_excedente"))
        or clave in {"mora", "mora30", "default", "tasa", "caida_ingresos", "tolerancia_reduccion",
                     "fuga_caja_mensual", "recuperacion_default", "prob_atrasos", "peso_modelo"}
    ):
        return "porcentaje"
    if "meses" in clave or clave == "plazo":
        return "meses"
    if "dias" in clave:
        return "dias"
    if "anios" in clave or "anos" in clave:
        return "anos"
    if "aplazamientos" in clave:
        return "aplazamientos"
    if clave in {"escenarios", "n_escenarios"}:
        return "escenarios"
    if clave.startswith("n_") or clave == "cantidad":
        return "cantidad"
    if clave in {"numero", "indice", "cuota_afectada", "paso"}:
        return "indice"
    if "_mult" in clave or clave in {"ajuste_asesor", "factor_sigma"}:
        return "multiplicador"
    if any(
        palabra in clave
        for palabra in (
            "monto", "principal", "cuota", "costo", "vpn", "interes", "capital", "saldo", "deficit",
            "excedente", "incremento", "ventas", "diferido",
        )
    ):
        return "monto"
    return anterior


def _cifras_evidencia(evidencia: object) -> dict[str, set[float]]:
    cifras: dict[str, set[float]] = defaultdict(set)

    def recorrer(valor: object, tipo: str = "numero") -> None:
        if isinstance(valor, Mapping):
            for campo, dato in valor.items():
                clave = normalizar(str(campo))
                if clave in _SESION_PRIVADA:
                    continue
                if clave == "motivos" and isinstance(dato, (list, tuple)):
                    # Estos mensajes los construye la política del motor, no el usuario.
                    for motivo in dato:
                        limpio = normalizar(str(motivo))
                        for cita in _CIFRA.finditer(limpio):
                            unidad = _tipo_mencion(limpio, cita)
                            leido = _formato_numero(cita["numero"], unidad)
                            if leido and math.isfinite(leido[0]):
                                cifras[unidad].add(leido[0])
                    continue
                for percentil in re.findall(r"(?:^|_)p(\d+)(?:_|$)", clave):
                    cifras["percentil"].add(float(percentil))
                if clave == "mora30":
                    cifras["mora"].add(30)
                if clave in {"plazo", "meses_alivio"} and isinstance(dato, Real) and not isinstance(dato, bool):
                    cifras["cuotas"].add(float(dato))
                recorrer(dato, _tipo_campo(clave, tipo))
        elif isinstance(valor, (list, tuple)):
            for item in valor:
                recorrer(item, tipo)
        elif isinstance(valor, Real) and not isinstance(valor, bool) and math.isfinite(valor):
            if tipo in {"porcentaje", "tea", "tem", "tcea", "cuantil", "puntos"}:
                cifras["porcentaje"].add(float(valor) * 100)
                cifras[tipo].add(float(valor) * 100)
                if tipo == "cuantil":
                    cifras["percentil"].add(float(valor) * 100)
            elif tipo == "porcentaje_puntos":
                cifras["porcentaje"].add(float(valor))
            else:
                cifras["numero"].add(float(valor))
                cifras[tipo].add(float(valor))

    recorrer(evidencia)
    return cifras


def cifras_validas(texto: str, evidencia: object) -> bool:
    """Valida valores y unidades contra resultados estructurados del motor."""
    limpio = normalizar(texto)
    solo_palabras = _CIFRA.sub(" ", limpio)
    if _CARDINAL_ESCRITO.search(solo_palabras):
        return False
    disponibles = _cifras_evidencia(evidencia)
    if any(not disponibles[tasa] and re.search(rf"\b{tasa}\b", limpio) for tasa in ("tcea", "tem")):
        return False
    for cifra in _CIFRA.finditer(limpio):
        tipo = _tipo_mencion(limpio, cifra)
        signo = cifra["signo_moneda"] or ""
        if signo and cifra["numero"].startswith(("+", "-")):
            return False
        numero = _formato_numero(signo + cifra["numero"], tipo)
        if numero is None:
            return False
        valor, decimales = numero
        tolerancia = 1e-9
        if tipo in {"numero", "monto", "porcentaje", "tea", "tem", "tcea", "puntos", "multiplicador"}:
            tolerancia += 0.5 * 10 ** -decimales
        if not any(abs(valor - esperado) <= tolerancia for esperado in disponibles[tipo]):
            return False
    return True


def _soles(monto: float) -> str:
    return f"S/ {monto:,.2f}"


def _tasa(propuesta: dict) -> str:
    return f"{propuesta['tea']:.2%}".rstrip("%").rstrip("0").rstrip(".") + "%"


def _cuotas(propuesta: dict) -> tuple[float, float]:
    cuotas = [fila["cuota"] for fila in propuesta.get("cronograma", ())]
    if not cuotas:
        cuotas = [propuesta["cuota_fija_referencia"]]
    return min(cuotas), max(cuotas)


def _para_cliente(propuesta: dict, elegibilidad: dict) -> str:
    principal = propuesta["principal_aprobado"]
    solicitado = propuesta["principal_solicitado"]
    plazo = propuesta["plazo"]
    minima, maxima = _cuotas(propuesta)
    aplazamientos = propuesta.get("aplazamientos_disponibles", 0) if MOSTRAR_CREDITO_VIGENTE else 0
    alivio = propuesta.get("clausula_el_nino") and MOSTRAR_CREDITO_VIGENTE
    partes = [
        f"Te sugerimos un préstamo de {_soles(principal)} a {plazo} meses.",
        f"La tasa efectiva anual (TEA) es {_tasa(propuesta)}.",
    ]
    if propuesta["producto"] == "estacional":
        partes.append(f"Pagarías entre {_soles(minima)} y {_soles(maxima)} según la temporada de tu negocio.")
    else:
        partes.append(f"Tu cuota regular sería de {_soles(propuesta['cuota_fija_referencia'])}.")
    if aplazamientos and alivio:
        partes.append(
            f"Puedes aplazar hasta {aplazamientos} cuotas si estás al día o pedir alivio durante una alerta "
            "de El Niño, con intereses sobre el monto postergado en ambos casos."
        )
    elif aplazamientos:
        partes.append(
            f"Puedes aplazar hasta {aplazamientos} cuotas si estás al día y cada aplazamiento tiene costo "
            "porque el monto postergado genera intereses."
        )
    elif alivio:
        partes.append("Durante una alerta aplicable por El Niño puedes solicitar una cuota menor, "
                      "con intereses sobre el saldo que postergues.")
    if not propuesta.get("valido", True):
        partes.append("Revisa el cronograma con tu asesor porque necesita ajustes.")
    elif principal < solicitado:
        partes.append("Te sugerimos un monto menor al que pediste para que la cuota se ajuste mejor a tu presupuesto.")
    elif len(partes) < 4:
        if elegibilidad.get("sobreendeudado"):
            partes.append("Las cuotas regulares toman en cuenta tus deudas y el dinero que tienes disponible cada mes.")
        elif not elegibilidad.get("elegible_flex", True):
            partes.append("La opción de cuota regular toma en cuenta tus atrasos anteriores.")
        else:
            partes.append("Antes de decidir, revisa el cronograma con tu asesor.")
    return " ".join(partes)


def _para_asesor(propuesta: dict, elegibilidad: dict) -> str:
    producto = {
        "fija": "Cuota fija", "estacional": "Cuota estacional", "aplazamiento": "Cuota con aplazamiento",
    }.get(propuesta["producto"], propuesta["producto"])
    principal = propuesta["principal_aprobado"]
    solicitado = propuesta["principal_solicitado"]
    minima, maxima = _cuotas(propuesta)
    partes = [
        f"{producto} por {_soles(principal)} a {propuesta['plazo']} meses con TEA de {_tasa(propuesta)}.",
    ]
    if minima != maxima:
        partes.append(f"La modalidad se ajusta a la estacionalidad de los ingresos con cuotas entre "
                      f"{_soles(minima)} y {_soles(maxima)}.")
    if principal < solicitado:
        partes.append(f"Se reduce el monto solicitado de {_soles(solicitado)} por capacidad de pago.")
    for motivo in filter(None, elegibilidad.get("motivos", ())):
        if "inf%" in motivo:
            partes.append("El excedente libre no cubre la carga de deuda.")
        else:
            partes.append(motivo[0].upper() + motivo[1:] + ".")
    if MOSTRAR_CREDITO_VIGENTE and propuesta.get("aplazamientos_disponibles"):
        partes.append("Los aplazamientos tienen costo por intereses sobre el saldo postergado.")
    if MOSTRAR_CREDITO_VIGENTE and propuesta.get("clausula_el_nino"):
        partes.append("La cláusula de El Niño permite solicitar alivio con intereses ante una alerta aplicable.")
    if not propuesta.get("valido", True):
        partes.append("El cronograma requiere revisión por incumplimiento de parámetros de riesgo.")
    elif len(partes) == 1:
        partes.append("El cronograma cumple los límites de capacidad de pago y de variación de cuotas.")
    return " ".join(partes)


def _para_llm(valor: object) -> object:
    if isinstance(valor, Mapping):
        return {clave: _para_llm(dato) for clave, dato in valor.items() if clave not in _SESION_PRIVADA}
    if isinstance(valor, (list, tuple)):
        return [_para_llm(dato) for dato in valor]
    if isinstance(valor, Real) and not isinstance(valor, bool):
        if not math.isfinite(valor):
            return None
        return valor.item() if hasattr(valor, "item") else valor
    return valor


def explicar(
    propuesta: dict, elegibilidad: dict, audiencia: str = "cliente", usar_llm: bool | None = None,
) -> Explicacion:
    """Explica una propuesta y registra si una salida generada supera las salvaguardas."""
    if audiencia not in ("cliente", "asesor"):
        raise ValueError("audiencia debe ser cliente o asesor")
    es_cliente = audiencia == "cliente"
    borrador = _para_cliente(propuesta, elegibilidad) if es_cliente else _para_asesor(propuesta, elegibilidad)
    respaldo: Explicacion = {
        "texto": borrador, "fuente": "plantilla", "cifras_verificadas": True,
    }
    if usar_llm is False:
        return respaldo

    from .agente_chat.llm import obtener_llm

    try:
        llm = obtener_llm(usar_llm)
        if llm is None:
            return respaldo
        tono = (
            "Escribe 4 o 5 frases en español sencillo, tutea y muestra la TEA o TCEA."
            if es_cliente else
            "Escribe en español técnico y breve para un asesor, con los riesgos y motivos de la decisión."
        )
        salida = llm.completar(
            sistema=(
                f"Reescribe el borrador con los datos de la propuesta CuotaFlex. {tono} "
                "Usa dígitos para cantidades y explicita la unidad de cada cifra. "
                + ("Mantén el costo de aplazar cuando corresponda. " if MOSTRAR_CREDITO_VIGENTE else
                   "No ofrezcas aplazamientos ni alivios: el plan es fijo desde el desembolso. ")
                + "Evita afirmar aprobación, garantía o resultados futuros."
            ),
            mensajes=[{"role": "user", "content": json.dumps(
                {"propuesta": _para_llm(propuesta), "borrador": borrador}, ensure_ascii=False, allow_nan=False,
            )}],
        )
        texto = salida.texto.strip()
    except Exception as error:
        _LOG.info("Explicación con plantilla tras error del proveedor (%s)", type(error).__name__)
        return respaldo

    if (
        not salida.llamadas
        and cifras_validas(texto, propuesta)
        and cumple_politica(
            texto, requiere_tasa=es_cliente,
            requiere_costo=es_cliente and MOSTRAR_CREDITO_VIGENTE and bool(
                propuesta.get("aplazamientos_disponibles") or propuesta.get("clausula_el_nino")
            ),
        )
        and (MOSTRAR_CREDITO_VIGENTE or not _OFRECE_REPROGRAMACION.search(texto))
    ):
        return {"texto": texto, "fuente": "llm", "cifras_verificadas": True}
    _LOG.info("Explicación generada rechazada por las salvaguardas (cifras_verificadas=false)")
    respaldo["cifras_verificadas"] = False
    return respaldo
