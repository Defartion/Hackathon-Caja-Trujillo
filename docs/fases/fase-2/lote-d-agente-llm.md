# Fase 2 · Lote D — Agente con IA generativa y salvaguardas

**Rama:** `fase-2/lote-d-agente`

## Objetivo
El reto pide "IA, agentes inteligentes" con **valor real** y descarta los chatbots genéricos. Este
lote convierte la explicación y la interacción del asesor en un agente que **usa las herramientas del
motor** (recalcular, simular, consultar políticas) y que **no puede inventar cifras**: cada número
que dice se verifica contra el motor.

## Antes de empezar
Confirma con la organización (correo de la fase 1) si se permite la IA generativa y cómo se declara.
Mientras tanto, construye todo con **respaldo sin LLM**, para que la demo funcione en cualquier caso.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/explicador.py` (nuevo)
- `src/cuotaflex/agente_chat/**` (nuevo): orquestador, herramientas y salvaguardas
- `src/cuotaflex/agente.py`: **solo el método `explicar()` y las funciones `_explicacion_plantilla` y `_explicacion_llm`**. `proponer()` es del lote A.
- `src/cuotaflex/api/routers/agente_chat.py` (nuevo)
- `web/asesor/src/components/ChatAgente.tsx` (nuevo) y una línea en `web/asesor/src/pages/Ficha.tsx` para insertarlo
- `evaluacion/**` (nuevo) y `tests/test_fase2_d.py` (nuevo)
- `requirements-fase2-d.txt` (por ejemplo, `anthropic` u otro SDK)

## Tareas

### 1. Explicador (`explicador.py`)
- `explicar(propuesta, elegibilidad, audiencia="cliente"|"asesor", usar_llm=None) -> {"texto", "fuente": "llm"|"plantilla", "cifras_verificadas": bool}`
- La **plantilla** actual se mueve aquí como respaldo y se mejora con dos tonos:
  - **Cliente:** español sencillo, tuteo, sin jerga, de 4 a 5 frases.
  - **Asesor:** técnico y breve, con riesgos y motivos de la decisión.
- **LLM:** proveedor configurable por entorno (`CUOTAFLEX_LLM_PROVEEDOR`, `CUOTAFLEX_LLM_MODELO`, clave API). Se le pasa **solo** la propuesta en JSON y el borrador de la plantilla. Temperatura baja y tiempo máximo de 8 s.
- **Salvaguarda numérica:** extrae todos los números del texto del LLM (montos, porcentajes, meses y plazos) y verifica que cada uno exista en la propuesta, con tolerancia de redondeo. Si alguno no existe, se descarta el texto y se usa la plantilla (`cifras_verificadas: false` en el registro).
- **Salvaguarda de cumplimiento:** el texto para el cliente debe mencionar la TCEA o TEA y, si hay aplazamientos, que tienen costo. Prohibido: "aprobado", "garantizado" o promesas de resultados. Si falla, se usa la plantilla.
- `agente.explicar()` pasa a llamar a `explicador.explicar(...)["texto"]`, con el mismo resultado de tipo `str`.

### 2. Chat del asesor con herramientas (`agente_chat/`)
Es un orquestador con **uso de herramientas**: el LLM decide qué herramienta usar y no responde de memoria. Herramientas:

| Herramienta | Qué hace |
|---|---|
| `recalcular_propuesta(monto?, plazo?, ajuste_asesor?)` | Llama a `AgenteAsesor.proponer` con los cambios |
| `simular_cliente(propuesta)` | Riesgo fija vs. CuotaFlex, igual que `/motor/propuesta` |
| `consultar_politica(tema)` | Devuelve los parámetros vigentes de `config` sobre el tema |
| `explicar_paso_bitacora(indice)` | Explica un paso de la bitácora |

- La sesión de chat guarda el cliente y la propuesta actual. Máximo 4 llamadas a herramientas por pregunta.
- **Toda cifra de la respuesta sale de una herramienta.** Aplica la misma salvaguarda numérica que el explicador sobre la unión de los resultados de las herramientas.
- **Respaldo sin LLM:** un enrutador por palabras clave para las 5 preguntas más comunes ("¿por qué bajó el monto?", "¿y a 24 meses?", "¿por qué este producto?", "¿qué pasa si hay El Niño?", "¿cuánto le cuesta el aplazamiento?"), que responde con plantillas y herramientas.

### 3. API (`routers/agente_chat.py`, prefijo `/agente`)
- `POST /agente/sesion`: recibe el cliente (mismo formato que `/motor/propuesta`) y devuelve `sesion_id` y la propuesta.
- `POST /agente/sesion/{id}/mensaje` con `{texto}`: devuelve `{respuesta, herramientas_usadas: [...], cifras_verificadas, fuente, propuesta_actualizada?}`.
- `GET /agente/explicacion?audiencia=` sobre la propuesta de la sesión.

### 4. Interfaz en la app del asesor (`ChatAgente.tsx`)
- Panel lateral plegable en la ficha, con el título "Pregúntale al agente".
- Botones con las 5 preguntas frecuentes y un campo libre.
- Cada respuesta muestra las herramientas usadas como pequeños distintivos ("recalculó a 24 meses") y un ✓ de "cifras verificadas".
- Si la respuesta trae una propuesta nueva, ofrece el botón "Aplicar a la ficha" (por ahora basta con mostrarla).
- Inserta el componente con **una sola línea** en `Ficha.tsx`.

### 5. Evaluación (`evaluacion/`)
- `casos.jsonl`: 30 casos (cliente, pregunta y lo esperado: herramienta correcta, cifras clave y frases prohibidas).
- `evaluar.py`: corre los casos con y sin LLM y reporta:
  - exactitud de cifras (debe ser 100%, por la salvaguarda);
  - herramienta correcta (%);
  - cumplimiento (%);
  - latencia p50 y p95;
  - costo estimado por consulta.
- Resultado en `evaluacion/REPORTE.md`. **Es evidencia de "IA con valor real" para el jurado.**

## Pruebas (`tests/test_fase2_d.py`)
Usa un LLM **simulado** (stub), sin red ni claves:
- Un texto del LLM con una cifra inventada se descarta y se usa la plantilla.
- Un texto que dice "aprobado" se descarta.
- Sin clave API, todo funciona con la plantilla y el enrutador.
- La sesión de chat recalcula a 24 meses cuando se le pide y devuelve la propuesta nueva.
- `agente.explicar()` sigue devolviendo `str`, y **las pruebas existentes siguen pasando**.

## Criterios de aceptación
- [ ] Explicación en dos tonos, con salvaguardas y respaldo.
- [ ] Chat con herramientas funcionando en la app del asesor, con y sin LLM.
- [ ] Reporte de evaluación con 100% de exactitud en cifras.
- [ ] Ninguna clave API en el repo (solo `.env.example`).
- [ ] `pytest` pasa completo sin red.
