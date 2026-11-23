# Hoja de ruta de CuotaFlex

Cada fase tiene 4 lotes (A, B, C, D) **independientes**: cada uno se trabaja en su propia rama y
toca solo sus propios archivos, así que se pueden fusionar en cualquier orden sin conflictos.

| Fase | Objetivo | Lotes |
|---|---|---|
| **0 · Base** (hecha) | Motor, API compatible con Fineract, simulación, pruebas, concepto preliminar | — |
| **1 · Demo funcional y concepto** (integrada ✅) | Que el jurado pueda *ver y usar* la solución y que el concepto esté listo para entregarse | A App del asesor · B App del cliente · C Tablero de simulación en vivo · D Concept Solution final |
| **2 · Calidad e integración** (en curso, ver `docs/fases/fase-2/`) | Modelo calibrado e integración con sistemas reales | A Calibración y backtesting · B Fineract real (Docker) · C Disparador ENFEN y notificaciones · D Agente con LLM y guardrails |
| 3 · Final (3 y 4 de diciembre) | Entregable de la final pulido y desplegado | A Persistencia, roles y despliegue · B Pitch y guion de demo · C QA de punta a punta y datos de demo · D Video de respaldo y ensayo |

Los lotes de las fases 2 y 3 se detallan al cerrar la fase anterior.

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
