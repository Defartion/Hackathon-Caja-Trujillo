# CuotaFlex · Fase 1 · Lote B — para Joaquin

Hola Joaquin. Este documento tiene todo lo que necesitas para tu parte. Trabajas solo en tu rama
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
git checkout -b fase-1/lote-b-cliente
```
3. Lee `README.md` y `NOTAS.md` (5 minutos). Para entender el motor, mira `src/cuotaflex/agente.py`.
4. Al terminar: haz `push` de tu rama y abre un Pull Request a `main` con capturas y la lista de criterios marcada.

---

## Fase 1 · Lote B — App web del cliente (móvil)

**Rama:** `fase-1/lote-b-cliente`

## Objetivo
Mostrar en la demo la experiencia del microempresario desde el celular: su próxima cuota, el
cronograma con temporadas altas y bajas, cómo pedir un aplazamiento viendo el efecto antes de
confirmarlo, y el aviso de alivio cuando el ENFEN declara alerta de El Niño costero.

## Archivos de este lote (exclusivos)
- `src/cuotaflex/api/routers/cliente.py` (nuevo)
- `web/cliente/**` (nuevo)
- `tests/test_lote_b_cliente.py` (nuevo)

No modifiques `src/cuotaflex/*.py` ni `api/main.py`.

## 1. Backend: `routers/cliente.py`

```python
from fastapi import APIRouter
from .. import main as api          # DB, BASE, crear_cliente, crear_prestamo, comando_prestamo, aplazar
router = APIRouter(prefix="/cliente", tags=["cliente"])
```
`api.DB["loans"][id]` es el dict del préstamo. Como los routers se registran al final de `main.py`,
la importación `from .. import main` funciona. Guarda tus campos propios con `setdefault`, por
ejemplo `l.setdefault("cuotasPagadas", 0)`.

### `POST /cliente/demo-seed`
Crea un cliente de demo para que la app funcione sola:
- Rubro `agricultura`, ventas medias 7000, margen 0.35, gasto familiar 1000 y 0 días de atraso.
- Préstamo de S/ 6,000 a 12 meses, con la primera cuota en el mes actual (`date.today().month - 1`).
- Lo aprueba y lo desembolsa, y devuelve `{"loanId": ..., "clientId": ...}`.
- Si se manda `?producto=aplazamiento`, usa rubro `bodega`, que da el producto de aplazamiento.

### `GET /cliente/prestamos/{loanId}`
```json
{
  "loanId": 3, "producto": "estacional", "descripcion": "...", "estado": "Active",
  "tea": 0.47, "principal": 6000,
  "proximaCuota": {"numero": 2, "mes": "feb", "monto": 310.5, "temporada": "baja"},
  "cuotasPagadas": 1, "totalCuotas": 12,
  "aplazamientosRestantes": 0, "clausulaElNino": true,
  "elNino": {"activo": false, "alivioDisponible": 3},
  "cronograma": [{"numero": 1, "mes": "ene", "cuota": 404.1, "estado": "pagada", "temporada": "alta"}, ...],
  "explicacion": "texto del agente"
}
```
- Los meses y la explicación salen de `l["propuesta"]`. Las cuotas vigentes salen de `l["cuotas"]`, que pueden haber cambiado por aplazamientos.
- `temporada`: "alta" si la cuota está por encima de la cuota fija de referencia × 1.05, "baja" si está por debajo × 0.95, y "normal" en otro caso.
- `estado` de cada cuota: "pagada" (numero ≤ cuotasPagadas), "proxima" o "pendiente".

### `POST /cliente/prestamos/{loanId}/pagar`
Registra el pago de la próxima cuota con `api.pagar(...)` (command `repayment`, monto igual a la cuota vigente) y suma 1 a `cuotasPagadas`.

### `POST /cliente/prestamos/{loanId}/aplazamiento/preview` con cuerpo `{"installment": n}`
- **No modifica nada.** Calcula lo mismo que `api.aplazar` sobre una copia de las cuotas: `piso`, el monto diferido y `extra = cuota_francesa(diferido, tem, n - k - 1)`.
- Devuelve `{cuotaActual, nuevaCuota, incrementoCuotasSiguientes, costoAdicionalTotal, cronogramaNuevo}`.
- `costoAdicionalTotal` es la suma de las cuotas nuevas menos la suma de las anteriores: es el interés extra, y hay que mostrarlo por transparencia.
- Devuelve 409 si no quedan aplazamientos, y 400 si es la última cuota o una cuota ya pagada.

### `POST /cliente/prestamos/{loanId}/aplazamiento`
Confirma llamando a `api.aplazar(loanId, "deferInstallment", AplazamientoIn(installment=n))`.

### `GET /cliente/el-nino` y `POST /cliente/el-nino`
- Hay un estado global de demo: `{"activo": bool, "desde": fecha, "fuente": "demo"}`. El POST recibe `{"activo": true/false}`.
- En la fase 2 (lote C) se reemplaza por el boletín real del ENFEN. Deja la lectura del estado en una sola función `estado_el_nino()`.

### `POST /cliente/prestamos/{loanId}/alivio-el-nino`
- Solo se puede si la alerta está activa, el préstamo tiene `clausula_el_nino` y quedan meses de alivio. Los meses salen de `l.setdefault("alivioRestante", par["el_nino"]["meses_alivio"])`.
- Lleva la próxima cuota al piso y redistribuye el resto con la misma fórmula del aplazamiento, pero sin gastar los aplazamientos normales.
- Resta 1 a `alivioRestante`.

### Pruebas (`tests/test_lote_b_cliente.py`)
- `demo-seed` → `GET` devuelve 12 cuotas y la próxima es la número 1.
- `preview` no cambia `l["cuotas"]`, y el valor presente del cronograma nuevo sigue igual al monto con tolerancia de 1.
- Confirmar el aplazamiento resta 1 a `aplazamientosRestantes`; con 0 restantes devuelve 409.
- El alivio de El Niño devuelve 409 sin alerta y funciona con la alerta activa.
- Pagar avanza la próxima cuota.

## 2. Frontend: `web/cliente`

**Stack:** Vite + React + TypeScript, en el puerto **5174**, diseñado para móvil a 375 px (centrado
en pantallas grandes). La URL de la API va en `VITE_API_URL`. Usa los tokens de color de `docs/fases/ROADMAP.md`.

**Lenguaje:** español sencillo, con frases cortas y tuteo. Nada de jerga como "VPN", "TEA" o "MILP"
sin explicarla. Letra base de 16 px o más y botones de al menos 44 px de alto.

### Pantallas
1. **Inicio**
   - Saludo y una tarjeta grande con la próxima cuota: monto, mes y una etiqueta de temporada (verde para alta, ámbar para baja).
   - Barra de avance con las cuotas pagadas sobre el total.
   - Botones: "Ver mi cronograma", "Necesito aplazar una cuota" (solo si quedan aplazamientos) y "Pagar cuota (demo)".
   - Banner rojo cuando hay alerta de El Niño y el préstamo tiene la cláusula: "Alerta El Niño activa: puedes pagar solo la cuota mínima este mes" con el botón "Usar alivio".
2. **Cronograma**
   - Lista vertical de cuotas: mes, monto y estado (✓ pagada, ● próxima, ○ pendiente), con un color por temporada.
   - Arriba, una línea que explica: "Tus cuotas son más altas en tus meses de más ventas y más bajas en los de menos ventas".
3. **Aplazar cuota** (3 pasos)
   1. Elegir la cuota (solo las pendientes).
   2. Llamar a `preview` y mostrar: "Este mes pagas S/ X en lugar de S/ Y. Las siguientes cuotas suben S/ Z. Costo adicional total: S/ W". También cuántos aplazamientos te quedarían.
   3. Confirmar → pantalla de éxito con el cronograma actualizado.
4. **Ayuda**: el texto `explicacion` del agente y tres preguntas frecuentes: ¿qué es el aplazamiento?, ¿cuánto me cuesta?, ¿qué pasa si hay El Niño?
5. **Panel de demo** (oculto, se abre con `?demo=1`)
   - Botón "Crear cliente de demo" (`demo-seed`, con o sin `producto=aplazamiento`).
   - Interruptor "Alerta El Niño" (`POST /cliente/el-nino`).
   - El `loanId` actual se guarda en `localStorage`, dentro de try/catch.

### Requisitos de calidad
- Si no hay préstamo cargado, la app muestra el panel de demo y no un error.
- Todas las acciones muestran un estado de carga y un mensaje de error legible.
- Montos en formato `S/ 1,234.56`.
- `npm run build` sin errores.

## Cómo correr
```bash
PYTHONPATH=src uvicorn cuotaflex.api.main:app --reload
cd web/cliente && npm install && npm run dev     # http://localhost:5174/?demo=1
```

## Criterios de aceptación
- [ ] Con `?demo=1` se crea un cliente y se ve su inicio y su cronograma.
- [ ] El aplazamiento muestra la vista previa con el costo adicional y, al confirmar, el cronograma cambia.
- [ ] Al activar El Niño aparece el banner y el alivio funciona.
- [ ] Se ve bien a 375×812.
- [ ] `pytest` pasa, incluidas las pruebas nuevas.
- [ ] Capturas de las 3 pantallas principales en `web/cliente/README.md`.

## Fuera de alcance
Login, notificaciones push o SMS (fase 2, lote C) y pagos reales con Yape.

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
