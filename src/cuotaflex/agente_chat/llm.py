"""Adaptadores de los proveedores opcionales de CuotaFlex."""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from time import monotonic

import httpx

TIEMPO_MAXIMO = 8.0


@dataclass(frozen=True)
class Llamada:
    id: str
    nombre: str
    argumentos: dict


@dataclass(frozen=True)
class RespuestaLLM:
    texto: str = ""
    llamadas: tuple[Llamada, ...] = ()
    tokens_entrada: int = 0
    tokens_salida: int = 0


@dataclass(frozen=True)
class ClienteLLM:
    proveedor: str
    modelo: str
    clave: str = field(repr=False)

    def completar(self, *, sistema: str, mensajes: list[dict], herramientas: list[dict] | None = None,
                  plazo_fin: float | None = None) -> RespuestaLLM:
        if plazo_fin is None:
            plazo_fin = monotonic() + TIEMPO_MAXIMO
        if self.proveedor == "anthropic":
            return self._anthropic(sistema, mensajes, herramientas, plazo_fin)
        return self._openai(sistema, mensajes, herramientas, plazo_fin)

    @staticmethod
    def _enviar(url: str, cabeceras: dict, cuerpo: dict, plazo_fin: float) -> dict:
        async def enviar(restante: float) -> dict:
            async with httpx.AsyncClient(timeout=restante) as cliente:
                respuesta = await cliente.post(url, headers=cabeceras, json=cuerpo)
                respuesta.raise_for_status()
                return respuesta.json()

        restante = plazo_fin - monotonic()
        if restante <= 0:
            raise TimeoutError("Se agotó el tiempo del proveedor")
        return asyncio.run(asyncio.wait_for(enviar(restante), timeout=restante))

    def _anthropic(self, sistema, mensajes, herramientas, plazo_fin):
        historial = []
        for mensaje in mensajes:
            rol, texto = mensaje["role"], mensaje["content"]
            if rol == "tool":
                bloque = {"type": "tool_result", "tool_use_id": mensaje["tool_call_id"], "content": texto}
                if historial and historial[-1]["role"] == "user" and isinstance(historial[-1]["content"], list):
                    historial[-1]["content"].append(bloque)
                else:
                    historial.append({"role": "user", "content": [bloque]})
            elif rol == "assistant":
                bloques = [{"type": "text", "text": texto}] if texto.strip() else []
                bloques.extend({"type": "tool_use", "id": llamada.id, "name": llamada.nombre,
                                "input": llamada.argumentos} for llamada in mensaje.get("llamadas", ()))
                historial.append({"role": rol, "content": bloques})
            else:
                historial.append({"role": rol, "content": texto})

        cuerpo = {"model": self.modelo, "max_tokens": 450, "temperature": 0.1,
                  "system": sistema, "messages": historial}
        if herramientas:
            cuerpo["tools"] = herramientas
        salida = self._enviar("https://api.anthropic.com/v1/messages",
                              {"x-api-key": self.clave, "anthropic-version": "2023-06-01"}, cuerpo, plazo_fin)
        uso = salida.get("usage", {})
        return RespuestaLLM(
            texto="\n".join(b["text"] for b in salida["content"] if b["type"] == "text"),
            llamadas=tuple(Llamada(b["id"], b["name"], b["input"])
                           for b in salida["content"] if b["type"] == "tool_use"),
            tokens_entrada=uso.get("input_tokens", 0),
            tokens_salida=uso.get("output_tokens", 0),
        )

    def _openai(self, sistema, mensajes, herramientas, plazo_fin):
        historial = [{"role": "system", "content": sistema}]
        for mensaje in mensajes:
            registro = {k: v for k, v in mensaje.items() if k != "llamadas"}
            if mensaje.get("llamadas"):
                registro["tool_calls"] = [
                    {"id": llamada.id, "type": "function", "function": {"name": llamada.nombre,
                     "arguments": json.dumps(llamada.argumentos, ensure_ascii=False)}}
                    for llamada in mensaje["llamadas"]
                ]
            historial.append(registro)

        cuerpo = {"model": self.modelo, "max_completion_tokens": 450, "temperature": 0.1, "messages": historial}
        if herramientas:
            cuerpo["tools"] = [
                {"type": "function", "function": {"name": h["name"], "description": h["description"],
                                                  "parameters": h["input_schema"]}}
                for h in herramientas
            ]
        salida = self._enviar("https://api.openai.com/v1/chat/completions",
                              {"Authorization": f"Bearer {self.clave}"}, cuerpo, plazo_fin)
        mensaje = salida["choices"][0]["message"]
        uso = salida.get("usage") or {}
        return RespuestaLLM(
            texto=mensaje.get("content") or "",
            llamadas=tuple(Llamada(t["id"], t["function"]["name"], json.loads(t["function"]["arguments"]))
                           for t in mensaje.get("tool_calls") or ()),
            tokens_entrada=uso.get("prompt_tokens", 0),
            tokens_salida=uso.get("completion_tokens", 0),
        )


def obtener_llm(usar_llm: bool | None = None) -> ClienteLLM | None:
    proveedor = os.getenv("CUOTAFLEX_LLM_PROVEEDOR", "").strip().lower()
    habilitado = os.getenv("CUOTAFLEX_LLM", "1" if proveedor else "0") == "1"
    if usar_llm is False or (usar_llm is None and not habilitado):
        return None
    proveedor = proveedor or "anthropic"
    opciones = {"anthropic": ("ANTHROPIC_API_KEY", "claude-haiku-4-5"),
                "openai": ("OPENAI_API_KEY", "gpt-4.1-mini")}
    if proveedor not in opciones:
        return None
    variable_clave, modelo_base = opciones[proveedor]
    clave = os.getenv(variable_clave, "").strip()
    modelo = os.getenv("CUOTAFLEX_LLM_MODELO") or os.getenv("CUOTAFLEX_MODELO") or modelo_base
    return ClienteLLM(proveedor, modelo, clave) if clave else None
