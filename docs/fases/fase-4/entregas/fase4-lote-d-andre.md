# CuotaFlex · Fase 4 · Lote D — para Andre

Hola Andre. Aquí está tu parte de la **fase 4: ajustar CuotaFlex a las preguntas frecuentes del NEG-01**, publicadas por la organización el 24 de noviembre en la plataforma (Desafíos → NEG-01 → Preguntas frecuentes). **Léelas primero, son 5 minutos.**

> **Antes que nada:** lee `entregas/URGENTE-concepto-v3-andre.md`. El concepto se sube **hasta el jueves 26**.

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
git checkout -b fase-4/lote-d-pitch-agente
```
Al terminar: haz `git push -u origin fase-4/lote-d-pitch-agente` y **abre el Pull Request** a `main`.

---

## Fase 4 · Lote D — Concepto v3, pitch alineado a las FAQ y agente para el comité

**Rama:** `fase-4/lote-d-pitch-agente` (el concepto v3 va antes en `concepto/v3`; ver `entregas/URGENTE-concepto-v3-andre.md`)

## Objetivo
1. **Hoy:** concepto v3 subido a la plataforma antes del cierre del jueves 26. Ver la guía urgente.
2. **Después:**
   - pitch y banco de preguntas alineados a cómo se evaluará: precisión del ciclo, ajuste cronograma-ciclo, Cuota/UN por etapa, estrés frente a la cuota fija, costos y adaptabilidad;
   - el agente pasa a **explicar el plan al asesor y al comité** usando el nuevo contrato, con **LLM externo vía API**, que las FAQ permiten para la demo.

## Archivos (exclusivos)
- `docs/concepto/v3/**` y `docs/pitch/**` (versión 2 del pitch: `CuotaFlex-pitch-v2.pdf`, `GUION.md` y `PREGUNTAS.md`)
- `src/cuotaflex/agente_chat/herramientas_plan.py` (nuevo) y `src/cuotaflex/explicador.py`
- `src/cuotaflex/api/routers/agente_chat.py`: solo para agregar los endpoints nuevos
- `web/asesor/src/components/ChatAgente.tsx`
- `evaluacion/**`
- `tests/test_fase4_d_*.py`, más las pruebas del concepto (v3)

**Contrato:** `docs/fases/fase-4/CONTRATOS.md`. Para trabajar sin esperar a A y B, usa los JSON de `tests/fixtures/contratos/`.

## Tareas
1. **Concepto v3:** según la guía urgente, subido a la plataforma. Cuando el lote A entregue `resultados/factor_por_etapa.md`, se actualizan las cifras en el pitch, no en el concepto ya subido.
2. **Pitch v2** (10 a 12 láminas):
   - **Gancho:** Rosa paga lo mismo en siembra que en cosecha.
   - **Problema:** ingreso promedio único y core solo con cuota fija.
   - **Solución:** ciclo, plan y comité.
   - **Demo.**
   - **Evidencia:**
     - precisión del ciclo con su backtest y fuentes;
     - Cuota/UN por etapa, fija contra adaptado;
     - estrés en escenarios adversos;
     - costo e interés, más TCEA.
   - **Por qué no es un tablero ni un chatbot:** optimización con restricciones, modelo de ciclo y agente que verifica.
   - **Implementación en la Caja:** solo parámetros por producto, sin datos internos, y el core no necesita cambios para el piloto.
   - **Equipo.**
   - **Quita el titular de mora de cartera.**
3. **Preguntas** (actualiza el banco):
   - ¿Por qué no usan el historial de pagos?
   - ¿Qué pasa si la UN de una etapa es negativa?
   - ¿La gracia encarece el crédito?
   - ¿Cómo se calcula la TCEA?
   - ¿Qué pasa si el asesor se equivoca en la captura?
   - ¿Cómo se valida el ciclo sin datos de la Caja?
   - ¿Qué cambia en el core para implementarlo?
4. **Herramientas nuevas del agente** (`herramientas_plan.py`), que leen el ciclo y el plan del contrato:
   - `explicar_etapa(n)`: por qué esa cuota en esa etapa (UN, factor, prelación);
   - `comparar_con_fija()`;
   - `probar_escenario(id)`: lee `estres`;
   - `justificar_ante_comite()`: un texto breve con cifras verificadas;
   - `que_pasa_si(monto | plazo | factor)`: llama a `/plan/proponer`, o al mock si no hay API.

   Salvaguarda numérica igual que hoy: toda cifra sale del contrato o de una herramienta.
5. **Endpoint** `GET /agente/explicacion-comite` (o un POST con el plan) para la vista del comité del lote C.
6. **LLM externo para la demo:** activar el proveedor real con las variables del `.env.example`. Probar latencia y costo con los 30 casos de evaluación, dejar un modo sin conexión con plantillas y **no subir claves**.
7. **Evaluación:** 20 casos nuevos sobre el plan (cifras 100% verificadas, herramienta correcta y nada prohibido), en `evaluacion/REPORTE_FASE4.md`.

## Criterios de aceptación
- [ ] Concepto v3 subido a la plataforma (captura de la confirmación en `docs/concepto/v3/`).
- [ ] Pitch v2, guion y preguntas actualizados y ensayados con cronómetro.
- [ ] El agente explica el plan y el estrés con cifras verificadas, con y sin LLM.
- [ ] `pytest` pasa completo.

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
