# Lista de verificación del Concept Solution

Estado al 23/11/2026. Cada criterio de la etapa de conceptos (bases, sección 5) con la sección que lo cubre y la evidencia que aporta.

## Criterios de evaluación

| Criterio (peso) | Dónde se cubre | Evidencia |
|---|---|---|
| **Impacto potencial (30%)**, en el KPI del desafío | Resumen ejecutivo · 3. Impacto esperado · Figura 1 | **Cifra:** atraso > 30 días de 16.3% a 7.3%, default de 8.5% a 3.4% y margen neto sobre cartera de 16.5% a 22.7% (`resultados/resumen.json`). **Prueba:** `tests/test_lote_d_concepto.py` comprueba que las cifras del documento coinciden con ese archivo. **Repo:** la simulación se reproduce con `python scripts/simular.py` (semilla 2026). Lectura honesta: efecto del dimensionamiento, −14% de cartera y supuesto de fuga de caja. |
| **Alineación al desafío (25%)** | 1. Problema abordado · 2. Concepto de solución · 8.2 Datos e insumos | **Cifra:** pregunta de innovación citada tal como está en el expediente NEG-01, estacionalidad de La Libertad y alerta vigente del ENFEN. **Repo:** reglas en `config/parametros.yaml`. Evidencia de seis experiencias (2.2), riesgos del expediente cubiertos (2.3) e insumos en el orden de la lista oficial (8.2). |
| **Viabilidad técnica (25%)** | 4. Enfoque tecnológico · 5. Tecnología preexistente · 8.1 Lo que ya funciona | **Prueba:** `pytest` cubre el optimizador, la elegibilidad, el agente, la simulación y la API. **Demo:** `python scripts/demo_agente.py 3` y la API en `/docs`. **Repo:** `src/cuotaflex/` y los diagramas `img/arquitectura.mmd` y `img/flujo-agente.mmd`. Licencias declaradas. |
| **Factibilidad de construcción (20%)** | 6. Funcionalidad crítica · 7. Nivel de desarrollo · 8.3 Plan · 8.4 Riesgos · 8.5 Equipo | **Repo:** fase 0 terminada y apps de la fase 1 en sus ramas (`fase-1/lote-a-asesor`, `lote-b-cliente`, `lote-c-tablero`). **Plan:** bloques de los dos días con responsable y plan B. **Equipo:** cuatro perfiles técnicos según la plataforma. |

## Componentes oficiales (bases, 3.3)

| Componente | Sección | Incluye del lote D |
|---|---|---|
| Problema abordado | 1 | Pregunta del reto, estacionalidad de La Libertad y riesgo de El Niño |
| Concepto de solución | 2 | Modalidades, reglas, evidencia, riesgos y cumplimiento |
| Impacto esperado | 3 | Tabla "completo" y "solo cronograma", lectura honesta y Figura 1 |
| Enfoque tecnológico | 4 | Componente avanzado, por qué no es chatbot ni tablero, arquitectura y flujo |
| Tecnología preexistente | 5 | Fases 0 y 1, licencias y propiedad intelectual |
| Funcionalidad crítica | 6 | Qué se construye en la fase presencial y caso de uso |
| Nivel de desarrollo esperado | 7 | Resultado al cierre de la hackathon |
| Factibilidad y dependencias | 8 | Datos solicitados, plan de dos días, riesgos y equipo |

El resumen ejecutivo va antes de la sección 1 y las fuentes al final. Así quedan cubiertas las 12 secciones que pide el lote, dentro de la estructura oficial.

## Criterios de aceptación del lote

- [x] Correo redactado, con fecha de seguimiento (25/11, 09:00). Falta enviarlo desde el correo de un integrante. Fecha: la plataforma abre la postulación del 25 al 26/11 y las bases decían del 20 al 24/11; falta confirmar la hora de cierre.
- [ ] El documento sigue la plantilla oficial sin pasarse de la extensión. Sigue los 8 componentes de las bases y ocupa 8 páginas en PDF. **Falta** contrastarlo con los campos del formulario de la plataforma, que se publican el 25/11.
- [x] Todas las cifras coinciden con `resultados/resumen.json`, verificado por `tests/test_lote_d_concepto.py`.
- [x] 3 diagramas en PNG con su fuente, y el script de figuras corre sin errores.
- [x] Resumen de una página y lista de verificación completos.
- [ ] El PDF está revisado (tablas, diagramas y tildes). **Falta** ajustarlo si el formulario de la plataforma pide otros campos o límites.
- [ ] Al menos un integrante que no lo escribió lo revisa.

## Pendientes antes de subir

1. Confirmar la hora de cierre del 26/11 (correo, WhatsApp del Cajathón o chat del owner).
2. El 25/11, copiar en `correo-organizacion.md` los campos del formulario y ajustar el documento si piden otros campos o límites.
3. Confirmar los responsables del plan de dos días (8.3) y que la funcionalidad crítica (6) se construirá en la fase presencial, porque las bases (5.2) exigen desarrollo nuevo en esas jornadas.
4. Completar, si el equipo quiere, la experiencia concreta de cada integrante (8.5): proyectos o trabajo relevante.
5. Declarar las herramientas de IA generativa según lo que responda la organización.
6. Revisión por un integrante que no lo escribió y nueva exportación del PDF.

## Cómo regenerar

Figura del cronograma, desde la raíz del repositorio:

```bash
pip install -r requirements.txt -r requirements-lote-d-concepto.txt
python docs/concepto/generar_figuras.py
```

Diagramas, desde `docs/concepto/img/` (requiere Node.js):

```bash
npx -y @mermaid-js/mermaid-cli -i arquitectura.mmd -o arquitectura.png -b white -s 2 -w 1500
npx -y @mermaid-js/mermaid-cli -i flujo-agente.mmd -o flujo-agente.png -b white -s 2 -w 1500
```

PDF, desde `docs/concepto/` (requiere pandoc, Google Chrome y la fuente Inter):

```bash
pandoc CONCEPT_SOLUTION.md -f gfm -t html5 -s --metadata pagetitle="CuotaFlex · Solution Concept" \
  --metadata lang=es --css export/estilo-pdf.css --embed-resources -o /tmp/concepto.html
google-chrome --headless --no-pdf-header-footer \
  --print-to-pdf=export/CuotaFlex-Solution-Concept.pdf /tmp/concepto.html
```

Si la plataforma pide Word, se exporta desde el mismo Markdown.
