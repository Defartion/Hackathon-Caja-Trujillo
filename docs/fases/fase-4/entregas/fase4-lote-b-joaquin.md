# CuotaFlex · Fase 4 · Lote B — para Joaquin

Hola Joaquin. Aquí está tu parte de la **fase 4: ajustar CuotaFlex a las preguntas frecuentes del NEG-01**, publicadas por la organización el 24 de noviembre en la plataforma (Desafíos → NEG-01 → Preguntas frecuentes). **Léelas primero, son 5 minutos.**

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
git checkout -b fase-4/lote-b-ciclo
```
Al terminar: haz `git push -u origin fase-4/lote-b-ciclo` y **abre el Pull Request** a `main`.

---

## Fase 4 · Lote B — Modelo del ciclo económico (sector × zona + captura del asesor)

**Rama:** `fase-4/lote-b-ciclo`

## Objetivo
Uno de los criterios de evaluación es la **precisión y sustento del modelo de ciclo**. Según las FAQ:
- la Caja **no entregará datos**;
- el ciclo **no debe basarse en el historial de pagos**;
- hay que **modelar el patrón del sector y la zona con fuentes públicas y ajustarlo a cada cliente** con lo que levanta el asesor.

Este lote reemplaza nuestra dependencia de "24 meses de ventas en la Caja", que no existen.

## Archivos (exclusivos)
- `src/cuotaflex/ciclo/**` (nuevo): `catalogo.py`, `estimador.py`, `escenarios.py` y `validacion.py`
- `data/ciclos/**` (nuevo): tablas de patrones por sector, actividad y zona, con su fuente
- `src/cuotaflex/api/routers/ciclo.py` (nuevo): `POST /ciclo/estimar` y `GET /ciclo/catalogo`
- `docs/ciclo/FUENTES.md` (nuevo)
- `tests/test_fase4_b_*.py`

**Contrato:** `docs/fases/fase-4/CONTRATOS.md` §1. **No toques** `src/cuotaflex/plan/**` ni el motor actual.

## Tareas
1. **Catálogo de patrones** (`data/ciclos/`): por lo menos estas actividades en La Libertad (provincias de Trujillo, Chepén, Pacasmayo, Virú, Ascope y Sánchez Carrión):
   - **Agro:** arroz, caña de azúcar, espárrago, palta y papa de sierra.
   - **Pesca:** artesanal, con temporadas y vedas.
   - **Comercio de campaña:** escolar, Fiestas Patrias y Navidad.
   - **Calzado** (El Porvenir), **bodega**, **restaurante** y **transporte**.

   Cada patrón trae un índice mensual normalizado a media 1, meses de cima y valle, volatilidad típica y la **fuente con fecha**: MIDAGRI (calendario de siembras y cosechas, series de producción), PRODUCE o IMARPE (temporadas y vedas), INEI y BCRP (series sectoriales y de precios) y calendarios comerciales. Si una cifra es un supuesto propio, se marca como **supuesto** y se dice por qué.
2. **`docs/ciclo/FUENTES.md`:** tabla de fuentes con qué dato se tomó, de dónde, cuándo y cómo se transformó. Es la evidencia de "sustento" para el jurado.
3. **Estimador:**
   - **Base:** patrón del sector × zona.
   - **Ajuste al cliente** con la captura: ventas en meses alto, normal y bajo, y qué meses son altos y bajos. Si el asesor marca meses distintos al patrón, prevalece el cliente, y queda registrado en `supuestos`.
   - **UN** = ventas × (1 − costo de ventas) − gastos operativos − tributarios − carga familiar − otras deudas.
   - Si hay **evidencias** (Yape o boletas), se usan para acotar el nivel de ventas.
   - **Incertidumbre:** cuantiles p10, p50 y p90 calibrados.
4. **Etapas:** `cima`, `normal` y `valle` según la UN esperada frente a la mediana del cliente (umbrales configurables).
5. **Escenarios adversos:** `base`, `el_nino` (caída por sector y zona, a partir de El Niño 2017 y 2023 con fuente SENAMHI o ENFEN y datos sectoriales), `retraso_cosecha` o `veda_extendida` según el sector, y `caida_precios`. Cada uno con su supuesto escrito.
6. **Validación** (`validacion.py` y `resultados/ciclo_validacion.md`):
   - Backtest sobre clientes sintéticos generados con ruido alrededor de los patrones: cobertura p10–p90 (objetivo ~80%) y MAPE de p50.
   - Coherencia: la suma de la UN anual es compatible con la captura.
   - Sensibilidad a errores de captura de ±20%.
7. **API:** `POST /ciclo/estimar`, idéntico al contrato (se valida contra `ciclo_estimar_respuesta.json`). `GET /ciclo/catalogo` devuelve las actividades y zonas disponibles para el formulario de la app.

## Pruebas
- Las respuestas tienen exactamente la forma del contrato.
- Las mismas entradas dan las mismas salidas (semilla fija).
- Arroz en Chepén: cima en jun–jul y valle en ene–mar. Pesca: valle en los meses de veda.
- Si el asesor indica otros meses altos, el ciclo los respeta.
- No se lee ningún campo de historial de pagos (prueba que falla si aparece `dias_atraso` en el flujo).

## Criterios de aceptación
- [ ] Al menos 12 actividades × zonas, con fuente o supuesto documentado.
- [ ] Cobertura del backtest de 75% a 85% y MAPE reportado.
- [ ] Los 3 casos estrella (E001 arroz en Chepén, E002 pesca en Pacasmayo, E003 bodega en Trujillo) con captura de ejemplo y ciclo coherente.
- [ ] `FUENTES.md` listo para citar en el concepto y el pitch.

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
