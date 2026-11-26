"""Patrones mensuales por actividad y zona de La Libertad."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from math import fsum, isfinite
from pathlib import Path

RUTA_DATOS = Path(__file__).resolve().with_name("recursos")

_SECTORES = {
    "agro": "agricultura",
    "agropecuario": "agricultura",
    "comercio de campana": "comercio",
    "industria": "manufactura",
    "servicio": "servicios",
}
_ACTIVIDADES = {
    "arroz cascara": "arroz",
    "cana": "cana de azucar",
    "palta hass": "palta",
    "papa": "papa de sierra",
    "artesanal": "pesca artesanal",
    "perico": "pesca artesanal",
    "anchoveta": "anchoveta artesanal",
    "escolar": "utiles escolares",
    "campana escolar": "utiles escolares",
    "campana fiestas patrias": "fiestas patrias",
    "campana navidena": "navidad",
    "navidena": "navidad",
    "transporte terrestre": "transporte",
}


@dataclass(frozen=True)
class Fuente:
    nombre: str
    fecha: str
    uso: str
    url: str


@dataclass(frozen=True)
class Patron:
    sector: str
    actividad: str
    departamento: str
    provincia: str
    distrito: str | None
    indices: tuple[float, ...]
    meses_altos: tuple[int, ...]
    meses_bajos: tuple[int, ...]
    volatilidad: float
    meses_veda: tuple[int, ...]
    meses_el_nino: tuple[int, ...]
    caida_el_nino: float
    supuestos: tuple[str, ...]
    _fuentes: tuple[Fuente, ...]

    @property
    def fuentes(self) -> list[dict[str, str]]:
        return [
            {"nombre": f"{fuente.nombre} ({fuente.fecha})", "uso": fuente.uso, "url": fuente.url}
            for fuente in self._fuentes
        ]

    @property
    def zona(self) -> dict[str, str | None]:
        return {
            "departamento": self.departamento,
            "provincia": self.provincia,
            "distrito": self.distrito,
        }


def _clave(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(letra for letra in normalizado if not unicodedata.combining(letra))
    return " ".join(sin_tildes.casefold().split())


def _indices(valores: list[float], peso: float) -> tuple[float, ...]:
    if len(valores) != 12 or any(not isfinite(valor) or valor < 0 for valor in valores):
        raise ValueError("El patrón debe contener doce valores mensuales no negativos.")
    promedio = fsum(valores) / 12
    if promedio == 0 or not 0 < peso <= 1:
        raise ValueError("El patrón debe tener media positiva y peso entre cero y uno.")
    normalizados = tuple(1 + peso * (valor / promedio - 1) for valor in valores)
    if min(normalizados) <= 0:
        raise ValueError("Los índices mensuales deben ser positivos.")
    return normalizados


@lru_cache(maxsize=1)
def cargar_patrones() -> tuple[Patron, ...]:
    datos = json.loads((RUTA_DATOS / "patrones.json").read_text(encoding="utf-8"))
    fuentes = {clave: Fuente(**dato) for clave, dato in datos["fuentes"].items()}
    patrones = []
    for registro in datos["patrones"]:
        zona = registro["zona"]
        escenario = registro["el_nino"]
        ids = registro["fuentes"] + datos["fuentes_el_nino"] + escenario.get("fuentes", [])
        patrones.append(Patron(
            sector=registro["sector"],
            actividad=registro["actividad"],
            departamento=datos["departamento"],
            provincia=zona["provincia"],
            distrito=zona.get("distrito"),
            indices=_indices(registro["valores"], registro.get("peso_serie", 1)),
            meses_altos=tuple(registro["meses_altos"]),
            meses_bajos=tuple(registro["meses_bajos"]),
            volatilidad=registro["volatilidad"],
            meses_veda=tuple(registro.get("meses_veda", [])),
            meses_el_nino=tuple(escenario["meses"]),
            caida_el_nino=escenario["caida"],
            supuestos=tuple(registro["supuestos"]),
            _fuentes=tuple(fuentes[identificador] for identificador in dict.fromkeys(ids)),
        ))
    return tuple(patrones)


def obtener_patron(
    sector: str, actividad: str, departamento: str, provincia: str, distrito: str | None = None
) -> Patron:
    sector_clave = _clave(sector)
    actividad_clave = _clave(actividad)
    sector_clave = _SECTORES.get(sector_clave, sector_clave)
    actividad_clave = _ACTIVIDADES.get(actividad_clave, actividad_clave)
    candidatos = [
        patron for patron in cargar_patrones()
        if (
            _clave(patron.sector) == sector_clave
            and _clave(patron.actividad) == actividad_clave
            and _clave(patron.departamento) == _clave(departamento)
            and _clave(patron.provincia) == _clave(provincia)
        )
    ]
    distrito_clave = _clave(distrito) if distrito is not None else None
    for patron in candidatos:
        if patron.distrito is not None and _clave(patron.distrito) == distrito_clave:
            return patron
    for patron in candidatos:
        if patron.distrito is None:
            return patron
    if distrito is None and len(candidatos) == 1:
        return candidatos[0]
    raise ValueError(f"No hay patrón para {sector} / {actividad} en {provincia}, {departamento}.")


def listar_catalogo() -> dict[str, list[dict]]:
    actividades: dict[tuple[str, str], list[dict]] = {}
    for patron in cargar_patrones():
        actividades.setdefault((patron.sector, patron.actividad), []).append(patron.zona)
    return {
        "actividades": [
            {"sector": sector, "actividad": actividad, "zonas": zonas}
            for (sector, actividad), zonas in actividades.items()
        ]
    }
