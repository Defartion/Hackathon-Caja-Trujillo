# CuotaFlex · Fase 3 · Lote D — para Andre

Hola Andre. Aquí está tu parte de la **fase 3, la preparación de la final**. Trabajas en tu rama y en tus archivos.

## Dónde estamos
- **Fase 2 integrada en `main` (24 nov):** 111 pruebas pasan. Ya están la calibración con la SBS, la selección de producto por simulación, Fineract real (espejo), el ENFEN con notificaciones y el agente con herramientas y salvaguardas.
- **Cifras vigentes:** `resultados/CAMBIOS_FASE2.md`. Con la cuota fija, el default es 4.8%; con CuotaFlex, 2.1%. El margen sobre cartera pasa de 19.2% a 25.7%.
- **Hoy hay una Alerta de El Niño Costero vigente** del ENFEN: CuotaFlex responde a un riesgo real.
- **Plazo:** terminar antes del **1 de diciembre**. La final es el **3 y 4 de diciembre** en el Hub UPAO.

## Antes de empezar
```bash
git checkout main && git pull
pip install -r requirements.txt
pytest                                    # deben pasar 111 (2 omitidas)
git checkout -b fase-3/lote-d-pitch
```
Al terminar: haz `git push -u origin fase-3/lote-d-pitch` y **abre el Pull Request** a `main` con evidencias y la lista de criterios marcada.

---

## Fase 3 · Lote D — Pitch, concepto actualizado y banco de preguntas

**Rama:** `fase-3/lote-d-pitch`

## Objetivo
La final se evalúa así: impacto 35%, funcionamiento y demo 35%, innovación 20% y presentación 10%.
Este lote prepara **cómo contamos** CuotaFlex en 5 a 7 minutos y cómo respondemos al jurado, con las
**cifras calibradas de la fase 2**.

## Archivos de este lote (exclusivos)
- `docs/pitch/**` (nuevo)
- `docs/concepto/**`: versión 2 del concepto. **No borres ni modifiques** el concepto entregado (v1).
- `tests/test_lote_d_concepto.py` y `tests/test_fase3_d.py` (nuevo)

## Fuentes de cifras (usa solo estas)
- `resultados/resumen.json` y `resultados/CAMBIOS_FASE2.md`: cifras vigentes de la fase 2.
- `resultados/backtest.md` y `resultados/sensibilidad.md`: validación y robustez.
- `evaluacion/REPORTE.md`: exactitud del agente (lote D de la fase 2).
- `src/cuotaflex/integraciones/README_ENFEN.md`: estado oficial del ENFEN. Hoy hay una **Alerta de El Niño Costero vigente**, un dato muy fuerte para el pitch.

## Tareas

### 1. Concepto v2 (`docs/concepto/v2/`)
- Copia `CONCEPT_SOLUTION.md` y `one-pager.md` a `docs/concepto/v2/` y actualiza **todas las cifras** con la fase 2. Explica en una nota corta qué cambió y por qué (calibración con la SBS y selección por simulación).
- Regenera la figura 1 con `generar_figuras.py` usando el motor actual, y ajusta el texto de su leyenda.
- Exporta el PDF v2 a `docs/concepto/v2/export/`.
- **Pruebas:**
  - en `tests/test_lote_d_concepto.py` agrega pruebas equivalentes para v2, contra `resultados/resumen.json`;
  - **quita el `skip`** de la prueba de la figura 1 y apúntala a v2;
  - las de v1 siguen contra `resultados/fase1/`.

### 2. Presentación (`docs/pitch/`)
**10 a 12 láminas** en la herramienta que prefiera el equipo. Exporta el PDF a `docs/pitch/CuotaFlex-pitch.pdf` y guarda el archivo editable o su enlace en `docs/pitch/README.md`:
1. **Gancho:** Rosa, agricultora de Chepén. Paga lo mismo en siembra que en cosecha y se atrasa aunque su negocio es viable.
2. **El problema en cifras:** estacionalidad en La Libertad, mora de microempresa de cajas municipales (SBS) y Alerta de El Niño Costero vigente (ENFEN).
3. **La solución en una frase** y las modalidades.
4. **Cómo funciona:** pronóstico con incertidumbre → selección por simulación → cronograma optimizado → agente que explica.
5. **Demo** (lámina de transición; la demo va en vivo).
6. **Impacto:** tabla de cuota fija contra CuotaFlex, con default, atraso, margen y cartera. Explica con honestidad qué parte viene del cronograma y qué parte del dimensionamiento.
7. **Robustez:** el gráfico de sensibilidad, para responder "¿y si…?".
8. **Riesgo y cumplimiento:** capacidad de pago con el escenario p25, sobreendeudamiento, transparencia (TEA y costo del aplazamiento) y salvaguardas del agente.
9. **Integración real:** Fineract, ENFEN y la API.
10. **Por qué no es un tablero ni un chatbot:** decide, optimiza y verifica.
11. **Implementación en la Caja:** piloto por rubro y región, datos necesarios y siguientes pasos.
12. **Equipo.**

Reglas de estilo:
- Una idea por lámina, cifras grandes y fuente al pie.
- Sin logo de Caja Trujillo: la marca es CuotaFlex.

### 3. Guion (`docs/pitch/GUION.md`)
- Entre 5 y 7 minutos **cronometrados**, con quién habla en cada parte, el texto aproximado y las transiciones a la demo.
- La demo sigue los 3 casos estrella del lote B (pide a Joaquin sus IDs y su guion).
- Prepara una versión de 3 minutos, por si recortan el tiempo.

### 4. Banco de preguntas (`docs/pitch/PREGUNTAS.md`)
Al menos **20 preguntas** del jurado, cada una con una respuesta de 30 segundos y la cifra o evidencia que la respalda. Deben incluir:
- ¿Y si el pronóstico falla? → backtest y sensibilidad
- ¿Esto no aumenta el sobreendeudamiento? → política y reducción de monto
- ¿Cómo lo vería la SBS? ¿Es una reprogramación?
- ¿Por qué baja la cartera colocada? ¿No pierde la Caja?
- ¿Cuánto cuesta implementarlo? ¿Qué datos necesitan?
- ¿Qué pasa si no hay El Niño?
- ¿Por qué no basta un tablero o un chatbot?
- ¿El LLM puede inventar cifras?
- ¿Cómo se integra con el core actual de la Caja?
- ¿Qué parte construyeron antes y qué parte en el evento? (coordina con Stefano, lote C)

### 5. Resumen impreso (`docs/pitch/one-pager-final.pdf`)
Una página para entregar al jurado, con cifras v2 y un código QR al repo o a la demo desplegada. Pide la URL a Sebastian (lote A).

## Pruebas (`tests/test_fase3_d.py`)
- Toda cifra porcentual de `GUION.md` y `PREGUNTAS.md` existe en `resultados/resumen.json` o en `CAMBIOS_FASE2.md`, con tolerancia de redondeo.
- El PDF del pitch existe y tiene entre 10 y 12 páginas (`pypdf`).
- El concepto v2 cita las cifras vigentes y el v1 sigue intacto.

## Criterios de aceptación
- [ ] Concepto v2 con cifras de la fase 2, figura regenerada y la prueba de la figura reactivada.
- [ ] Pitch de 10 a 12 láminas en PDF, guion cronometrado (versiones de 5–7 y de 3 minutos) y 20 preguntas o más.
- [ ] Resumen impreso con QR.
- [ ] Ensayo con cronómetro grabado en audio y revisado por otro integrante.
- [ ] `pytest` pasa completo.

---

## Reglas para trabajar en paralelo

1. **Rama por lote:** `fase-3/lote-a-despliegue`, `fase-3/lote-b-qa`, `fase-3/lote-c-final`, `fase-3/lote-d-pitch`.
2. **Archivos exclusivos:** cada lote solo crea o modifica los archivos que su `.md` marca como suyos. Si necesitas tocar otro archivo, avísalo al equipo antes.
3. **Motor congelado:** en la fase 3 nadie edita `src/cuotaflex/*.py` del motor. Si encuentras un bug, avisa a Sebastian y se corrige aparte.
4. **Endpoints nuevos:** van en un archivo propio dentro de `src/cuotaflex/api/routers/`, con una variable `router`. La API lo registra sola, sin tocar `main.py`.
5. **Frontends:** cada uno vive en su carpeta dentro de `web/` con su propio `package.json`. Puertos fijos: asesor 5173, cliente 5174, tablero 5175. El CORS ya los permite.
6. **Dependencias de Python nuevas:** se agregan en `requirements-<lote>.txt`, no en `requirements.txt`. Se consolidan al cerrar la fase.
7. **Pruebas:** cada lote agrega `tests/test_<lote>.py`, y `pytest` debe pasar antes del PR.
8. **Datos:** solo sintéticos. Nunca datos reales de clientes.
9. **Commits:** a nombre de cada integrante, sin coautores automáticos.


10. **Commits desde tu propia cuenta de GitHub**: queda registrado quién hizo qué, y eso importa para la declaración de propiedad intelectual.
