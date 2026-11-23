# Concept Solution · CuotaFlex

**Cajathón 2026 · Caja Trujillo · Eje 4: Inclusión financiera y resiliencia · NEG-01 "Cuotas que se adaptan al flujo del negocio"**

## 1. Resumen

CuotaFlex es un motor de decisión para el asesor de negocios. Con la información del cliente
pronostica sus ventas con incertidumbre, evalúa si puede acceder a flexibilidad, elige la modalidad
de pago adecuada y calcula un cronograma óptimo que cabe en su flujo del escenario conservador.
El valor presente del crédito se mantiene, así que la Caja conserva su rentabilidad. Un agente
orquesta los pasos, replanifica cuando la propuesta no cabe y explica la decisión. El cronograma
se carga en el core (Fineract o una API compatible).

En la simulación con 600 créditos sintéticos y 200 escenarios por crédito, los créditos con atraso
mayor a 30 días bajaron de 16.3% a 7.3% y el default de 8.5% a 3.4%. El margen neto sobre la cartera
subió de 16.5% a 22.7%.

## 2. Problema

- Los ingresos de los microempresarios varían por las campañas agrícolas, la temporada de pesca, las
  campañas comerciales (escolar, Día de la Madre, Fiestas Patrias, Navidad) y la producción de calzado.
- La cuota uniforme exige lo mismo en temporada baja que en alta. Un negocio viable cae en atraso por
  falta de liquidez, no por falta de capacidad anual.
- En la práctica el sobrante de la temporada alta no se guarda por completo: se reinvierte o se
  gasta. Por eso la cuota fija cae justo en el mes de menos caja.
- Los eventos climáticos (El Niño costero) golpean a la vez a rubros enteros de la región.

## 3. Solución

### 3.1 Modalidades de pago

| Modalidad | Para quién | Regla |
|---|---|---|
| Cuota fija | Clientes sin historial suficiente, con atrasos o sobreendeudados | Cronograma tradicional |
| Fija con aplazamiento | Buen historial y negocio poco estacional | Hasta **2 cuotas** por crédito pagando solo la cuota mínima, solo si está al día. El saldo se redistribuye con interés |
| Estacional | Buen historial y negocio estacional (agro, pesca, comercio de campaña, calzado) | Cuotas optimizadas según el flujo, con piso y techo y hasta 4 meses reducidos por año |
| Cláusula El Niño | Rubros expuestos | Alivio automático de hasta 3 cuotas al mínimo si el **ENFEN declara alerta de El Niño costero** |

Las opciones flexibles llevan un recargo referencial de +2 pp de TEA, que ayuda a que las elijan
quienes de verdad las valoran (autoselección).

### 3.2 Evidencia que respalda el diseño

- **BRAC (Bangladesh):** el aplazamiento de hasta dos cuotas por ciclo redujo la mora 35% y subió la ganancia 27% en los créditos más pequeños.
- **Kolkata (India):** dos meses de gracia sin condiciones elevaron la ganancia, pero la mora pasó de 2% a 7%. Por eso CuotaFlex exige cuota mínima y condiciona la flexibilidad al buen pago.
- **Sonata (India):** un contrato flexible con +2 pp de tasa lo eligió 1 de cada 3 clientes y su pago fue similar al de los demás. Este es el respaldo del recargo.
- **Bangladesh rural:** las cuotas ajustadas a la temporada baja no empeoraron la mora (resultados preliminares).
- **Shopify Capital:** cobra un porcentaje de las ventas. Es la referencia de largo plazo cuando haya datos de ventas registrados (por ejemplo, con Open Finance, previsto para 2028).
- **Caja Nuestra Gente (2011-2012):** un seguro paramétrico contra El Niño protegió 585 créditos agrícolas. Es el antecedente regional de la cláusula El Niño.

### 3.3 Capacidades tecnológicas (más allá de un tablero o un chatbot)

1. **Analítica predictiva probabilística:** pronóstico de ventas por cliente con `statsforecast`
   (AutoETS estacional) combinado con el perfil estacional de negocios similares y con un ajuste del
   asesor acotado a ±10%. El resultado son cuantiles, no un número único, porque el reto pide
   reconocer la incertidumbre.
2. **Optimización matemática (MILP):** con CVXPY y HiGHS decide el monto de cada cuota. Las
   restricciones son cuatro: el valor presente es igual al capital (rentabilidad), la cuota es menor
   o igual al 70% del excedente del escenario p25 (capacidad de pago), hay piso y techo por cuota (sin
   cuotas globo) y hay un límite de meses reducidos (política). El objetivo minimiza el déficit de
   capacidad y la desviación respecto a la cuota fija.
3. **Agente asesor:** planifica y ejecuta las herramientas (elegibilidad → pronóstico → producto →
   optimización → validación). Si la propuesta no cabe, **replanifica**: primero amplía el plazo y
   después reduce el monto. Deja una bitácora auditable y explica la decisión en lenguaje simple. La
   redacción con un LLM es opcional y nunca inventa cifras.
4. **Simulación Monte Carlo:** miles de trayectorias de ingresos con choques, estacionalidad y El
   Niño. Compara la cuota fija con CuotaFlex usando las mismas trayectorias, así que mide la mejora
   causal en mora y rentabilidad.
5. **Integración con el core:** una API compatible con Apache Fineract (préstamos con cuotas
   variables, aprobación, desembolso, pagos y aplazamiento). El cronograma se carga antes de aprobar,
   como exige Fineract.

## 4. Gestión de riesgo y cumplimiento

- **Capacidad de pago:** el diseño se hace contra el escenario conservador p25, no contra el promedio.
- **Sobreendeudamiento:** si la cuota nueva más las otras deudas supera el 80% del excedente, el cliente
  no recibe flexibilidad y el agente reduce el monto. CuotaFlex no aumenta el endeudamiento para
  hacer caber un cronograma.
- **Rentabilidad:** el valor presente se cierra a la tasa del crédito. La flexibilidad cambia
  *cuándo* se paga, no *cuánto vale* el crédito.
- **Políticas configurables:** todas están en `config/parametros.yaml` (piso, techo, aplazamientos,
  ratios, recargo, requisitos de historial) y el equipo de Riesgos de la Caja puede calibrarlas.
- **Transparencia:** el cliente recibe el cronograma completo con la TCEA antes de firmar. El
  aplazamiento y la cláusula El Niño quedan pactados en el contrato.
- **A validar con la Caja:** la conformidad con su normativa y la de la SBS (transparencia, tratamiento
  contable de los aplazamientos pactados y diferencia con una reprogramación). También si la Caja ya
  ofrece cuotas estacionales o pago a cosecha.

## 5. Indicadores y resultados

Hay dos variantes de simulación (`resultados/resumen.json`):

| Indicador | Cuota fija | CuotaFlex completo | Solo cronograma |
|---|---|---|---|
| Atraso > 30 días | 16.3% | 7.3% | 14.3% |
| Default | 8.5% | 3.4% | 7.7% |
| Margen neto / cartera | 16.5% | 22.7% | 17.1% |
| Cartera colocada | S/ 4.51 M | S/ 3.89 M | S/ 4.51 M |

Cómo leerlos:
- La mayor parte de la mejora viene de **dimensionar** bien el monto y el plazo con el pronóstico
  probabilístico. La otra parte viene del cronograma flexible.
- La cartera colocada baja 14% porque el agente se niega a sobreendeudar. Hay que discutir este
  intercambio con la Caja: el margen neto absoluto sube aun con menos colocación.
- Los rubros más estacionales (agricultura y pesca) concentran el beneficio. En rubros estables el
  efecto es neutro. En calzado y comercio, el cronograma por sí solo no mejora y se está calibrando
  el umbral de estacionalidad.
- Los datos son sintéticos y la cartera está estresada a propósito. Las cifras muestran el método,
  no son una promesa de resultados.

## 6. Datos que se solicitarían a la Caja

1. Historial de pagos anonimizado por crédito (días de atraso por cuota, reprogramaciones).
2. Ventas o flujos declarados en las evaluaciones del asesor, por rubro y región.
3. Condiciones crediticias: tasas por segmento, plazos, montos, políticas de capacidad de pago y de sobreendeudamiento.
4. Costo de fondeo, gasto operativo y tasas de recuperación referenciales.
5. Calendarios estacionales por rubro validados por los asesores de campo.
6. Historial de las alertas del ENFEN y del impacto de El Niño 2017 y 2023 en la cartera.

## 7. Arquitectura e integración

Ver `docs/ARQUITECTURA.md`. Flujo en resumen: app del asesor → API CuotaFlex → agente (pronóstico +
política + optimizador) → cronograma → Fineract (cuotas variables) → app del cliente (cronograma,
aplazamiento, avisos El Niño).

## 8. Plan para los dos días de la final

| Bloque | Entregable |
|---|---|
| Día 1, mañana | Calibrar parámetros con los datos que entregue la Caja y correr la simulación con su escala |
| Día 1, tarde | App web del asesor: ficha del cliente, propuesta, comparación fija/flexible y bitácora del agente |
| Día 2, mañana | App del cliente (aplazamiento y aviso El Niño) e integración con Fineract (real o API compatible) |
| Día 2, tarde | Tablero de simulación en vivo (cambiar parámetros y ver mora y margen), ensayo del pitch y video de respaldo |

Ya están construidos: el motor, la API, las pruebas y la simulación (este repositorio).

## 9. Diferenciación

- No es un tablero ni un chatbot: **decide** y **optimiza** el cronograma con restricciones de
  riesgo, y lo **demuestra** con una simulación causal.
- La incertidumbre forma parte del diseño (cuantiles y escenario conservador).
- La cláusula El Niño usa un disparador objetivo (la alerta del ENFEN) adaptado al norte del Perú.
- Está integrado con un core bancario de código abierto, no es una maqueta aislada.

## 10. Riesgos del proyecto y mitigación

| Riesgo | Mitigación |
|---|---|
| Muchos equipos eligen este reto | Diferenciarse con la optimización, el agente y la simulación causal |
| Instalar Fineract consume tiempo | Usar una API propia compatible, declarada en el concepto |
| Datos de la Caja incompletos | Usar el generador sintético calibrable y el perfil por rubro |
| Pronóstico errado | Diseñar contra el p25, aplicar un piso y techo, permitir aplazamientos y replanificar |

## 11. Pendientes con la organización

- Confirmar la fecha de entrega del concepto. Las bases indican del 20 al 24 de noviembre y el cronograma del 25 al 26 (cajathon@cajatrujillo.com.pe).
- Preguntar qué herramientas externas de asistencia se permiten (incluida la IA generativa).
- Tener en cuenta que lo construido durante el evento pasa a ser propiedad de la Caja si el equipo gana. El motor base que ya existe está declarado como desarrollo previo.

## Fuentes

Bases del Cajathón 2026 · J-PAL (contratos flexibles de BRAC) · Field et al. (periodo de gracia en India) ·
Barboni (flexibilidad y selección, JEBO) · Warwick (experimento con Sonata) · Shonchoy y Kurosaki (microcrédito
estacional) · Shopify Capital · GIZ y BASIS (seguro El Niño en el norte del Perú) · SBS (modelo de Finanzas Abiertas) ·
Fineract (Variable Installment Loans).
