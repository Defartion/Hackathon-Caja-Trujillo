# Módulo en vivo: pago por ventas y pago a cosecha

> **Solo diseño.** Este módulo se programa durante la final (3 y 4 de diciembre, Hub UPAO), como piden las
> bases. Antes del evento el repositorio no tiene código del módulo: solo este documento.

## 1. La idea en una frase

El cliente paga **un porcentaje de lo que vende cada mes** (sus cobros registrados con Yape o POS), con un
piso y un techo mensual y un plazo máximo. En la variante **a cosecha**, paga cuotas mínimas durante la
campaña y un pago grande cuando cosecha.

Se inspira en Shopify Capital, donde el comerciante devuelve el financiamiento con un porcentaje de sus
ventas, pero aquí sigue siendo un **crédito con TEA**: el interés corre sobre el saldo y el valor presente
de los pagos cierra el crédito.

## 2. Por qué es la extensión natural de Thinku

| Hoy (fases 0 a 2) | El módulo en vivo |
|---|---|
| La cuota se adapta al **pronóstico** de ventas (fija, aplazamiento, estacional) | La cuota se adapta a las **ventas reales** de cada mes |
| La selección por simulación compara 3 modalidades | Entran 2 candidatas más: `ventas` y `cosecha` |
| El alivio por El Niño baja la cuota al mínimo | Con ventas por el piso, la cuota ya baja sola; la alerta del ENFEN quita el piso |

El caso estrella E001 (Rosa, arroz en Chepén) es el ejemplo natural del pago a cosecha, y E002 (Martín,
pescador) muestra el pago por ventas con la alerta del ENFEN.

## 3. Reglas de negocio

### 3.1 Pago por ventas (`ventas`)

| Regla | Valor inicial | De dónde sale |
|---|---|---|
| Base del pago | Ventas **registradas** del mes (cobros digitales) | Exporte de Yape o POS (sección 5) |
| Tasa de retención `r` | Se calcula por cliente; tope de **30%** | Sección 3.3 |
| Piso mensual | 35% de la cuota fija equivalente | `flexibilidad.cuota_minima_pct` |
| Techo mensual | 1.8 veces la cuota fija | `flexibilidad.cuota_maxima_mult` |
| Plazo objetivo | El que pide el cliente | Igual que hoy |
| Plazo máximo | Objetivo + 6 meses, sin pasar de 30 | Nuevo: `pago_ventas.meses_extra_max` |
| Elegibilidad | Al menos 30% de cobros digitales, mismas reglas de atraso y sobreendeudamiento que hoy | `pct_cobros_yape` ya existe en la cartera sintética |
| TEA | La de la modalidad flexible (base + recargo) | `recargo` en `parametros.yaml` |

**Cada mes:**

```
pago_t  = mínimo(saldo_t · (1 + TEM),  limitar(r · ventas_registradas_t,  piso,  techo))
saldo_t+1 = saldo_t · (1 + TEM) − pago_t
```

- **Si las ventas caen, el pago cae solo** hasta el piso. No hay que pedir nada.
- **Si las ventas suben, el crédito se paga antes** y el cliente paga menos interés.
- **Alerta de El Niño Costero (ENFEN) en rubros expuestos:** durante la alerta el piso pasa a 0 hasta por
  `el_nino.meses_alivio` meses. El interés se capitaliza, igual que con el alivio actual.
- **Cierre del valor presente:** como el interés corre sobre el saldo a la TEM del crédito, el valor
  presente de los pagos es igual al principal en cuanto el saldo llega a cero. Si al plazo máximo queda
  saldo, ese mes vence completo (**pago de cierre**). La política se calibra para que, en el escenario
  conservador (p25), ese pago no supere una cuota fija.
- **Cláusula de conversión:** si dos meses seguidos las ventas registradas caen por debajo del 50% del
  promedio declarado (posible desvío de cobros fuera de Yape), el crédito pasa a cuota fija por el saldo y
  el plazo restantes, y el asesor recibe un aviso.

### 3.2 Pago a cosecha (`cosecha`)

- Solo para rubros con campañas marcadas: los **meses de cosecha** son los del perfil estacional con
  1.25 veces la media o más. Con los perfiles actuales, en agricultura son mayo–julio y noviembre–diciembre.
- **Durante la campaña:** se paga el mayor entre el interés del mes y el 35% de la cuota fija. Así el saldo
  nunca crece.
- **En la cosecha:** se paga lo que cierra el valor presente, repartido entre los meses de cosecha según la
  capacidad p25. Tope: 3 veces la cuota fija por mes.
- **Si hay alerta de El Niño en plena cosecha** (como en los Niños costeros de 2017 y 2023), el pago de
  cosecha pasa a la campaña siguiente una sola vez, con el interés capitalizado.
- Se implementa **reutilizando el optimizador MILP actual**: se llama a `optimizar_cronograma` con una copia
  de los parámetros que permite 3 veces la cuota fija en los meses de cosecha y más meses reducidos el
  resto del año. No hace falta un optimizador nuevo.

### 3.3 Cómo se calcula la tasa de retención `r`

1. Se toma el pronóstico p50 de ventas del cliente (ya lo calcula `pronostico.py`) y se multiplica por su
   porcentaje de cobros digitales.
2. Se busca `r` por bisección para que, con esas ventas, el saldo llegue a cero justo en el plazo objetivo.
3. Se comprueba con el escenario p25: el crédito debe cerrar antes del plazo máximo con un pago de cierre de
   una cuota fija o menos. Si no, se reduce el monto 10%, igual que la replanificación de hoy.
4. Si `r` pasa del 30%, la modalidad no se ofrece: la cuota pesaría demasiado sobre lo que vende.

**Ejemplo de referencia** (S/ 6,000 a 12 meses, TEA 47%, ventas medias de S/ 7,000; cuota fija S/ 612.26,
piso S/ 214.29 y techo S/ 1,102.07):

| Cobros digitales | Ventas registradas medias | `r` aproximada |
|---|---|---|
| 30% | S/ 2,100 | 29.2% (en el límite) |
| 40% | S/ 2,800 | 21.9% |
| 70% | S/ 4,900 | 12.5% |

Son cálculos de referencia (cuota fija dividida entre ventas registradas medias); el motor los afinará con
el pronóstico mes a mes.

### 3.4 Transparencia para el cliente

Antes de firmar, la app muestra la TEA, `r`, el piso, el techo, el plazo esperado y el **costo total en
tres escenarios** (ventas bajas, normales y altas), además del pago de cierre si lo hubiera. Ninguna cifra
se promete: son estimaciones, como en el resto de Thinku.

## 4. Encaje en el motor

Cambios previstos (el motor está congelado en la fase 3 y se edita recién en el evento):

| Archivo | Cambio | Compatibilidad |
|---|---|---|
| `politica.py` | `PRODUCTOS["ventas"]` y `PRODUCTOS["cosecha"]`; elegibilidad por cobros digitales y por rubro; `validar_regla()` (tope de `r`, piso, techo y plazo máximo) | No cambia lo existente |
| `agente.py` | `_dimensionar(cli, "ventas", q)` calcula `r` (sección 3.3) y devuelve la regla más un cronograma esperado con p50 para mostrarlo; `_dimensionar(cli, "cosecha", q)` llama al MILP con parámetros de cosecha | Las 3 modalidades actuales no cambian |
| `seleccion.py` | `candidatos += ["ventas"]` si hay 30% o más de cobros digitales; `+= ["cosecha"]` si el rubro tiene meses de cosecha. `ORDEN_DESEMPATE` suma ambas. `elegir()` no cambia: menor default con VPN ≥ VPN de la fija − 5% | Si no son elegibles, todo queda igual |
| `simulacion.py` | `simular_credito(..., regla_pago=None)`. Con regla, cada mes la cuota se calcula con las ventas de esa trayectoria (pseudocódigo abajo) | Sin regla, resultados idénticos a hoy |
| `datos.py` | Ventas registradas = ventas × `pct_cobros_yape`, con un parámetro de "desvío" para la sensibilidad | Nuevo, opcional |
| `config/parametros.yaml` | Bloques `pago_ventas` (`pct_cobros_min: 0.30`, `r_max: 0.30`, `meses_extra_max: 6`, `conversion_si_cae: 0.5`) y `cosecha` (`techo_mult: 3.0`, `umbral_perfil: 1.25`) | Claves nuevas |

**Pseudocódigo dentro del bucle mensual de `simular_credito`** (todo vectorizado por trayectoria, como hoy):

```python
if regla_pago is not None:
    ventas_reg = ventas[:, t] * regla_pago["pct_digital"]
    piso_t = np.where(nino[:, t] & (alivio_rest > 0), 0.0, regla_pago["piso"])
    cuota_t = np.clip(regla_pago["r"] * ventas_reg, piso_t, regla_pago["techo"])
    cuota_t = np.minimum(cuota_t, saldo * (1 + tem))                 # nunca más que lo que se debe
    cuota_t = np.where(t == n - 1, saldo * (1 + tem), cuota_t)       # pago de cierre al plazo máximo
    # ... el resto del bucle sigue igual: caja, atraso, mora > 30 días, default y VPN
    saldo = saldo * (1 + tem) - pago                                 # pago = lo que realmente cobró la Caja
```

Así se comparan las cinco modalidades con **las mismas trayectorias** de ventas y El Niño, y la selección
sigue siendo justa entre todas.

## 5. Datos

- **En producción:** el historial de cobros que el cliente autorice y pueda exportar de su billetera o POS
  (por ejemplo, un CSV de movimientos), los depósitos en su cuenta de la Caja y, más adelante, los esquemas
  de Open Finance cuando estén disponibles en el Perú. Siempre con consentimiento expreso y solo los datos
  necesarios (Ley N° 29733 de Protección de Datos Personales).
- **En la demo:** todo sintético. La cartera ya trae `pct_cobros_yape`; se generan las ventas registradas de
  cada mes para los tres casos estrella y un CSV de ejemplo con columnas `fecha, monto, medio`.
- **Lo que no se hace:** no se conecta ninguna cuenta real ni se usan datos de clientes de la Caja.

## 6. API y pantallas

### Endpoints (router nuevo `src/cuotaflex/api/routers/pago_ventas.py`, se registra solo)

| Método y ruta | Qué hace |
|---|---|
| `POST /pago-ventas/propuesta` | Igual que `/motor/propuesta`, más las candidatas `ventas` y `cosecha` con `r`, piso, techo, plazo esperado, pagos p25/p50/p90 y comparación con la fija |
| `POST /pago-ventas/prestamos/{loanId}/ventas` | Registra las ventas del mes (JSON o CSV) y devuelve el pago calculado |
| `GET /pago-ventas/prestamos/{loanId}` | Saldo, ventas del mes, pago del mes, `r`, piso, techo y avance |
| `POST /pago-ventas/prestamos/{loanId}/pagar` | Paga el monto calculado del mes y actualiza el saldo |

El formato del préstamo en `api.DB` no cambia: la regla va en un campo nuevo, `regla_pago`, que los demás
routers ignoran.

### App del asesor: tarjeta "Pago por ventas" en la ficha

```
┌ Pago por ventas ─────────────────────────────── elegible: 40% de cobros digitales ┐
│  Retención r  [■■■■■■■■□□□□□□□□]  21.9 %        Piso S/ 214 · Techo S/ 1,102      │
│                                                                                     │
│  Pagos esperados   ▁▂▃▅▇█▇▅▃▂▂▃   p50     ── cuota fija S/ 612                      │
│                    banda p25–p90                                                    │
│  Plazo esperado 12 meses (máx. 18) · Costo total p25 / p50 / p90: S/ … / … / …      │
│  Selección por simulación: default …% vs. …% con la fija    → [Usar esta modalidad]│
└─────────────────────────────────────────────────────────────────────────────────────┘
```

Las cifras de los bocetos son ilustrativas (salen del ejemplo de la sección 3.3), no resultados del motor.

### App del cliente: tarjeta "Tu pago de este mes" en el inicio

```
┌ Tu pago de este mes ───────────────┐
│  Vendiste con Yape     S/ 2,950    │
│  Pagas el 21.9 %   →   S/ 646.05   │
│  ────────────────────────────────  │
│  Si vendes menos, pagas menos      │
│  (mínimo S/ 214.29).               │
│  Te falta: ▓▓▓▓▓▓▓░░░  S/ 3,480    │
│  [ Pagar S/ 646.05 ]               │
└────────────────────────────────────┘
```

**Tablero (día 2):** la modalidad aparece en el gráfico de productos y en la comparación de default.

## 7. Pruebas que se escribirán (`tests/test_modulo_en_vivo.py`)

1. Con el p50 del cliente, `r` deja el saldo en cero en el plazo objetivo (diferencia menor a S/ 1).
2. Con ventas aleatorias, el valor presente de los pagos a la TEM es igual al principal (prueba con muchas
   trayectorias).
3. Cada pago respeta el piso y el techo; el último liquida el saldo.
4. Con ventas 50% más bajas, el pago baja al piso y el plazo se alarga sin pasar el máximo.
5. Con alerta del ENFEN, el piso es 0 como máximo durante `meses_alivio` meses.
6. Con menos de 30% de cobros digitales no se ofrece `ventas`; en agricultura aparece `cosecha`.
7. `simular_credito` sin regla da exactamente los mismos resultados que hoy (regresión).
8. Pago a cosecha: los pagos grandes caen solo en meses de cosecha y respetan el tope de 3 veces.
9. API: la propuesta trae las candidatas; registrar ventas calcula el pago; préstamo inexistente → 404;
   pagar dos veces el mismo mes → 409.
10. **Todas las pruebas anteriores siguen pasando.**

## 8. Plan de implementación (8 horas efectivas)

Motor y API: **Sebastian** (motor) y **Stefano** (API y pruebas). Frontends: **Joaquin** (app del cliente) y
**Andre** (app del asesor). Encaja con el plan de los dos días (`PLAN_DOS_DIAS.md`).

| Hora | Motor y API | Frontends | Control |
|---|---|---|---|
| 0:00–0:30 | Todos: se congela el **contrato de la API** con un JSON de ejemplo por endpoint | Todos | El contrato queda en el repo |
| 0:30–2:30 | Sebastian: regla de pago en `simular_credito` y pruebas 2, 3, 4 y 7. Stefano: router con respuestas del contrato y pruebas 9 | Joaquin: tarjeta del cliente con el JSON de ejemplo. Andre: tarjeta del asesor con el JSON de ejemplo | **H2.5:** ¿el valor presente cierra? ¿pasan las pruebas de la regla? |
| 2:30–4:30 | Sebastian: cálculo de `r`, candidata en `seleccion.py` y pruebas 1, 5 y 6. Stefano: conecta el router al motor y registra ventas | Ambos conectan sus tarjetas a la API real | **H4.5 (fin del día 1):** flujo asesor → cliente con datos reales |
| 4:30–6:30 | Sebastian: variante `cosecha` (prueba 8). Stefano: CSV de ventas y casos estrella con la modalidad | Joaquin: pruebas de punta a punta. Andre: tablero y textos | **H6.5:** demo completa con E001 y E002 |
| 6:30–8:00 | Errores y colchón | Capturas y video actualizado | **Congelamiento** (3 h antes de presentar) |

**Mínimo demostrable** (si todo se complica): la app del asesor propone `ventas` para E001 y la app del
cliente muestra "pagas el X% de lo que vendiste" con un pago calculado por la API.

**Orden de recorte** si un control llega tarde:

1. Se quita la variante `cosecha` (queda solo `ventas`).
2. Se quita la integración con el tablero.
3. El CSV se reemplaza por ventas en JSON.
4. El control deslizante de `r` en la ficha pasa a ser una tarjeta fija.

## 9. Riesgos

| Riesgo | Probabilidad | Impacto | Respuesta |
|---|---|---|---|
| El valor presente no cierra por redondeos | Media | Alto | Pago de cierre explícito y prueba 2 con muchas trayectorias |
| La selección nunca elige `ventas` (pierde más de 5% de VPN) | Media | Medio | Se muestra igual como alternativa en la ficha y se explica con honestidad por qué no gana |
| El cliente desvía cobros fuera de Yape para pagar menos | Media | Alto | Piso, cláusula de conversión a cuota fija y aviso al asesor |
| `/motor/propuesta` se vuelve lenta con 5 candidatas | Media | Medio | 100 escenarios para las candidatas nuevas o simularlas solo si son elegibles |
| Encaje regulatorio (crédito de cuotas variables, TCEA) | Media | Alto | Se presenta como piloto; validarlo con las áreas legal y de riesgos de la Caja |
| No alcanza el tiempo | Media | Alto | Orden de recorte de la sección 8 y mínimo demostrable |
| Se rompe algo existente | Baja | Alto | Prueba 7 de regresión y `pytest` completo en cada control |
