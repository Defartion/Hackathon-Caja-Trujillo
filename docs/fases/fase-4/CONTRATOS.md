# Contratos de la fase 4 (no cambiarlos sin avisar a todo el equipo)

Los cuatro lotes trabajan en paralelo contra estos contratos. Los JSON de ejemplo están en
`tests/fixtures/contratos/` y son **ilustrativos**: el caso es Rosa, arroz en Chepén. Tienen cifras
coherentes para construir y probar interfaces, pero **no los produce el motor**. Cada lote debe hacer
que su salida real tenga exactamente esta forma.

```
App del asesor (lote C) ──POST /ciclo/estimar──▶ Modelo de ciclo (lote B)
        │                                         │ devuelve: periodos + escenarios + supuestos + fuentes
        └──POST /plan/proponer (con el ciclo)──▶ Constructor del plan (lote A)
                                                  │ devuelve: plan + plan_cuota_fija + estres + supuestos
Agente (lote D) lee ciclo y plan para explicar al asesor y al comité.
```

## 1. `POST /ciclo/estimar` (lote B)
**Solicitud:** `ciclo_estimar_solicitud.json`

| Campo | Tipo | Nota |
|---|---|---|
| `cliente_id` | str | |
| `sector`, `actividad` | str | p. ej. `agricultura` / `arroz`, `pesca` / `anchoveta artesanal`, `comercio` / `útiles escolares` |
| `zona` | obj | `departamento`, `provincia`, `distrito` (o null) |
| `fecha_inicio` | ISO date | fecha prevista de desembolso |
| `meses` | int | horizonte, igual al plazo del crédito |
| `captura` | obj | lo que levanta el asesor (detalle en el ejemplo). Los **meses van de 1 a 12** |

**Respuesta:** `ciclo_estimar_respuesta.json`
- `periodos[]`, **uno por mes** desde el mes siguiente al desembolso: `periodo` ("AAAA-MM"), `etapa` (`cima` | `normal` | `valle`), `ventas_p50`, `un_p10`, `un_p50`, `un_p90`.
  - **UN = utilidad neta mensual**, ya descontados costos, gastos operativos y tributarios, otras deudas y carga familiar.
- `escenarios[]`: `id`, `nombre`, `un[]`. El largo de `un` es igual a `meses`. **Siempre incluye `base`**, y al menos `el_nino`, `retraso_cosecha` o `veda_extendida` según el sector, y `caida_precios`.
- `supuestos[]` (textos), `fuentes[]` (`nombre`, `uso`, `url` opcional) y `calidad` (`metodo`, `cobertura_p10_p90_backtest`).

## 2. `POST /plan/proponer` (lote A)
**Solicitud:** `plan_proponer_solicitud.json`

| Campo | Tipo | Nota |
|---|---|---|
| `monto`, `tea`, `fecha_desembolso`, `plazo_meses` | | La TEA es editable y debe ser ≤ `producto.tope_tea`, si se envía |
| `producto` | obj | `nombre`, `factor` (< 1), `tope_tea`, `max_meses_gracia`, `permite_solo_interes` |
| `seguros` | obj | `desgravamen{activo, tasa_mensual}` y `multirriesgo{activo, tasa_mensual, valor_asegurable}`. Cada seguro se calcula como `tasa_mensual / 30 × días × base` (interés simple, base 360) |
| `ciclo` | obj | la **respuesta completa** de `/ciclo/estimar` |
| `comparar_cuota_fija` | bool | |

**Respuesta:** `plan_proponer_respuesta.json`
- `factible` (bool) y `ajustes_sugeridos[]` (`tipo`: `reducir_monto` | `ampliar_plazo` | `bajar_factor`, con su valor) cuando no es factible.
- `plan` y `plan_cuota_fija`, con la **misma forma**:
  - `periodos[]`: `n`, `fecha_vencimiento`, `dias`, `etapa`, `cuota`, `seguro_desgravamen`, `seguro_multirriesgo`, `interes`, `pago_seguros`, `pago_interes`, `capital`, `pendiente_seguros`, `pendiente_interes`, `saldo_capital`, `saldo_deuda`, `un_esperada`, `ratio_cuota_un` (null si la UN es ≤ 0) y `tipo` (`amortizacion` | `solo_interes` | `gracia`).
  - `resumen`: `cuotas`, `total_pagado`, `interes_total`, `seguros_total`, `ted`, `tcea`, `ratio_max`, `etapas_sobre_factor`, `cumple_factor`, `meses_gracia` y `meses_solo_interes`.
- `estres[]`: `escenario`, `nombre`, `adaptado{etapas_sobre_factor, ratio_max, monto_sobre_capacidad}` y `fija{…}`.
- `supuestos[]` y `bitacora[]` (pasos del constructor, como hoy en el agente).

## Reglas de negocio comunes (de las FAQ del NEG-01)
- Solo créditos nuevos. El plan se define antes del desembolso y **no cambia**.
- **Cuota ÷ UN esperada de la etapa ≤ factor del producto**, en todas las etapas con cuota > 0. Con UN ≤ 0, la cuota debe ser 0 (gracia).
- **TEA → TED = (1+TEA)^(1/360) − 1**, aplicada por los **días exactos** del periodo sobre el saldo de capital.
- **Prelación:** seguros → interés → capital. Lo no pagado queda **pendiente en su concepto**: suma a `saldo_deuda`, **no** a `saldo_capital` y **no genera interés**. En el periodo siguiente se paga primero lo pendiente.
- **TCEA:** la tasa anual (base 360) que iguala el monto desembolsado con las cuotas en sus fechas.
- **La Caja no entrega datos.** El ciclo **no usa el historial de pagos**.
