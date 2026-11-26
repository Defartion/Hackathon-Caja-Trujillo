"""Contrato de estimación del ciclo económico y catálogo para el asesor."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from ...ciclo.catalogo import listar_catalogo
from ...ciclo.estimador import estimar_ciclo

router = APIRouter(prefix="/ciclo", tags=["ciclo"])

Texto = Annotated[str, Field(min_length=1)]
Mes = Annotated[int, Field(strict=True, ge=1, le=12)]
Monto = Annotated[FiniteFloat, Field(strict=True, ge=0)]


class EntradaCiclo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Zona(EntradaCiclo):
    departamento: Texto
    provincia: Texto
    distrito: Texto | None = None


class Evidencia(EntradaCiclo):
    tipo: Literal["yape", "boleta", "boletas"]
    meses: int = Field(strict=True, gt=0)
    monto_promedio_mensual: Monto

    @field_validator("tipo", mode="before")
    @classmethod
    def normalizar_tipo(cls, tipo):
        return tipo.strip().casefold() if isinstance(tipo, str) else tipo


class Captura(EntradaCiclo):
    ventas_mes_alto: Monto
    ventas_mes_normal: Monto
    ventas_mes_bajo: Monto
    meses_altos: list[Mes] = Field(default_factory=list, max_length=12)
    meses_bajos: list[Mes] = Field(default_factory=list, max_length=12)
    costo_ventas_pct: Annotated[FiniteFloat, Field(strict=True, ge=0, le=1)]
    gastos_operativos: Monto
    gastos_tributarios: Monto
    carga_familiar: Monto
    otras_deudas_cuota: Monto
    evidencias: list[Evidencia] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_temporadas(self) -> Captura:
        if not self.ventas_mes_alto >= self.ventas_mes_normal >= self.ventas_mes_bajo:
            raise ValueError("Las ventas deben ordenarse de mes alto a normal a bajo.")
        altos, bajos = set(self.meses_altos), set(self.meses_bajos)
        if len(altos) != len(self.meses_altos) or len(bajos) != len(self.meses_bajos):
            raise ValueError("Los meses de una temporada deben ser únicos.")
        if altos & bajos:
            raise ValueError("Un mes no puede ser alto y bajo a la vez.")
        return self


class CicloSolicitud(EntradaCiclo):
    cliente_id: Texto
    sector: Texto
    actividad: Texto
    zona: Zona
    fecha_inicio: date
    meses: int = Field(strict=True, gt=0)
    captura: Captura

    @model_validator(mode="after")
    def validar_horizonte(self) -> CicloSolicitud:
        disponibles = (date.max.year - self.fecha_inicio.year) * 12 + 12 - self.fecha_inicio.month
        if self.meses > disponibles:
            raise ValueError("El horizonte excede el calendario soportado.")
        return self


class Periodo(BaseModel):
    periodo: str
    etapa: Literal["cima", "normal", "valle"]
    ventas_p50: FiniteFloat
    un_p10: FiniteFloat
    un_p50: FiniteFloat
    un_p90: FiniteFloat


class Escenario(BaseModel):
    id: str
    nombre: str
    un: list[FiniteFloat]


class Fuente(BaseModel):
    nombre: str
    uso: str
    url: str | None = None


class Calidad(BaseModel):
    metodo: str
    cobertura_p10_p90_backtest: Annotated[FiniteFloat, Field(ge=0, le=1)]


class CicloRespuesta(BaseModel):
    cliente_id: str
    sector: str
    actividad: str
    zona: Zona
    fecha_inicio: date
    meses: int
    periodos: list[Periodo]
    escenarios: list[Escenario]
    supuestos: list[str]
    fuentes: list[Fuente]
    calidad: Calidad


class ActividadCatalogo(BaseModel):
    sector: str
    actividad: str
    zonas: list[Zona]


class CicloCatalogo(BaseModel):
    actividades: list[ActividadCatalogo]


@router.get("/catalogo", response_model=CicloCatalogo)
def catalogo():
    return listar_catalogo()


@router.post("/estimar", response_model=CicloRespuesta, response_model_exclude_unset=True)
def estimar(solicitud: CicloSolicitud):
    try:
        resultado = estimar_ciclo(solicitud.model_dump(mode="json", exclude_unset=True))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except OverflowError as error:
        raise HTTPException(422, "La captura excede el rango de cálculo.") from error
    return resultado
