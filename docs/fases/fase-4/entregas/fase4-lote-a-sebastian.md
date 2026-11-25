# CuotaFlex · Fase 4 · Lote A — para Sebastian

Hola Sebastian. Aquí está tu parte de la **fase 4: ajustar CuotaFlex a las preguntas frecuentes del NEG-01**, publicadas por la organización el 24 de noviembre en la plataforma (Desafíos → NEG-01 → Preguntas frecuentes). **Léelas primero, son 5 minutos.**

## Por qué hay una fase 4
Las FAQ dejan claro qué se evalúa:
- una herramienta del **Asesor de Negocios** que **estima el ciclo económico** del cliente (patrón de sector y zona con fuentes públicas, ajustado con la captura del asesor, **sin historial de pagos**);
- que en el mismo lugar **construye un plan nuevo** con cuotas y periodos variables, con **Cuota/UN ≤ factor en cada etapa**, TED base 360, seguros, prelación seguros → interés → capital, pendientes sin capitalizar y TCEA;
- una **vista para el Asesor de Riesgos y el comité**;
- la **comparación con la cuota fija en escenarios adversos**.

**No se medirá la mora de una cartera real.** Solo cuentan créditos nuevos, con el plan fijo desde el desembolso.

## Cómo trabajamos en esta fase
- **Contratos:** `docs/fases/fase-4/CONTRATOS.md` define qué recibe y qué devuelve cada pieza. Hay JSON de ejemplo en `tests/fixtures/contratos/` (caso Rosa) para no depender de los demás.
- **Plazo:** terminar antes del **30 de noviembre**, para integrar y ensayar el 1 y 2 de diciembre. La final es el **3 y 4 de diciembre**.

## Antes de empezar
```bash
git checkout main && git pull
pip install -r requirements.txt -r requirements-dev.txt
pytest                                    # deben pasar todas
git checkout -b fase-4/lote-a-plan
```
Al terminar: haz `git push -u origin fase-4/lote-a-plan` y **abre el Pull Request** a `main`.

---

## Fase 4 · Lote A — Motor financiero y constructor del plan por etapas

**Rama:** `fase-4/lote-a-plan`

## Objetivo
Que el plan se construya **desde el ciclo** con las reglas de la Caja (FAQ del NEG-01):
- cada cuota con su monto y su periodo, respetando **Cuota/UN ≤ factor en todas las etapas**;
- TED base 360 por días exactos, seguros, prelación seguros → interés → capital, pendientes sin capitalizar y TCEA;
- comparación con la cuota fija y prueba de estrés en escenarios adversos.

Hoy el plan adaptado todavía supera el factor de 0.85 en el 34% de los clientes, y en el 78–95% en agricultura y pesca. La meta es **0% por construcción**.

## Archivos (exclusivos)
- `src/cuotaflex/plan/**` (nuevo): `calendario.py`, `costos.py`, `prelacion.py`, `constructor.py`, `estres.py` y `tcea.py`
- `src/cuotaflex/api/routers/plan.py` (nuevo): `POST /plan/proponer`
- `src/cuotaflex/agente.py`: **solo** `proponer()`, para añadir un adaptador opcional hacia el plan nuevo
- `src/cuotaflex/politica.py` y `optimizador.py`
- `config/parametros.yaml`: nueva sección `productos` y `seguros`
- `scripts/factor_por_etapa.py`, `resultados/factor_por_etapa.*`
- `tests/test_fase4_a_*.py`

**Contrato:** `docs/fases/fase-4/CONTRATOS.md` §2. **No toques** `src/cuotaflex/ciclo/**` (lote B): consume el `ciclo` que llega en la solicitud.

## Tareas
1. **Calendario:** fechas de vencimiento mensuales a partir del desembolso, con los días exactos de cada periodo y fin de mes seguro (31 → 28/30). Soporta periodos de **otra periodicidad** si el constructor agrupa meses (por ejemplo, una cuota trimestral en la cosecha): un periodo puede abarcar varios meses del ciclo, y su UN es la suma de la UN de esos meses.
2. **Costos:** TED = (1+TEA)^(1/360) − 1. El interés del periodo es `saldo_capital × ((1+TED)^días − 1)`. Seguros con interés simple por días: desgravamen sobre `saldo_capital` y multirriesgo sobre `valor_asegurable`. Valida que la TEA sea ≤ `tope_tea`.
3. **Prelación y pendientes:** seguros → interés → capital, con pagos parciales; lo pendiente se arrastra en su concepto, **sin capitalizar**. Prueba de propiedad: la suma de pagos es igual a capital + interés + seguros generados, con tolerancia de 1 céntimo.
4. **Constructor del plan** (CVXPY/HiGHS o programación dinámica):
   - **Restricción dura:** cuota_t ≤ factor × UN_t, con UN_t ≤ 0 ⇒ cuota_t = 0.
   - La deuda queda en 0 al vencer el plazo.
   - Como máximo `max_meses_gracia` periodos con interés pendiente.
   - **Objetivo:** primero minimizar el costo total (interés + seguros), que equivale a amortizar el máximo en la cima. Luego, como segundo término, penalizar la gracia y los cambios bruscos entre periodos vecinos.
   - Si no hay solución: `factible=false` y `ajustes_sugeridos`, calculando por búsqueda binaria el **monto máximo** factible y el **plazo mínimo** factible.
   - Si el asesor usa un factor menor, se respeta.
5. **Cuota fija de referencia** con el mismo motor: cuota constante que cancela al final con días exactos y prelación. Así la comparación es justa.
6. **Estrés:** evalúa ambos planes contra cada `ciclo.escenarios[].un`: etapas sobre el factor, ratio máximo y monto sobre la capacidad.
7. **TCEA** por bisección sobre los flujos con días/360.
8. **Router** `POST /plan/proponer`, que respeta el contrato exacto y se valida contra `plan_proponer_respuesta.json` (mismas claves y tipos).
9. **Cifras para el concepto y el pitch** (`scripts/factor_por_etapa.py`): sobre los 600 clientes sintéticos (y los casos E001 a E003), compara la fija con el plan nuevo:
   - % de clientes con alguna etapa sobre el factor (0.65 y 0.85), en el escenario esperado y en los adversos;
   - interés total, TCEA y meses de gracia.

   Salida en `resultados/factor_por_etapa.md` y `.json`. **Pásale las cifras a Andre.**
10. **Compatibilidad:** `/motor/propuesta` y la app actual siguen funcionando. El plan nuevo vive en `/plan/proponer`.

## Pruebas
- Prelación, pendientes sin capitalizar y TED por días: casos calculados a mano, incluido un periodo de 31 días y otro de febrero.
- **Ningún plan factible tiene una etapa con Cuota/UN > factor** (prueba de propiedad sobre 200 ciclos sintéticos).
- No factible ⇒ hay `ajustes_sugeridos`, y aplicar el ajuste lo vuelve factible.
- Respuesta idéntica en forma a la del contrato.
- La TCEA de un plan sin seguros, con cuota fija y meses de 30 días, coincide con la TEA dentro de ±0.1 pp.
- Las pruebas existentes siguen pasando.

## Criterios de aceptación
- [ ] 0% de planes factibles con alguna etapa sobre el factor.
- [ ] Rosa (E001) recibe cuotas concentradas en la cosecha, gracia en la siembra, deuda en 0 al final y TCEA reportada.
- [ ] Luis (E003): con su factor no es factible al monto pedido, y el motor sugiere el monto máximo.
- [ ] `resultados/factor_por_etapa.md` con cifras entregado a Andre.

---

## Reglas para trabajar en paralelo

1. **Rama por lote:** `fase-4/lote-a-plan`, `fase-4/lote-b-ciclo`, `fase-4/lote-c-comite`, `fase-4/lote-d-pitch-agente`.
2. **Archivos exclusivos:** cada lote solo crea o modifica los archivos que su `.md` marca como suyos. Si necesitas tocar otro archivo, avísalo al equipo antes.
3. **Contratos primero:** todo lo que se pasa entre lotes sigue `docs/fases/fase-4/CONTRATOS.md`. Mientras otro lote no esté listo, se trabaja con los JSON de `tests/fixtures/contratos/`.
4. **Endpoints nuevos:** van en un archivo propio dentro de `src/cuotaflex/api/routers/`, con una variable `router`. La API lo registra sola, sin tocar `main.py`.
5. **Frontends:** cada uno vive en su carpeta dentro de `web/` con su propio `package.json`. Puertos fijos: asesor 5173, cliente 5174, tablero 5175. El CORS ya los permite.
6. **Dependencias de Python nuevas:** se agregan en `requirements-<lote>.txt`, no en `requirements.txt`. Se consolidan al cerrar la fase.
7. **Pruebas:** cada lote agrega `tests/test_<lote>.py`, y `pytest` debe pasar antes del PR.
8. **Datos:** solo sintéticos. Nunca datos reales de clientes.
9. **Commits:** a nombre de cada integrante, sin coautores automáticos.


10. **Commits desde tu propia cuenta de GitHub**, para la declaración de propiedad intelectual.
