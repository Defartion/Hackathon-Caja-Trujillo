# CuotaFlex · Fase 1 · Lote D — para Andre

Hola Andre. Este documento tiene todo lo que necesitas para tu parte. Trabajas solo en tu rama
y en tus archivos, así que no dependes de los demás lotes.

## Contexto en 30 segundos
Participamos en el **Cajathón 2026 de Caja Trujillo**, reto **NEG-01 "Cuotas que se adaptan al flujo
del negocio"**. Nuestra solución, **CuotaFlex**, es un motor con IA que:
- pronostica las ventas del microempresario con incertidumbre,
- elige la modalidad de pago (cuota fija, cuota con aplazamientos o cuota estacional, más un alivio cuando el ENFEN declara El Niño costero),
- optimiza el cronograma sin que la Caja pierda rentabilidad,
- y demuestra el impacto en mora y rentabilidad con una simulación de miles de escenarios.

La **fase 0** (motor, API compatible con Fineract, simulación y pruebas) ya está construida y en el repositorio.

## Antes de empezar
1. Acepta la invitación de colaborador al repo privado **github.com/Defartion/Hackathon-Caja-Trujillo**.
2. Prepara el entorno:
```bash
git clone https://github.com/Defartion/Hackathon-Caja-Trujillo.git
cd Hackathon-Caja-Trujillo
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                                                 # deben pasar todas
git checkout -b fase-1/lote-d-concepto
```
3. Lee `README.md` y `NOTAS.md` (5 minutos). Para entender el motor, mira `src/cuotaflex/agente.py`.
4. Al terminar: haz `push` de tu rama y abre un Pull Request a `main` con capturas y la lista de criterios marcada.

---

## Fase 1 · Lote D — Concept Solution final

**Rama:** `fase-1/lote-d-concepto`
**Prioridad: urgente.** Según el análisis de desafíos, las bases fijan la entrega del concepto del
20 al 24 de noviembre, mientras que el cronograma dice del 25 al 26. Lo primero es confirmar la fecha.

## Objetivo
Entregar en la plataforma del Cajathón un concepto que maximice la clasificación:

| Criterio | Peso |
|---|---|
| Impacto en el KPI | 30% |
| Alineación con el desafío | 25% |
| Viabilidad técnica | 25% |
| Capacidad de construir | 20% |

Viabilidad y capacidad suman 45%. Por eso el documento tiene que demostrar que la base ya
funciona y que el plan para los dos días es realista.

## Archivos de este lote (exclusivos)
- `docs/concepto/**` (nuevo): documento final, diagramas, resumen de una página y correo
- `docs/CONCEPTO.md`: este lote es su único dueño. Al terminar, el archivo queda solo como un puntero a `docs/concepto/`.

No modifiques código. Las cifras salen de `resultados/resumen.json`, que ya está en el repo.

## Tareas

### 1. Confirmar condiciones con la organización (día 1)
Redacta `docs/concepto/correo-organizacion.md` para cajathon@cajatrujillo.com.pe, con estas preguntas:
1. ¿Cuál es la fecha y hora límite de entrega del Concept Solution?
2. ¿Qué formato y extensión máxima tiene? ¿Hay plantilla oficial?
3. ¿Qué herramientas externas de asistencia se permiten, incluida la IA generativa, y cómo se declaran?
4. ¿La Caja ya ofrece cuotas estacionales o pago a cosecha?
5. ¿Qué datos podría compartir para el prototipo (historial anonimizado, políticas de capacidad de pago)?
6. ¿Puede el equipo usar componentes desarrollados antes del evento si se declaran como tecnología existente?

El equipo lo envía desde su correo; no lo envía nadie de forma automática. Además, revisa la sección
"Concepto de solución" en https://cajathon.cajatrujillo.com.pe/equipos/ (requiere iniciar sesión) y
copia aquí la plantilla o la lista de campos exactos que pide.

### 2. Documento final: `docs/concepto/CONCEPT_SOLUTION.md`
Parte del borrador `docs/CONCEPTO.md` y ajústalo **a la estructura oficial** si existe. Si no
existe, usa estas secciones, en este orden:

1. **Resumen ejecutivo** (máximo 150 palabras): problema, solución, impacto en números y por qué se puede construir.
2. **Pregunta del reto y problema**: cita la pregunta oficial; describe la estacionalidad de La Libertad (agro, pesca, campañas, calzado) y el riesgo de El Niño.
3. **Solución CuotaFlex**: las modalidades, las reglas y la evidencia (BRAC, Kolkata, Sonata, Bangladesh, Shopify y Caja Nuestra Gente).
4. **Componente tecnológico avanzado**: pronóstico probabilístico, optimización entera mixta (MILP), agente que replanifica y explica, simulación Monte Carlo causal e integración con Fineract. Deja explícito por qué **no** es un chatbot ni un tablero.
5. **Impacto en los indicadores**: la tabla de `resultados/resumen.json` con las variantes "completo" y "solo cronograma", leída con honestidad:
   - La mayor parte del efecto viene de dimensionar bien el monto y el plazo.
   - La cartera colocada baja 14%.
   - El supuesto clave es el gasto del sobrante mensual (`fuga_caja_mensual`).
6. **Gestión de riesgos y cumplimiento**: capacidad de pago con el escenario p25, sobreendeudamiento, rentabilidad (el valor presente se cierra), transparencia (cronograma y TCEA antes de firmar) y lo que falta validar con la Caja y la SBS.
7. **Datos e insumos que se solicitan a la Caja**, sección por sección, siguiendo la lista oficial del reto: flujos de ingresos, estacionalidad, historial de pagos, condiciones crediticias, tasas y plazos, políticas de riesgo y datos sintéticos.
8. **Arquitectura e integración**: un diagrama.
9. **Plan de los dos días de la final**: bloques, responsables y plan B.
10. **Equipo y roles**: nombre, rol y experiencia relevante de cada integrante. Pídeselo al equipo.
11. **Tecnología existente declarada y propiedad intelectual**: qué se construyó antes del evento (la fase 0 y la fase 1) y qué se construirá durante el evento; todas las librerías de código abierto con su licencia.
12. **Fuentes**.

**Reglas de redacción**
- Español claro y sin relleno. Cada cifra con su fuente.
- Sin promesas: los resultados son "en simulación con datos sintéticos".
- Respeta la extensión máxima oficial; si no hay, que quepa en 6 a 8 páginas en PDF.

### 3. Diagramas: `docs/concepto/img/`
- `arquitectura.png`: app del asesor y app del cliente → API → agente (pronóstico, políticas, optimizador) → Fineract, más el disparador del ENFEN.
- `flujo-agente.png`: elegibilidad → pronóstico → producto → optimización → ¿cabe? (si no, ampliar plazo o reducir monto) → validación → explicación.
- `cronograma-ejemplo.png`: cuota fija contra cuota estacional de un agricultor sobre la capacidad mensual. Se genera con un script `docs/concepto/generar_figuras.py` (matplotlib) que use `cuotaflex.agente` y una semilla fija.
- Guarda el código fuente de los diagramas, en Mermaid o draw.io, junto al PNG.

### 4. Resumen de una página: `docs/concepto/one-pager.md`
Problema, solución, tres cifras de impacto, la diferenciación y el equipo. Sirve para la plataforma y como portada del pitch.

### 5. Exportación
- Exporta `CONCEPT_SOLUTION.md` al formato que pida la plataforma (PDF o Word) en `docs/concepto/export/`.
- Revisa que tablas, diagramas y tildes se vean bien en el archivo exportado.

### 6. Lista de verificación contra los criterios: `docs/concepto/checklist.md`
Por cada criterio de evaluación, anota qué sección lo cubre y qué evidencia aporta: cifra, demo, prueba o enlace al repo.

## Criterios de aceptación
- [ ] Correo redactado y fecha límite confirmada (o con fecha de seguimiento).
- [ ] El documento sigue la plantilla oficial, o las 12 secciones si no la hay, sin pasarse de la extensión.
- [ ] Todas las cifras coinciden con `resultados/resumen.json`.
- [ ] 3 diagramas en PNG con su fuente, y el script de figuras corre sin errores.
- [ ] Resumen de una página y lista de verificación completos.
- [ ] El archivo exportado está revisado y listo para subir.
- [ ] Al menos un integrante que no lo escribió lo revisa.

## Fuera de alcance
El pitch y el guion de la demo (fase 3, lote B). Cambios en el motor o en las cifras: si se
recalibra, eso ocurre en la fase 2 y el concepto se actualiza después.

---

## Reglas para trabajar en paralelo

1. **Rama por lote:** `fase-1/lote-a-asesor`, `fase-1/lote-b-cliente`, `fase-1/lote-c-tablero`, `fase-1/lote-d-concepto`.
2. **Archivos exclusivos:** cada lote solo crea o modifica los archivos que su `.md` marca como suyos. Si necesitas tocar otro archivo, avísalo al equipo antes.
3. **Nada de cambios en el motor (`src/cuotaflex/*.py`) en la fase 1.** El motor de la fase 0 se consume, no se edita. Si encuentras un bug, abre un issue y se corrige en un PR aparte.
4. **Endpoints nuevos:** van en un archivo propio dentro de `src/cuotaflex/api/routers/`, con una variable `router`. La API lo registra sola, sin tocar `main.py`.
5. **Frontends:** cada uno vive en su carpeta dentro de `web/` con su propio `package.json`. Puertos fijos: asesor 5173, cliente 5174, tablero 5175. El CORS ya los permite.
6. **Dependencias de Python nuevas:** se agregan en `requirements-<lote>.txt`, no en `requirements.txt`. Se consolidan al cerrar la fase.
7. **Pruebas:** cada lote agrega `tests/test_<lote>.py`, y `pytest` debe pasar antes del PR.
8. **Datos:** solo sintéticos. Nunca datos reales de clientes.
9. **Commits:** a nombre de cada integrante, sin coautores automáticos.

## Identidad visual común (para los lotes A, B y C)

Cada app copia estos tokens en su propio CSS, así ninguna depende de las otras:

```css
:root {
  --cf-rojo: #C8102E;       /* acento institucional */
  --cf-rojo-osc: #8E0B20;
  --cf-gris-900: #1F2328;
  --cf-gris-600: #57606A;
  --cf-gris-200: #E5E7EB;
  --cf-fondo: #F7F7F8;
  --cf-verde: #1A7F37;      /* mejora / al día */
  --cf-ambar: #B7791F;      /* alerta / temporada baja */
  --cf-azul: #0B5CAD;       /* cuota flexible en gráficos */
  --cf-radio: 10px;
  --cf-fuente: "Inter", system-ui, sans-serif;
}
```

No uses el logo de Caja Trujillo ni imites sus pantallas reales. La marca de la solución es "CuotaFlex".
