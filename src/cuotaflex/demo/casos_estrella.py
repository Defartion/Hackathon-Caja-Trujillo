"""Solicitudes ficticias que reproducen tres decisiones del motor durante la demo."""
from __future__ import annotations

from ..datos import PERFILES, indice_estacionalidad

# Desviaciones fijas de ventas respecto de la estacionalidad del rubro.
_DESVIACIONES = (
    -.15, .09, -.10, .05, -.12, .11, .13, -.05, .15, -.10, .11, -.06,
    -.07, .15, -.10, .07, -.11, .07, -.07, .08, -.15, .09, .06, -.07,
)


def _solicitud(*, amplitud: float = 1, **datos) -> dict:
    rubro = datos["rubro"]
    perfil = PERFILES[rubro]
    inicio = datos["mes_desembolso"] - len(_DESVIACIONES)
    ventas = [
        round(float(datos["ventas_medias"] * perfil[(inicio + i) % len(perfil)] * (1 + amplitud * desvio)), 2)
        for i, desvio in enumerate(_DESVIACIONES)
    ]
    return {
        "ajuste_asesor": 1.0,
        "tea": 0.45,
        **datos,
        "historial_ventas": ventas,
        "indice_estacionalidad": round(indice_estacionalidad(rubro), 3),
    }


def casos_estrella() -> list[dict]:
    """Entrega solicitudes nuevas en el mismo formato de la bandeja del asesor."""
    return [
        # Rosa cultiva arroz. Los pagos siguen el flujo de siembra y cosecha.
        _solicitud(
            cliente_id="E001", rubro="agricultura", region="Chepén", ventas_medias=8600.0,
            margen=0.35, gasto_familiar=1100.0, otras_cuotas=0.0, dias_atraso_max=0,
            creditos_previos=2, pct_cobros_yape=0.16, antiguedad_negocio_anios=7,
            principal=9800.0, plazo=18, mes_desembolso=0, amplitud=2.75,
        ),
        # Martín trabaja en pesca artesanal. Se muestra el alivio en su primera cuota.
        _solicitud(
            cliente_id="E002", rubro="pesca", region="Pacasmayo", ventas_medias=8500.0,
            margen=0.35, gasto_familiar=900.0, otras_cuotas=0.0, dias_atraso_max=3,
            creditos_previos=1, pct_cobros_yape=0.31, antiguedad_negocio_anios=5,
            principal=5200.0, plazo=12, mes_desembolso=4,
        ),
        # Luis ya paga otras deudas. El motor reduce capital y amplía el plazo.
        _solicitud(
            cliente_id="E003", rubro="bodega", region="Trujillo", ventas_medias=6000.0,
            margen=0.30, gasto_familiar=800.0, otras_cuotas=380.0, dias_atraso_max=3,
            creditos_previos=3, pct_cobros_yape=0.50, antiguedad_negocio_anios=6,
            principal=8000.0, plazo=12, mes_desembolso=0, amplitud=0.4,
        ),
    ]
