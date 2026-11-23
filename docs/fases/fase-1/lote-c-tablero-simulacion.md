# Fase 1 · Lote C — Tablero de simulación en vivo

**Rama:** `fase-1/lote-c-tablero`

## Objetivo
Darle al jurado la prueba del impacto en los indicadores (30% de la clasificación y 35% en la final).
Es un tablero donde se cambian las políticas (aplazamientos, cuota mínima, recargo, capacidad, El
Niño), se corre la simulación de la cartera y se ve en segundos cómo cambian la mora, el default y
la rentabilidad entre cuota fija y CuotaFlex.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/api/routers/simulacion.py` (nuevo)
- `web/tablero/**` (nuevo)
- `tests/test_lote_c_simulacion.py` (nuevo)

No modifiques `src/cuotaflex/*.py` ni `api/main.py`.

## 1. Backend: `routers/simulacion.py`

```python
router = APIRouter(prefix="/simulacion", tags=["simulacion"])
```

> ⚠️ `config.cargar_parametros()` está cacheado y devuelve **siempre el mismo dict**. Haz
> `par = copy.deepcopy(cargar_parametros())` antes de aplicar cambios, o alterarás la configuración
> de toda la API.

### `GET /simulacion/parametros-editables`
Devuelve la lista de controles del tablero (ruta, etiqueta, mínimo, máximo, paso, valor actual y ayuda):

| ruta | etiqueta | rango | paso |
|---|---|---|---|
| `flexibilidad.max_aplazamientos` | Aplazamientos por crédito | 0–4 | 1 |
| `flexibilidad.cuota_minima_pct` | Cuota mínima (% de la fija) | 0.20–0.60 | 0.05 |
| `flexibilidad.cuota_maxima_mult` | Cuota máxima (× la fija) | 1.2–2.5 | 0.1 |
| `flexibilidad.recargo_spread_tea` | Recargo por flexibilidad (TEA) | 0–0.05 | 0.005 |
| `flexibilidad.requisito_dias_atraso_max` | Atraso máximo para acceder | 0–30 | 1 |
| `capacidad_pago.ratio_cuota_excedente_max` | Cuota / excedente máx. | 0.5–0.9 | 0.05 |
| `capacidad_pago.ratio_deuda_total_max` | Deuda total / excedente máx. | 0.6–1.0 | 0.05 |
| `el_nino.probabilidad_anual` | Probabilidad anual de El Niño | 0–1 | 0.05 |
| `el_nino.meses_alivio` | Meses de alivio El Niño | 0–6 | 1 |
| `simulacion.fuga_caja_mensual` | Gasto del sobrante mensual | 0–0.4 | 0.05 |

### `POST /simulacion/correr`
```json
{"n_clientes": 200, "n_escenarios": 100, "semilla": 2026, "replanificar": true,
 "cambios": {"flexibilidad.max_aplazamientos": 3, "el_nino.probabilidad_anual": 1.0}}
```
- Valida que `n_clientes ≤ 600`, `n_escenarios ≤ 300` y que cada ruta de `cambios` esté en la tabla anterior. Si no, responde 422.
- Aplica los cambios sobre la copia `par` y llama a `simulacion.comparar_cartera(n_clientes, n_escenarios, semilla, "perfil", par, replanificar)`.
- **Caché:** guarda en un dict los resultados por el hash del cuerpo (JSON con `sort_keys`), hasta 50 entradas. La misma consulta debe responder al instante.
- Respuesta:
```json
{
  "resumen": { ...salida de resumir()... },
  "histograma_vpn": {"bordes": [...21], "fija": [...20], "cuotaflex": [...20]},
  "dispersion": [{"cliente_id": "...", "rubro": "...", "mora_fija": 0.2, "mora_flex": 0.05}],
  "duracion_s": 4.2, "parametros_usados": { ...solo las rutas editables... }
}
```
- `histograma_vpn` usa `np.histogram` con 20 tramos comunes a las dos estrategias, a partir de la columna `vpn` del detalle.
- Convierte todos los tipos de NumPy a tipos nativos de Python.
- **Rendimiento:** con 200 clientes y 100 escenarios debe responder en menos de 10 s. Mídelo y anótalo en el README.

### `GET /simulacion/escenarios`
Escenarios predefinidos para los botones del tablero:
- **Base:** sin cambios.
- **Año El Niño:** `el_nino.probabilidad_anual` = 1.0.
- **Sin flexibilidad:** `max_aplazamientos` = 0, `cuota_minima_pct` = 0.95, `recargo_spread_tea` = 0. Sirve de control.
- **Cliente ahorrador:** `fuga_caja_mensual` = 0. Muestra con honestidad cuándo la flexibilidad aporta poco.
- **Política estricta:** `ratio_deuda_total_max` = 0.6.

### Pruebas (`tests/test_lote_c_simulacion.py`)
- `parametros-editables` devuelve las 10 rutas.
- `correr` con 30 clientes y 20 escenarios responde con un resumen que incluye `fija`, `cuotaflex` y `delta`, y el histograma con 20 tramos.
- Con una ruta no permitida, responde 422.
- Después de correr con cambios, `cargar_parametros()` conserva sus valores originales (se aplicó a una copia).
- La segunda llamada idéntica sale de la caché.

## 2. Frontend: `web/tablero`

**Stack:** Vite + React + TypeScript + Recharts, en el puerto **5175**, pensado para proyectarse en
1920×1080 y que funcione en 1366×768. La URL de la API va en `VITE_API_URL`. Usa los tokens de `docs/fases/ROADMAP.md`.

### Diseño de la pantalla
- **Panel izquierdo (controles)**
  - Botones de escenarios predefinidos.
  - Deslizadores generados a partir de `parametros-editables`, con su valor visible y la ayuda en un tooltip.
  - Interruptor "Completo / Solo cronograma" (el campo `replanificar`).
  - Selector de tamaño: Rápido (150×80), Estándar (300×150) y Completo (600×200).
  - Botón grande **"Simular"** con barra de carga. Mientras corre, los controles quedan desactivados.
- **Fila de indicadores** (4 tarjetas): atraso > 30 días, default, margen neto sobre la cartera y cartera colocada. Cada una muestra fija → CuotaFlex y la diferencia en verde o rojo (para mora y default, bajar es verde).
- **Gráfico 1:** barras agrupadas de atraso > 30 días por rubro, fija contra CuotaFlex.
- **Gráfico 2:** histograma superpuesto del VPN por crédito para las dos estrategias.
- **Gráfico 3:** dispersión con la mora de cada cliente en fija (eje X) contra CuotaFlex (eje Y), con la diagonal y = x. Los puntos bajo la diagonal son mejoras; color por rubro.
- **Gráfico 4:** dona con el reparto de productos (fija, aplazamiento, estacional).
- **Historial de corridas:** una tabla con las últimas 5 simulaciones (parámetros cambiados y los indicadores clave) para comparar escenarios en vivo.
- **Pie fijo:** "Datos 100% sintéticos. Parámetros referenciales a calibrar con Caja Trujillo."

### Requisitos de calidad
- Los colores de cada estrategia son siempre los mismos: fija en gris (`--cf-gris-600`) y CuotaFlex en azul (`--cf-azul`).
- Si la simulación falla o tarda más de 30 s, se muestra un mensaje y se reactivan los controles.
- `npm run build` sin errores.

## Cómo correr
```bash
PYTHONPATH=src uvicorn cuotaflex.api.main:app --reload
cd web/tablero && npm install && npm run dev
```

## Criterios de aceptación
- [ ] El escenario "Base" en tamaño Estándar muestra los indicadores y los 4 gráficos en menos de 15 s.
- [ ] Al cambiar un deslizador y volver a simular, cambian los indicadores, y el historial guarda las dos corridas.
- [ ] El escenario "Año El Niño" muestra que el alivio reduce el default frente a la cuota fija.
- [ ] La configuración global no se altera (cubierto por las pruebas).
- [ ] `pytest` pasa, incluidas las pruebas nuevas.
- [ ] El README incluye capturas y una tabla de tiempos de respuesta por tamaño.

## Fuera de alcance
La calibración del modelo (fase 2, lote A) y la persistencia del historial (fase 3).
