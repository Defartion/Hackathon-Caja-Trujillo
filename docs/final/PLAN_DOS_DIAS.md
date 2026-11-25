# Plan de los dos días de la final

**Jueves 3 y viernes 4 de diciembre de 2026 · Hub UPAO.** Es la base para ajustar con el cronograma
oficial cuando la organización lo publique. Las horas suponen una presentación el viernes a las **15:00**;
si cambia, se mueve todo el día 2 manteniendo la regla de oro.

> **Regla de oro:** desde 3 horas antes de presentar **no se cambia código**, solo datos y textos.
> Con presentación a las 15:00, el código se congela a las **12:00** del viernes.

## Quién lleva qué

| Persona | Responsabilidad durante la final |
|---|---|
| **Sebastian** | Recalibración con datos de la Caja, motor del módulo en vivo y despliegue |
| **Joaquin** | Integración, pruebas de punta a punta, casos estrella y app del cliente |
| **Stefano** | API del módulo, controles de tiempo, verificación de las laptops, contingencias y video |
| **Andre** | Pitch, ensayos, presentación y app del asesor |

## Día 1 · jueves 3 de diciembre

| Hora | Bloque | Qué se hace | Responsable |
|---|---|---|---|
| 7:30–8:30 | Llegada | Armar la mesa con la [lista de verificación](CHECKLIST.md). `verificar_entorno` en las dos laptops: todo en verde | Stefano |
| 8:30–9:00 | Apertura | Escuchar las reglas, anotar horarios oficiales y ajustar este plan | Todos |
| 9:00–12:30 | **Mañana** | Recibir los datos o parámetros de la Caja, recalibrar `parametros.yaml` y volver a correr la simulación (`scripts/simular.py`) | **Sebastian** |
| 9:00–12:30 | Mañana (en paralelo) | Joaquin: que los casos estrella sigan dando su resultado con la recalibración. Andre: cifras nuevas en el pitch y el guion. Stefano: contrato JSON de la API del módulo, esqueleto de pruebas y apoyo a la simulación | Joaquin, Andre, Stefano |
| 12:30–13:30 | Almuerzo | Control de las 12:30 antes de comer | Todos |
| 13:30–18:00 | **Tarde** | Construir el módulo en vivo, horas 0 a 4.5 del [plan del módulo](MODULO_EN_VIVO.md#8-plan-de-implementación-8-horas-efectivas): motor y API más los dos frontends | **Todos** |
| 18:00–19:00 | Cierre | Fusionar a `main` lo que funciona, `pytest` completo, desplegar, etiqueta `final-dia1` y plan del día 2 | Joaquin y Sebastian |

## Día 2 · viernes 4 de diciembre

| Hora | Bloque | Qué se hace | Responsable |
|---|---|---|---|
| 8:00–8:30 | Arranque | Reunión de 10 minutos, `verificar_entorno` y revisión de la versión desplegada | Stefano |
| 8:30–12:00 | **Mañana** | Integrar el módulo (horas 4.5 a 8): tablero y comparación, pruebas de punta a punta y casos estrella | **Joaquin** |
| **12:00** | **Congelamiento** | Etiqueta `final-presentacion`. Desde aquí solo datos y textos | Joaquin |
| 12:00–13:00 | Ensayo 1 | Pitch completo con cronómetro y demo en vivo sobre la etiqueta congelada; anotar tiempos | **Andre** |
| 13:00–14:00 | Ajustes y ensayo 2 | Ajustar textos y datos, segundo ensayo cronometrado y volver a grabar el video de respaldo si cambió la interfaz | Andre y Stefano |
| 14:00–14:45 | Escenario | Probar el proyector, el adaptador y el sonido; dejar abierto el modo sin conexión y el video en el USB | Stefano |
| **15:00** | **Presentación** | Pitch de 5 a 7 minutos y preguntas | **Andre** |

## Controles cada 2 horas: "¿vamos a tiempo?"

Cinco minutos, de pie. Cada persona dice qué terminó, qué sigue y qué la bloquea. Stefano anota el resultado
en el canal del equipo.

| Control | Pregunta clave |
|---|---|
| Jue 10:30 | ¿La recalibración corre? ¿Cambian las cifras del pitch? |
| Jue 12:30 | ¿Simulación nueva lista? ¿El contrato JSON del módulo está congelado? |
| Jue 14:30 (hora 1 del módulo) | ¿Cada uno trabaja contra el contrato sin esperar a otro? |
| Jue 16:00 (hora 2.5) | ¿El valor presente cierra y pasan las pruebas de la regla? |
| Jue 18:00 (hora 4.5) | ¿Flujo asesor → cliente con datos reales de la API? |
| Vie 10:30 (hora 6.5) | ¿Demo completa con E001 y E002? ¿Existe el mínimo demostrable? |
| Vie 12:00 | Congelamiento: lo que no está, no entra |

## Regla para recortar alcance

1. Si en un control vamos **30 minutos o más atrasados**, se aplica el siguiente recorte de la lista del
   módulo (`MODULO_EN_VIVO.md`, sección 8), sin discusión.
2. Si en el control del viernes a las 10:30 **no existe el mínimo demostrable**, se deja de construir y se
   integra y ensaya lo que haya.
3. **Nada nuevo** entra después del control del viernes a las 10:30: solo errores, textos y datos.
4. Un error que aparece después del congelamiento **no se arregla con código**: se esquiva con la
   [contingencia](CONTINGENCIAS.md) que corresponda (modo sin conexión, video o la otra laptop).

## Ramas y etiquetas

- Durante el evento: `final/modulo-motor`, `final/modulo-api`, `final/modulo-cliente`, `final/modulo-asesor`.
  Cada una se fusiona a `main` en los controles, nunca en medio de un bloque.
- `final-dia1` (jueves 18:00) y `final-presentacion` (viernes 12:00): si algo se rompe, se vuelve a la
  etiqueta anterior en un minuto.
- Commits desde la cuenta de GitHub de cada integrante: queda registrado qué se construyó en el evento
  (ver `PROPIEDAD_INTELECTUAL.md`).
