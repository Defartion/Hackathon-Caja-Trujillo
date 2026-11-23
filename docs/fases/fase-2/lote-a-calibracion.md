# Fase 2 · Lote A — Calibración del modelo, backtesting y selección de producto por simulación

**Rama:** `fase-2/lote-a-calibracion`

## Objetivo
Que las cifras resistan las preguntas del jurado: el impacto en indicadores vale 30% en la clasificación y 35% en la final.
Hay tres problemas por resolver:
- La mora de la cuota fija sale demasiado alta (16%) frente a una cartera de microempresa real.
- Hay rubros (calzado y comercio) donde la cuota estacional sale **peor** que la fija.
- No hemos medido qué tan bueno es el pronóstico.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/datos.py`, `pronostico.py`, `politica.py`, `simulacion.py`, `optimizador.py`
- `src/cuotaflex/seleccion.py` (nuevo)
- `src/cuotaflex/agente.py`: **solo el método `proponer()`**. El método `explicar()` y las funciones `_explicacion_*` son del lote D.
- `config/parametros.yaml`, `resultados/**`, `notebooks/**` (nuevo)
- `scripts/backtest.py` y `scripts/sensibilidad.py` (nuevos)
- `tests/test_fase2_a.py` (nuevo)

## Contratos que NO se pueden romper
El tablero (fase 1, lote C) y la app del asesor dependen de estas firmas; mantenlas compatibles:
- `optimizador.optimizar_cronograma(principal, tem, capacidad, par=None, suavidad=0.02) -> dict` y el nombre `optimizar_cronograma` importado dentro de `agente.py`. El router de simulación lo reemplaza con una versión que guarda resultados en memoria.
- `simulacion.comparar_cartera(n_clientes, n_escenarios, semilla, metodo_pronostico, par, replanificar) -> (DataFrame, dict)`, con las mismas claves en `resumir()`: `fija`, `cuotaflex`, `delta`, `por_rubro` y `mix_productos`. Puedes agregar claves, no quitar.
- La salida de `AgenteAsesor.proponer()`: mismas claves. Puedes agregar.
- Las rutas de `config/parametros.yaml` que usa el tablero (lista en `routers/simulacion.py`). Puedes agregar rutas nuevas.

## Tareas

### 1. Calibrar la cartera sintética
- Busca la **mora de microempresa de las cajas municipales** en las estadísticas de la SBS (cartera atrasada de microempresa, último dato disponible) y anota la fuente en `resultados/calibracion.md`.
- Ajusta `datos.generar_cartera` (tamaño de la cuota frente al excedente, cola de historial con atrasos, volatilidad por rubro) y `simulacion.fuga_caja_mensual` hasta que la **cuota fija** dé una mora cercana a esa referencia. Atención: la simulación mide "algún atraso > 30 días durante la vida del crédito", así que debe quedar algo por encima de la mora contable de un mes cualquiera. Explica cómo se compara.
- No cambies la lógica del flujo de caja de `simular_credito` sin documentarlo.

### 2. Backtesting del pronóstico (`scripts/backtest.py`)
- Validación con origen móvil sobre la cartera sintética: entrena con 18 meses y pronostica 6, con al menos 3 orígenes.
- Métodos a comparar: `perfil`, `statsforecast` y `mixto`, con varios pesos (0.3, 0.5 y 0.7).
- Métricas por rubro y método:
  - MAPE de p50;
  - pérdida pinball de p10, p25, p50 y p90;
  - **cobertura** de p10–p90 (lo ideal es cerca de 80%) y de p25 (cerca de 75% de los valores por encima).
- Elige el método y el peso por defecto con evidencia y deja la tabla en `resultados/backtest.md`.
- Opcional: Chronos-Bolt, si se instala en menos de 10 minutos, declarado en `requirements.txt` como opcional.

### 3. Selección de producto por simulación (`seleccion.py`)
Reemplaza la regla fija (`indice_estacionalidad >= 0.15` → estacional):
- Para cada cliente elegible, construye las tres modalidades (fija, aplazamiento y estacional) y simúlalas con `simular_credito` en 200 escenarios con semilla fija por cliente.
- Elige la de **menor default**, siempre que su VPN medio no caiga más de X% respecto de la fija (X va en `config`: `seleccion.max_perdida_vpn_pct`, por defecto 5).
- Registra en la `bitacora` un paso `{"paso": "seleccion", "candidatos": {...métricas por modalidad...}, "elegido": ...}`. La app del asesor ya muestra la bitácora; el paso nuevo debe aparecer como texto genérico sin romper nada.
- **Rendimiento:** la propuesta individual debe seguir respondiendo en menos de 2 s. Para la cartera completa (600 × 200), prevé un modo rápido: `seleccion.modo: simulacion|regla`, con la simulación por defecto en propuestas individuales.
- Integra el cambio en `agente.proponer()` reemplazando la llamada a `recomendar_producto`.

### 4. Recargo por producto
- Convierte `flexibilidad.recargo_spread_tea` en recargo por producto: `recargo.estacional` y `recargo.aplazamiento`. **Mantén también la clave antigua**, porque el tablero la usa; si se envía, se aplica a ambos.
- Evalúa el recargo de la estacional entre 0 y 2 pp y documenta cuál maximiza VPN sin subir el default.

### 5. Análisis de sensibilidad (`scripts/sensibilidad.py`)
Genera un gráfico PNG y una tabla del beneficio de CuotaFlex (reducción de default y diferencia de margen) en función de:
- `fuga_caja_mensual`, de 0 a 0.4 (el supuesto clave);
- `el_nino.probabilidad_anual`, de 0 a 1;
- el error del pronóstico (multiplicar el sigma por 1, 1.5 y 2).

Salida en `resultados/sensibilidad.md` y `resultados/img/*.png`.

### 6. Actualizar resultados
- Vuelve a correr `python scripts/simular.py` y actualiza `resultados/resumen.json`.
- Escribe `resultados/CAMBIOS_FASE2.md` con una tabla de cifras antes y después, más una explicación en 5 viñetas para que Andre la lleve al concepto y al pitch.

## Pruebas (`tests/test_fase2_a.py`)
- La mora de la cuota fija en la cartera calibrada (200 × 100, semilla fija) queda en el rango objetivo documentado.
- La selección nunca elige un producto con más default que la fija si el cliente es elegible.
- Un cliente de calzado con el caso de la fase 1 (`C00000` con `semilla=7`) ya no sale peor con CuotaFlex.
- `comparar_cartera` mantiene sus claves de salida, y la clave antigua `recargo_spread_tea` sigue funcionando.
- La propuesta individual tarda menos de 2 s, medido en la prueba.
- **Todas las pruebas existentes (42) siguen pasando.**

## Criterios de aceptación
- [ ] Mora de la fija calibrada contra la referencia de la SBS, con la fuente citada.
- [ ] Tabla de backtesting y método por defecto elegido con evidencia.
- [ ] Selección por simulación integrada, sin ningún rubro donde CuotaFlex empeore en promedio.
- [ ] Gráficos de sensibilidad y documento de cambios en cifras.
- [ ] Tablero y app del asesor funcionando sin cambios (revisión manual más pruebas).
