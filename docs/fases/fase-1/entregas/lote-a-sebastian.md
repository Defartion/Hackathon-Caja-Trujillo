# CuotaFlex · Fase 1 · Lote A — para Sebastian

Hola Sebastian. Este documento tiene todo lo que necesitas para tu parte. Trabajas solo en tu rama
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
git checkout -b fase-1/lote-a-asesor
```
3. Lee `README.md` y `NOTAS.md` (5 minutos). Para entender el motor, mira `src/cuotaflex/agente.py`.
4. Al terminar: haz `push` de tu rama y abre un Pull Request a `main` con capturas y la lista de criterios marcada.

---

## Fase 1 · Lote A — App web del asesor

**Rama:** `fase-1/lote-a-asesor`

## Objetivo
Construir la herramienta que usaría el asesor de negocios en la demo. Debe permitir elegir una
solicitud, ver el pronóstico del negocio, recibir la propuesta del agente (producto, cronograma y
explicación), compararla con la cuota fija y registrarla en el core.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/api/routers/asesor.py` (nuevo)
- `web/asesor/**` (nuevo)
- `tests/test_lote_a_asesor.py` (nuevo)
- `requirements-lote-a.txt`, solo si necesitas otra librería de Python

No modifiques `src/cuotaflex/*.py` ni `api/main.py`.

## 1. Backend: `routers/asesor.py`

```python
from fastapi import APIRouter
router = APIRouter(prefix="/motor", tags=["asesor"])
```

### `GET /motor/cartera-demo?n=20&semilla=7`
- Usa `datos.generar_cartera(n, semilla)` y cachea el resultado por `(n, semilla)` en un dict del módulo.
- Responde con una lista de clientes con todos los campos del DataFrame, más:
  - `historial_ventas`: la lista de 24 ventas mensuales del cliente, ordenadas por `t`.
  - `indice_estacionalidad`: `datos.indice_estacionalidad(rubro)`.
- Límite: `n ≤ 100`.

### `POST /motor/propuesta`
Cuerpo: un cliente con los mismos campos que devuelve `cartera-demo`. `historial_ventas` es
opcional; si no viene, se simula con `datos.simular_ventas` igual que en `api/main.py::crear_prestamo`.

Pasos:
1. Arma `historial` (DataFrame `cliente_id, t, ventas`) y llama a `AgenteAsesor(metodo_pronostico="mixto").proponer(cliente, historial)`.
2. Calcula el pronóstico de ventas para el gráfico: `pronostico.pronosticar(DataFrame([{**cliente, "plazo": propuesta["plazo"]}]), historial)` devuelve un array de forma (4, plazo) con p10, p25, p50 y p90.
3. **Comparación de riesgo para este cliente.** Simula 300 escenarios con `simulacion.simular_credito` para las dos estrategias, usando las mismas trayectorias:
   - `rng = np.random.default_rng(semilla_fija)`
   - `ventas = datos.simular_ventas(rubro, ventas_medias, 24, rng, mes_desembolso, 300)[:, :plazo]`
   - `nino = simulacion._trayectorias_el_nino(300, 24, rng, par)[:, :plazo]`
   - **Fija:** cuota francesa con el monto, plazo y TEA solicitados, sin aplazamientos ni alivio.
   - **CuotaFlex:** las cuotas, la TEA, el plazo y el monto de la propuesta, con `aplazamientos_disponibles` y `clausula_el_nino`.
   - Vuelve a crear `rng` con la misma semilla antes de simular la segunda estrategia.
4. Responde:
```json
{
  "propuesta": { ...salida completa de proponer... },
  "pronostico": {"p10": [...], "p25": [...], "p50": [...], "p90": [...]},
  "capacidad": [...],
  "comparativa": {
    "fija":      {"mora30": 0.18, "default": 0.07, "vpn_medio": 512.3, "cuotas": [...]},
    "cuotaflex": {"mora30": 0.06, "default": 0.02, "vpn_medio": 640.1, "cuotas": [...]}
  }
}
```
`capacidad[t] = max(excedente_p25[t], 0) * ratio_cuota_excedente_max`. `excedente_p25` sale de la propuesta.

Convierte todos los `np.float64` a `float` antes de responder.

### Pruebas (`tests/test_lote_a_asesor.py`)
- `cartera-demo` devuelve `n` clientes, cada uno con 24 ventas en el historial.
- `propuesta` devuelve un cronograma de largo `plazo`, cuatro series de pronóstico, y en la comparativa valores `mora30` y `default` entre 0 y 1.
- `propuesta` sin `historial_ventas` también funciona.
- La misma entrada da el mismo resultado dos veces (semillas fijas).

## 2. Frontend: `web/asesor`

**Stack:** Vite + React + TypeScript + Recharts, en el puerto **5173**. La URL de la API va en
`VITE_API_URL` (por defecto `http://127.0.0.1:8000`). Copia los tokens de color de `docs/fases/ROADMAP.md`.

### Pantallas

**1. Bandeja de solicitudes** (`/`)
- Una tabla con los clientes de `cartera-demo` (n=30): código, rubro, región, monto solicitado, plazo,
  días de atraso máximos y un indicador de estacionalidad (barra o etiqueta baja/media/alta).
- Filtro por rubro y búsqueda por código. Al hacer clic en una fila se abre la ficha.

**2. Ficha y propuesta** (`/cliente/:id`). Al entrar llama a `POST /motor/propuesta`.
- **Encabezado:** rubro, región, ventas medias, margen y otras deudas.
- **Gráfico 1 · Ventas:** las 24 ventas históricas como línea y el pronóstico p50 como línea punteada, con banda p10–p90 sombreada. Eje X en meses (ene…dic).
- **Gráfico 2 · Cuota vs. capacidad:** barras con la cuota fija y la cuota CuotaFlex por mes, y una línea con la `capacidad`. Los meses donde la cuota supera la capacidad van en ámbar.
- **Tarjeta del producto:** el nombre (`descripcion_producto`), un distintivo (fija, aplazamiento o estacional), monto aprobado contra el solicitado (si bajó, mostrar el motivo), la TEA, si tiene cláusula El Niño y cuántos aplazamientos quedan.
- **Explicación del agente:** el texto de `explicacion`.
- **Comparativa de riesgo:** tres indicadores (atraso > 30 días, default y VPN medio) para fija y CuotaFlex, con la diferencia en verde o rojo.
- **Bitácora del agente:** una línea de tiempo con los pasos de `bitacora` (elegibilidad → producto → cronograma, más las replanificaciones → validación), que muestre los `motivos` y los `chequeos` con ✓ o ✗.
- **Tabla del cronograma:** número, mes, cuota, interés, capital y saldo. Se puede plegar.

**3. Simulación de cambios** (dentro de la ficha)
- Campos editables: monto, plazo (12, 18 o 24) y el ajuste del asesor (de 0.9 a 1.1, con deslizador).
- Botón "Recalcular": vuelve a llamar a `propuesta` y actualiza todo. Debe mostrar un estado de carga.

**4. Registrar en el core**
- Botón "Registrar solicitud":
  1. `POST /fineract-provider/api/v1/clients`, con nombre "Cliente {id}" y los campos del cliente.
  2. `POST /fineract-provider/api/v1/loans`, que devuelve `loanId`.
- Muestra el `loanId` y los botones "Aprobar" y "Desembolsar" (`POST /loans/{id}?command=approve|disburse`), con el estado actual.
- Enlace "Ver cronograma en core" que abre `GET /loans/{id}?associations=repaymentSchedule` en un modal.

### Requisitos de calidad
- Si la API no responde, se muestra un mensaje claro, nunca la pantalla en blanco.
- Funciona bien en 1366×768 (laptop de la demo).
- Montos en formato `S/ 1,234.56` y porcentajes con un decimal.
- `npm run build` sin errores de TypeScript.

## Cómo correr
```bash
PYTHONPATH=src uvicorn cuotaflex.api.main:app --reload
cd web/asesor && npm install && npm run dev
```

## Criterios de aceptación
- [ ] La bandeja carga 30 clientes y deja filtrar.
- [ ] La ficha muestra los dos gráficos, la propuesta, la explicación, la comparativa y la bitácora.
- [ ] Al cambiar monto o plazo y recalcular, cambian el cronograma y la comparativa.
- [ ] El flujo registrar → aprobar → desembolsar funciona de punta a punta.
- [ ] `pytest` pasa, incluidas las pruebas nuevas.
- [ ] Una captura de la ficha en `web/asesor/README.md`.

## Fuera de alcance
App del cliente (lote B), tablero de cartera (lote C), login y base de datos (fase 3).

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
