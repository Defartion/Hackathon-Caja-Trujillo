# URGENTE · Ajustar el concepto a las preguntas frecuentes del NEG-01 — para Andre

Hola Andre. El **24 de noviembre** la organización publicó **10 preguntas frecuentes** del NEG-01 en la plataforma (Desafíos → NEG-01 → Preguntas frecuentes). Cambian qué se evalúa y cómo, y el concepto v2 choca con varias de ellas. **La postulación del Concepto de solución está abierta del miércoles 25 al jueves 26 de noviembre**, así que hay que sacar una **v3** antes de subirla.

Lee las 10 FAQ en la plataforma antes de empezar (5 minutos). Abajo va qué cambiar en cada sección.

## Archivos
- Crea `docs/concepto/v3/` copiando `v2/`. **No toques v1 ni v2.**
- Rama: `concepto/v3`.
- Pruebas: agrega las de v3 en `tests/test_lote_d_concepto.py`. Las de v1 y v2 siguen igual.

## Los 6 cambios de fondo
1. **Solo créditos nuevos** (admisión, ampliación, recuperación), con el plan **definido antes del desembolso y fijo**. Cambiar un crédito vigente sería reprogramar, y no es el objetivo. → **Saca del centro el aplazamiento durante el crédito y el alivio de El Niño en vivo.** El Niño pasa a ser un **escenario adverso al diseñar el plan**.
2. **El plan se construye desde el ciclo estimado,** no redistribuyendo una cuota fija. Cada cuota puede tener **monto y periodo distintos**: en la cima se amortiza el máximo de capital; en el valle primero seguros e intereses, y capital solo si alcanza. Gracia y solo interés se permiten con cautela.
3. **Capacidad de pago:** **Cuota ÷ Utilidad Neta ≤ factor del producto en cada etapa**, calculada con la utilidad esperada de cada etapa y no con el promedio. El factor es configurable por producto (ejemplos: 0.65 en inclusión, 0.85 en pequeña empresa). La utilidad neta ya descuenta otras deudas y la carga familiar.
4. **Costos como los de la Caja:**
   - la TEA se pasa a **tasa diaria base 360** y se aplica por **días exactos** sobre el saldo de capital;
   - **seguros** de desgravamen (sobre el saldo) y multirriesgo (sobre el valor asegurable), con interés simple por días;
   - **prelación:** seguros → interés → capital; lo no cubierto queda **pendiente sin capitalizar**;
   - se muestra la **TCEA**, y la TEA es editable sin pasar el tope del BCRP.
5. **Datos:** la Caja **no entregará datos**. El ciclo se estima con lo que levanta el asesor (ventas por temporada, costos, gastos, carga familiar y evidencias) y con el **patrón del sector y la zona de fuentes públicas** (MIDAGRI, SENAMHI, INEI, BCRP, SUNAT, calendarios comerciales). **No debe basarse en el historial de pagos.**
6. **Cómo se evalúa:**
   - innovación tecnológica;
   - **precisión y sustento del modelo de ciclo**;
   - **ajuste del cronograma al ciclo**;
   - adaptabilidad;
   - beneficios esperados;
   - **comparación con la cuota fija en escenarios sintéticos, incluidos los adversos.**

   **No se medirá la mora de una cartera real**: simular su maduración se considera subjetivo. Además:
   - **Usuarios:** el Asesor de Negocios propone, el Asesor de Riesgos valida y el comité aprueba.
   - **Para el comité:** el ciclo en gráfico, las cuotas, Cuota/UN por etapa y los supuestos.
   - **Prototipo:** no se conecta a la Caja; puede ser web, app o WhatsApp, y **se permite un LLM externo vía API para la demo.**

## Sección por sección

| Sección v2 | Qué hacer en v3 |
|---|---|
| **Resumen ejecutivo** | Reescribir. CuotaFlex es la herramienta del Asesor de Negocios que **estima el ciclo económico** del cliente (patrón de su sector y zona, ajustado con lo que levanta en campo) y **construye desde el inicio un plan con cuotas y periodos variables**, con Cuota/UN ≤ factor en cada etapa, costos transparentes (TED 360, seguros, TCEA) y comparación con la cuota fija en escenarios adversos. **Quita la cifra de default de cartera como titular.** |
| **1. Problema** | Agrega lo que dicen las FAQ: la evaluación usa un **ingreso promedio único**, el core **solo genera cuotas fijas** y el límite es del sistema, no de la normativa; al asesor le faltan herramientas para estimar el ciclo. Mantén El Niño como riesgo de la región (alerta vigente). La mora de la SBS puede quedar como contexto en una línea. |
| **2. Concepto** | Quién la usa: Asesor de Negocios, Asesor de Riesgos y comité. Solo créditos nuevos y plan fijo. **Quita** al cliente aplazando cuotas y activando el alivio desde la app; si quieres, menciónalo en una línea como posible extensión vía reprogramación, fuera del alcance del reto. |
| **2.1 Modalidades** | Reemplázala por **"Cómo se construye el plan"**: etapas cima, normal y valle; reglas de amortización por etapa; gracia o solo interés con cautela; periodicidad variable (por ejemplo, cuotas en cosecha); factor por producto; prelación y pendientes; TED 360 y TCEA. |
| **2.3 Riesgos** | Capacidad = regla Cuota/UN por etapa (con un factor menor si el asesor lo decide). Sobreendeudamiento: la UN ya descuenta otras deudas y la carga familiar. Si no hay plan factible, el motor propone menos monto o más plazo, o lo reporta al comité. Escenarios adversos para el comité. **Quita** la elegibilidad por historial de pagos como base del modelo. |
| **3. Impacto** | **Cambia la tabla principal.** En vez de la mora de cartera, usa las métricas que evalúan (ver abajo). La simulación de cartera puede quedar como anexo de una línea, aclarando que no es criterio de evaluación. |
| **4. Enfoque tecnológico** | (1) **Modelo de ciclo:** patrón sector × zona de fuentes públicas, ajuste con la captura del asesor, cuantiles e intervalo calibrado (backtest: cobertura de 79.5% y MAPE p50 de 16.5%). (2) **Constructor del plan:** optimización con Cuota/UN ≤ factor por etapa como restricción dura, prelación y pendientes. (3) **Escenarios adversos:** El Niño, retraso de cosecha, veda y caída de precios. (4) **Agente con LLM externo** (permitido para la demo) que explica al comité y verifica cada cifra. (5) Fineract como demostración opcional de integración. |
| **5. Tecnología preexistente** | Igual, con una nota: la fase 4 adapta el motor a las FAQ. |
| **6. Funcionalidad crítica** | Lo que se mostrará: (a) el asesor estima el ciclo y propone el plan **en la misma herramienta**; (b) la **vista para el comité** con ciclo, cuotas, Cuota/UN por etapa y supuestos; (c) la comparación con la cuota fija en escenarios adversos. Casos: **Rosa** (cuotas en cosecha y gracia en siembra), **Martín** (veda más El Niño como escenario adverso) y **Luis** (el factor obliga a reducir el monto). |
| **7. Nivel de desarrollo** | Ajústalo a lo de arriba. Quita el registro en el core y el desembolso como protagonistas. |
| **8. Factibilidad y dependencias** | **Quita** pedir historial y datos anonimizados (la Caja no los dará). Pide solo **parámetros**: factor por producto, tasas de seguros, tope de TEA y políticas de periodos de gracia. Fuentes públicas en lugar de datos internos. |

## Cifras que sí puedes usar hoy
Vienen del **prototipo actual (motor de la fase 2)**: 600 clientes sintéticos con el mismo monto y plazo, comparando la cuota fija con el plan adaptado (estacional), sobre la utilidad neta esperada de cada mes. Las calculé el 25 de noviembre.

| Métrica | Cuota fija | Plan adaptado (prototipo actual) |
|---|---:|---:|
| Clientes con alguna etapa donde Cuota/UN > 0.85 | 45.8% | 34.3% |
| Etapas por crédito con Cuota/UN > 0.85 (promedio) | 2.39 | 1.60 |
| Clientes con alguna etapa donde Cuota/UN > 0.65 | 56.0% | 39.0% |
| Escenario El Niño · clientes con alguna etapa > 0.85 | 62.7% | 55.0% |
| Interés total medio por crédito | S/ 2,060 | S/ 2,030 |

Por rubro, con factor 0.85 y escenario esperado:

| Rubro | Cuota fija | Plan adaptado |
|---|---:|---:|
| Agricultura | 100% | 78% |
| Pesca | 100% | 95% |
| Calzado | 71% | 34% |
| Comercio de campaña | 27% | 18% |

**Cómo presentarlo con honestidad:** el prototipo actual ya reduce los incumplimientos, pero **no los elimina en agro y pesca**. Hoy el motor exige un piso de cuota incluso en el valle. **El motor de la fase 4 impone Cuota/UN ≤ factor en cada etapa como restricción dura**, con gracia o solo interés en el valle y pendientes sin capitalizar. Por construcción, ningún plan propuesto superará el factor; si no existe plan factible, propone menos monto o más plazo, o lo informa al comité. Escríbelo como **diseño comprometido para la final**, no como resultado medido. Sebastian te pasará las cifras del motor nuevo apenas estén.

## Checklist antes de subir
- [ ] No queda ninguna afirmación de que el cliente aplaza cuotas o activa el alivio durante el crédito como parte central.
- [ ] La tabla de impacto principal mide Cuota/UN por etapa frente a la cuota fija (no la mora de cartera).
- [ ] Se nombran el Asesor de Negocios, el Asesor de Riesgos y el comité, y la vista para el comité.
- [ ] Aparecen TED base 360, seguros, prelación, pendientes sin capitalizar y TCEA.
- [ ] Fuentes públicas del ciclo (MIDAGRI, SENAMHI, INEI, BCRP, SUNAT, calendarios comerciales) y ninguna dependencia del historial de pagos.
- [ ] El LLM externo se menciona como permitido para la demo.
- [ ] El PDF v3 está exportado y revisado, las pruebas pasan y lo revisó otro integrante.
- [ ] **Subido en la plataforma antes del cierre del jueves 26.**
