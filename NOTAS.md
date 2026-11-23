# NOTAS del proyecto (leer primero al retomar)

## Decisiones
- Reto: NEG-01 Cuotas. Nombre de la solución: **CuotaFlex**.
- Integración: API propia compatible con Fineract (`src/cuotaflex/api/main.py`). Fineract real es opcional.
- Pronóstico por defecto en la simulación: `perfil`, por rapidez. El agente individual usa `mixto` (statsforecast + perfil).
- Diseño contra el escenario p25, con la cuota hasta el 70% del excedente.
- Simulación: `fuga_caja_mensual = 0.15` (el sobrante no se ahorra por completo). Sin fuga, la cuota estacional no aporta: es el supuesto clave y hay que validarlo con la Caja.

## Resultados vigentes (600 × 200, semilla 2026)
- Completo: atraso > 30 días 16.3% → 7.3%, default 8.5% → 3.4%, margen/cartera 16.5% → 22.7%, cartera -14%.
- Solo cronograma: atraso 16.3% → 14.3%, default 8.5% → 7.7%.

## Pendientes (detalle por fase en docs/fases/ROADMAP.md)
- [ ] Calibrar el umbral de estacionalidad: en calzado y comercio, el cronograma por sí solo empeora un poco.
- [x] Fase 1 integrada: app del asesor (5173), app del cliente (5174), tablero (5175) y Concept Solution (docs/concepto/).
- [ ] Confirmar la fecha de entrega del concepto y las herramientas de IA permitidas (cajathon@cajatrujillo.com.pe).
- [x] Concept Solution final en docs/concepto/ (exportado a PDF).

## Integración fase 1 (23 nov)
- 42 pruebas pasan; las 3 apps compilan.
- Prueba de punta a punta: el asesor registra, aprueba y desembolsa → el cliente ve el préstamo y la alerta El Niño → el tablero corre el escenario Base Estándar en ~9 s.
- Sin conflictos de fusión ni errores en consola.
