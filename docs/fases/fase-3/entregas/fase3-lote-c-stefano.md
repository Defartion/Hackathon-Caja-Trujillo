# CuotaFlex · Fase 3 · Lote C — para Stefano

Hola Stefano. Aquí está tu parte de la **fase 3, la preparación de la final**. Trabajas en tu rama y en tus archivos.

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
git checkout -b fase-3/lote-c-final
```
Al terminar: haz `git push -u origin fase-3/lote-c-final` y **abre el Pull Request** a `main` con evidencias y la lista de criterios marcada.

---

## Fase 3 · Lote C — Plan de los dos días de la final, módulo en vivo y video de respaldo

**Rama:** `fase-3/lote-c-final`

## Objetivo
La final (3 y 4 de diciembre, Hub UPAO) son **dos días de construcción, demostración y pitch**.
Las bases piden que el motor y el módulo se desarrollen **durante el evento**, y lo que se construya
pasa a la Caja si ganamos. Este lote prepara todo para que esos dos días rindan al máximo:
- un plan por horas;
- el diseño del módulo que construiremos **en vivo**;
- la verificación de las laptops;
- un video de respaldo por si falla algo.

## Archivos de este lote (exclusivos)
- `docs/final/**` (nuevo)
- `scripts/verificar_entorno.sh` y `.ps1` (nuevos)
- `tests/test_fase3_c.py` (nuevo, solo para el script de verificación)

No escribas el código del módulo en vivo: se construye en el evento. Aquí va **solo su diseño**.

## Tareas

### 1. Diseño del módulo en vivo: "Pago a cosecha / porcentaje de ventas" (`docs/final/MODULO_EN_VIVO.md`)
Es la extensión natural de CuotaFlex, inspirada en Shopify Capital: el cliente paga un **porcentaje de
sus ventas registradas** (por ejemplo, los cobros con Yape) con un piso mínimo mensual y un plazo
máximo. Una variante es el **pago a cosecha**: cuotas mínimas durante la campaña y un pago grande al
cosechar. Documenta:
- **Reglas de negocio:** % de ventas, piso, techo, plazo máximo, qué pasa si las ventas caen (alivio) y cómo se cierra el valor presente.
- **Encaje en el motor:** una cuarta modalidad candidata en la selección por simulación (`seleccion.py`) y cómo simular el cobro (`simular_credito` recibe una regla de pago en lugar de un cronograma fijo).
- **Datos:** cómo se obtendrían las ventas reales (exportes de Yape o POS y, en el futuro, Open Finance) y qué se simula en la demo.
- **API y pantallas:** endpoints nuevos, un componente en la app del asesor y uno en la del cliente (bocetos en Markdown o imágenes).
- **Pruebas que se escribirán.**
- **Plan de implementación por horas,** con 2 personas en el motor y la API y 2 en los frontends. Debe caber en unas **8 horas efectivas**.
- **Riesgos** y qué se recorta si no alcanza el tiempo.

### 2. Plan por horas de los dos días (`docs/final/PLAN_DOS_DIAS.md`)
Base para ajustar con el cronograma oficial cuando la organización lo publique:

| Bloque | Qué se hace | Responsable |
|---|---|---|
| Día 1, mañana | Recibir datos o parámetros de la Caja, recalibrar y volver a correr la simulación | Sebastian |
| Día 1, tarde | Construir el módulo en vivo (motor y API, más frontends) | Todos |
| Día 2, mañana | Integrar, pruebas de punta a punta y casos estrella | Joaquin |
| Día 2, tarde | Congelar el código 3 h antes, ensayar dos veces y presentar | Andre |

- Agrega puntos de control cada 2 h ("¿vamos a tiempo?") y una regla clara para recortar alcance.
- **Regla de oro:** desde 3 horas antes de presentar no se cambia código, solo datos y textos.

### 3. Lista de verificación y contingencias (`docs/final/CHECKLIST.md` y `CONTINGENCIAS.md`)
- **Equipo:** 2 laptops con el repo clonado y probado, cargadores, adaptador HDMI o USB-C, punto de acceso móvil con datos, extensión eléctrica y un USB con el video y el PDF.
- **Cuentas:** GitHub con sesión iniciada, plataforma de despliegue y correo del equipo.
- **Contingencias**, cada una con un responsable y un tiempo de reacción:
  - sin internet → modo sin conexión;
  - Fineract no arranca → core simulado;
  - falla el proveedor de IA → plantillas;
  - falla el proyector → laptop más video;
  - falla la laptop principal → la segunda.

### 4. Verificación del entorno (`scripts/verificar_entorno.sh` y `.ps1`)
Un comando que dice en verde o rojo si la laptop está lista:
- versiones de Python y Node;
- dependencias instaladas;
- `pytest` rápido;
- compilación de las tres apps;
- puertos 8000 y 5173–5175 libres;
- Docker disponible (opcional);
- espacio en disco.

Además, `tests/test_fase3_c.py` prueba las funciones de verificación sin depender de la máquina (usa mocks).

### 5. Video de respaldo (`docs/final/VIDEO.md` y el archivo de video)
- **Guion de 3 minutos** con los tres casos estrella (en coordinación con Joaquin, lote B): asesor → chat → cliente → alerta ENFEN → tablero.
- Grábalo sobre `main` actual (fase 2) **ahora**. Se vuelve a grabar tras la integración de la fase 3 si cambia la interfaz.
- Resolución 1080p, sin datos personales y con subtítulos breves.
- El video **no se sube al repo** (pesa mucho): súbelo al Drive del equipo y deja el enlace en `VIDEO.md`.

### 6. Declaración de propiedad intelectual (`docs/final/PROPIEDAD_INTELECTUAL.md`)
- Tabla de **qué existía antes del evento** (fases 0 a 3, con fechas y commits) y **qué se construirá durante el evento** (el módulo en vivo).
- Todas las librerías de código abierto con su licencia (revisa `requirements.txt` y los `package.json`).
- Coordina el texto con Andre (lote D), que lo usará en el pitch.

## Criterios de aceptación
- [ ] Diseño del módulo en vivo completo, con un plan que cabe en 8 horas.
- [ ] Plan de los dos días, lista de verificación y contingencias con responsables.
- [ ] El script de verificación funciona en Windows y en Linux o Mac.
- [ ] Video de respaldo grabado y enlazado.
- [ ] Declaración de propiedad intelectual revisada por el equipo.

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
