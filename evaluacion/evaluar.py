"""Evalúa el chat del asesor con casos sintéticos en modo local y con LLM simulado."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent / "src"))

from cuotaflex.agente_chat import SesionChat  # noqa: E402
from cuotaflex.agente_chat.llm import Llamada, RespuestaLLM, obtener_llm  # noqa: E402
from cuotaflex.api.routers.asesor import ClienteSolicitud  # noqa: E402
from cuotaflex.explicador import cifras_validas, cumple_politica  # noqa: E402

CIFRA_CON_UNIDAD = re.compile(
    r"(?P<moneda>S/\s*)?(?P<valor>[+\-−]?\d+(?:[.,]\d+)*)"
    r"(?:\s*(?P<unidad>%|puntos porcentuales|mes(?:es)?\b|aplazamientos?\b|escenarios?\b))?",
    re.IGNORECASE,
)
UNIDADES = {
    "mes": "meses",
    "aplazamiento": "aplazamientos",
    "escenario": "escenarios",
}
BORRADORES_INCORRECTOS = {
    "D01": "El nuevo monto es de S/ 999,999,997.13.",
    "D06": "El desembolso está garantizado.",
}


def _decimal(valor: str, unidad: str) -> Decimal:
    valor = valor.replace("−", "-")
    separador = "," if "," in valor else "."
    if "," in valor and "." in valor:
        separador = "," if valor.rfind(",") > valor.rfind(".") else "."
    if valor.count(separador) > 1 or (
        unidad == "soles" and len(valor.rpartition(separador)[2]) == 3 and separador in valor
        and ("," not in valor or "." not in valor)
    ):
        return Decimal(valor.replace(separador, ""))
    miles = "." if separador == "," else ","
    return Decimal(valor.replace(miles, "").replace(separador, "."))


def _cifras_clave_presentes(texto: str, esperadas: list[dict]) -> bool:
    presentes = set()
    for coincidencia in CIFRA_CON_UNIDAD.finditer(texto):
        unidad = "soles" if coincidencia["moneda"] else coincidencia["unidad"]
        if unidad:
            unidad = unidad.lower()
            presentes.add((_decimal(coincidencia["valor"], unidad), UNIDADES.get(unidad, unidad)))
    return all((Decimal(str(cifra["valor"])), cifra["unidad"]) in presentes for cifra in esperadas)


class LLMSimulado:
    """Solicita la herramienta prevista por la prueba y redacta a partir de su resultado."""

    def __init__(self, caso: dict, sesion: SesionChat):
        self.caso = caso
        self.sesion = sesion
        self.entrego_borrador_incorrecto = False

    def completar(self, *, sistema, mensajes, herramientas=None, plazo_fin=None) -> RespuestaLLM:
        if mensajes[-1]["role"] == "tool":
            resultado = json.loads(mensajes[-1]["content"])
            motivo = resultado["motivo"]
            borrador_incorrecto = BORRADORES_INCORRECTOS.get(self.caso["id"])
            if borrador_incorrecto:
                self.entrego_borrador_incorrecto = True
                motivo = f"{motivo} {borrador_incorrecto}"
            return RespuestaLLM(texto=f"Según el motor, {motivo[0].lower()}{motivo[1:]}")

        nombre = self.caso["esperado"]["herramienta"]
        argumentos = self._argumentos(nombre)
        return RespuestaLLM(llamadas=(Llamada("evaluacion", nombre, argumentos),))

    def _argumentos(self, herramienta: str) -> dict:
        pregunta = self.caso["pregunta"].casefold()
        if herramienta == "recalcular_propuesta":
            return {"plazo": int(re.search(r"(\d+) meses", pregunta)[1])}
        if herramienta == "consultar_politica":
            return {"tema": "el_nino" if "niño" in pregunta else "aplazamiento"}
        if herramienta == "explicar_paso_bitacora":
            bitacora = self.sesion.propuesta["bitacora"]
            pasos = [paso["paso"] for paso in bitacora]
            buscado = "producto"
            if "monto" in pregunta:
                buscado = "replanificar" if "replanificar" in pasos else "cronograma"
            return {"indice": len(pasos) - pasos[::-1].index(buscado)}
        return {}


def _ejecutar_casos(casos: list[dict], modo: str) -> list[dict]:
    resultados = []
    for caso in casos:
        sesion = SesionChat(ClienteSolicitud.model_validate(caso["cliente"]))
        stub = LLMSimulado(caso, sesion) if modo == "simulado" else None
        inicio = perf_counter()
        respuesta = sesion.responder(caso["pregunta"], usar_llm=modo != "local", cliente_llm=stub)
        ms = (perf_counter() - inicio) * 1000
        texto, esperado = respuesta["respuesta"], caso["esperado"]
        exactitud = (
            bool(sesion.evidencia_respuesta)
            and cifras_validas(texto, sesion.evidencia_respuesta)
            and _cifras_clave_presentes(texto, esperado["cifras"])
        )
        politica = cumple_politica(texto, requiere_tasa=False, requiere_costo=False)
        frases_permitidas = not any(
            re.search(r"(?<!\w)" + re.escape(frase) + r"(?!\w)", texto, re.IGNORECASE)
            for frase in esperado["frases_prohibidas"]
        )
        resultados.append({
            "id": caso["id"],
            "exactitud": exactitud,
            "herramienta": esperado["herramienta"] in respuesta["herramientas_usadas"],
            "cumplimiento": politica and frases_permitidas,
            "ms": ms,
            "fuente": respuesta["fuente"],
            "rechazo_capturado": (
                stub is not None and stub.entrego_borrador_incorrecto and respuesta["fuente"] == "plantilla"
                and exactitud and politica and frases_permitidas
            ),
            "tokens_entrada": sesion.uso_llm.get("tokens_entrada", 0),
            "tokens_salida": sesion.uso_llm.get("tokens_salida", 0),
        })
    return resultados


def _costo_medio(resultados: list[dict], modo: str, tarifas: tuple[float, float] | None) -> str:
    if modo != "real":
        return "USD 0.00"
    entrada = sum(fila["tokens_entrada"] for fila in resultados)
    salida = sum(fila["tokens_salida"] for fila in resultados)
    if not (entrada or salida):
        return "Sin consumo confirmado"
    if tarifas is None:
        return "Sin tarifa indicada"
    costo = (entrada * tarifas[0] + salida * tarifas[1]) / (1_000_000 * len(resultados))
    return f"USD {costo:.6f}"


def _reporte(casos: list[dict], corridas: dict[str, list[dict]], tarifas: tuple[float, float] | None) -> str:
    nombres = {"local": "Sin LLM", "simulado": "LLM simulado", "real": "LLM real"}
    criterios = ("exactitud", "herramienta", "cumplimiento")
    con_cifras_clave = sum(bool(caso["esperado"]["cifras"]) for caso in casos)
    lineas = [
        "# Evaluación del agente CuotaFlex",
        "",
        f"Se evaluaron {len(casos)} consultas con clientes sintéticos. {con_cifras_clave} casos exigen "
        "cifras concretas con unidad. En todos se verifica el respaldo de las cifras emitidas.",
        "",
        "| Modo | Casos | Exactitud de cifras | Herramienta correcta | Cumplimiento | "
        "Respuestas del LLM | p50 (ms) | p95 (ms) | Costo medio por consulta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for modo, filas in corridas.items():
        n = len(filas)
        porcentajes = " | ".join(f"{sum(f[clave] for f in filas) / n:.0%}" for clave in criterios)
        tiempos = [f["ms"] for f in filas]
        p50 = median(tiempos)
        p95 = quantiles(tiempos, n=100, method="inclusive")[94]
        llm = sum(f["fuente"] == "llm" for f in filas)
        lineas.append(
            f"| {nombres[modo]} | {n} | {porcentajes} | {llm}/{n} | {p50:.1f} | {p95:.1f} | "
            f"{_costo_medio(filas, modo, tarifas)} |"
        )

    rechazos = sum(fila["rechazo_capturado"] for fila in corridas["simulado"])
    lineas.extend([
        "",
        f"Los controles descartaron {rechazos} de {len(BORRADORES_INCORRECTOS)} borradores "
        "del LLM simulado con una cifra inventada o una garantía indebida. La respuesta de respaldo "
        "conservó las cifras esperadas y pasó los controles de cumplimiento.",
        "",
        "## Cómo se midió",
        "",
        "- **Exactitud.** Cada cifra debe estar respaldada por los resultados de las herramientas y cada cifra "
        "esperada debe aparecer con su unidad.",
        "- **Herramienta.** La lista de herramientas usadas debe incluir la esperada por el caso.",
        "- **Cumplimiento.** Se aplican las reglas del chat del asesor y las frases prohibidas del caso.",
        "- **Latencia.** Los percentiles miden el procesamiento del mensaje con la sesión ya iniciada.",
        "- **LLM simulado.** Las pruebas le indican la herramienta que debe solicitar. El orquestador ejecuta "
        "la llamada y el simulador redacta con los resultados. Su porcentaje de herramienta mide esa integración, "
        "mientras que la fila sin LLM mide el enrutamiento por palabras clave.",
        "- **Costo.** Los modos locales tienen costo de API de USD 0.00. En modo real se usan los tokens "
        "informados por el proveedor y las tarifas indicadas al ejecutar el análisis.",
        "",
    ])
    if "real" not in corridas:
        lineas.extend(["La ejecución registrada usa los dos modos locales.", ""])
    elif tarifas is not None:
        lineas.extend([
            f"Tarifas usadas por millón de tokens en modo real. Entrada USD {tarifas[0]:.4f}. "
            f"Salida USD {tarifas[1]:.4f}.",
            "",
        ])
    fallos = [
        f"- {nombres[modo]} · {fila['id']} · {criterio}"
        for modo, filas in corridas.items()
        for fila in filas
        for criterio in criterios
        if not fila[criterio]
    ]
    if fallos:
        lineas.extend(["## Casos pendientes", "", *fallos, ""])

    lineas.extend([
        "## Reproducir",
        "",
        "```bash",
        "python evaluacion/evaluar.py",
        "```",
        "",
        "Usa `--llm-real` con el proveedor y su clave configurados para añadir una corrida externa "
        "con los mismos casos sintéticos. Las opciones `--usd-por-millon-entrada` y "
        "`--usd-por-millon-salida` permiten calcular su costo.",
        "",
    ])
    return "\n".join(lineas)


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--llm-real", action="store_true", help="Ejecuta también con el proveedor configurado.")
    analizador.add_argument("--usd-por-millon-entrada", type=float)
    analizador.add_argument("--usd-por-millon-salida", type=float)
    argumentos = analizador.parse_args()
    valores = (argumentos.usd_por_millon_entrada, argumentos.usd_por_millon_salida)
    tarifas = None
    if any(valor is not None for valor in valores):
        if any(valor is None or valor < 0 or not math.isfinite(valor) for valor in valores):
            analizador.error("Indica ambas tarifas como valores no negativos.")
        tarifas = valores
    if argumentos.llm_real and obtener_llm(True) is None:
        analizador.error("Configura el proveedor y su clave para ejecutar con --llm-real.")

    casos = [json.loads(linea) for linea in (CARPETA / "casos.jsonl").read_text(encoding="utf-8").splitlines()]
    modos = ["local", "simulado"]
    if argumentos.llm_real:
        modos.append("real")
    corridas = {modo: _ejecutar_casos(casos, modo) for modo in modos}
    reporte = _reporte(casos, corridas, tarifas)
    (CARPETA / "REPORTE.md").write_text(reporte, encoding="utf-8")
    print(reporte)
    fallo_metricas = any(
        not (fila["exactitud"] and fila["herramienta"] and fila["cumplimiento"])
        for filas in corridas.values()
        for fila in filas
    )
    fallo_deteccion = sum(fila["rechazo_capturado"] for fila in corridas["simulado"]) != len(BORRADORES_INCORRECTOS)
    fallo_proveedor = argumentos.llm_real and not any(
        fila["tokens_entrada"] or fila["tokens_salida"] or fila["fuente"] == "llm"
        for fila in corridas["real"]
    )
    return int(fallo_metricas or fallo_deteccion or fallo_proveedor)


if __name__ == "__main__":
    raise SystemExit(main())
