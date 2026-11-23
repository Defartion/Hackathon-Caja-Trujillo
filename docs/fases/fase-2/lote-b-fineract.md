# Fase 2 · Lote B — Integración con Apache Fineract real

**Rama:** `fase-2/lote-b-fineract`

## Objetivo
Demostrar integración tecnológica real, que pesa en viabilidad técnica (25%) y en funcionamiento (35%).
Un préstamo creado en CuotaFlex debe aparecer en un **Apache Fineract real** con su cronograma de
cuotas variables, aprobado y desembolsado. La API simulada de la fase 0 queda como plan B.

## Archivos de este lote (exclusivos)
- `infra/fineract/**` (nuevo): `docker-compose.yml`, scripts y README
- `src/cuotaflex/integraciones/__init__.py` y `src/cuotaflex/integraciones/fineract.py` (nuevos)
- `src/cuotaflex/api/routers/core_fineract.py` (nuevo)
- `scripts/seed_fineract.py` (nuevo)
- `tests/test_fase2_b.py` (nuevo)
- `requirements-fase2-b.txt`, si necesitas librerías

No modifiques `api/main.py`, los otros routers ni el motor. La integración funciona como un
**espejo**: toma un préstamo del core simulado y lo replica en Fineract.

## Tareas

### 1. Levantar Fineract con Docker (`infra/fineract/`)
- `docker-compose.yml` con la imagen oficial `apache/fineract` en una **versión fija** (nada de `latest`), su base de datos (MariaDB o PostgreSQL, según la documentación de esa versión) y healthchecks.
- Toma la configuración de variables de entorno de la documentación oficial de la versión elegida (`fineract.apache.org/docs`). Anota la versión y el enlace en el README.
- Script `up.sh` (y `up.ps1` para Windows) que levanta todo, espera a que la API responda y muestra la URL.
- Credenciales de demo solo en `.env.example`. Nunca subas un `.env` real.
- **Mide cuánto tarda en arrancar y cuánta memoria usa**, y anótalo: decide si corre en una laptop el día de la final.

### 2. Datos base (`scripts/seed_fineract.py`)
Idempotente (se puede correr varias veces sin duplicar):
- La oficina por defecto, un usuario o asesor de demo y la moneda PEN.
- **Producto de crédito "CuotaFlex Microempresa"** con *variable installments* habilitado y el mínimo y máximo de días entre cuotas. Usa el tipo de interés y la amortización que mejor se acerquen a nuestra cuota francesa (saldo decreciente).
- Guarda los IDs creados en `infra/fineract/ids.json`.

### 3. Cliente HTTP (`integraciones/fineract.py`)
Clase `FineractClient(base_url, tenant, usuario, clave, verify_ssl)`, con encabezado
`Fineract-Platform-TenantId` y autenticación básica. Métodos:
- `crear_cliente(datos) -> int`
- `crear_prestamo(client_id, product_id, principal, plazo, tea, fecha_desembolso) -> int`
- `calcular_cronograma(loan_id)`, `agregar_variaciones(loan_id, cuotas)` y `eliminar_variaciones(loan_id)`
- `aprobar(loan_id, fecha)`, `desembolsar(loan_id, fecha)`, `pagar(loan_id, monto, fecha)` y `obtener_prestamo(loan_id)` (con el cronograma)

Detalles importantes:
- **Revisa en el Swagger de tu versión** (`/fineract-provider/swagger-ui/index.html`) el cuerpo exacto de `POST /loans/{loanId}/schedule?command=addVariations`. Documenta un ejemplo real que funcione en el README; no confíes en ejemplos de internet.
- Fineract recalcula la última cuota: no la fuerces.
- Fechas con `dateFormat` y `locale`, como pide Fineract.
- Errores de Fineract convertidos en excepciones legibles, con el mensaje de `errors[].defaultUserMessage`.
- Tiempo máximo de espera de 15 s y un reintento en errores de red.

### 4. Router espejo (`routers/core_fineract.py`, prefijo `/core`)
- `GET /core/estado`: responde `{"fineract": "conectado"|"no disponible", "version": ..., "url": ...}` sin fallar si Fineract está apagado.
- `POST /core/espejo/{loanId}`: toma el préstamo del core simulado (`api.main.DB["loans"][loanId]`) y lo replica en Fineract. Crea el cliente, crea el préstamo, aplica las variaciones con `l["cuotas"]`, aprueba y desembolsa si en el simulado está `Active`. Devuelve los IDs de Fineract y compara las cuotas de los dos sistemas (diferencia máxima).
- `GET /core/espejo/{loanId}`: el cronograma según Fineract, al lado del simulado.
- La configuración se toma de variables de entorno: `FINERACT_URL`, `FINERACT_TENANT`, `FINERACT_USER`, `FINERACT_PASSWORD` y `FINERACT_VERIFY_SSL`.

### 5. Pruebas (`tests/test_fase2_b.py`)
- Pruebas unitarias del cliente con respuestas simuladas (`httpx.MockTransport` o `respx`): cuerpos enviados, fechas y manejo de errores. **Deben pasar sin Fineract corriendo.**
- Una prueba de integración marcada `@pytest.mark.fineract`, que se salta si `FINERACT_URL` no está definido. Corre el flujo completo contra el Docker real.
- `GET /core/estado` responde "no disponible" sin romperse cuando Fineract está apagado.

### 6. Evidencia
- Un GIF o video corto: préstamo creado en la app del asesor → espejo → el mismo cronograma visible en Fineract (por la API o en la interfaz web de Mifos si la levantas).
- Una tabla en el README que compare cuota por cuota entre el simulado y Fineract, con diferencias de redondeo en céntimos.

## Criterios de aceptación
- [ ] `up.sh` levanta Fineract desde cero y `seed_fineract.py` crea el producto con cuotas variables.
- [ ] El espejo de un préstamo estacional deja en Fineract las mismas cuotas, con una diferencia de S/ 0.05 o menos, salvo la última.
- [ ] Con Fineract apagado, la API de CuotaFlex sigue funcionando y `/core/estado` lo informa.
- [ ] `pytest` pasa sin Fineract (la prueba de integración se salta).
- [ ] El README tiene la versión, los requisitos de memoria, un ejemplo real de `addVariations` y el GIF.

## Fuera de alcance
Cambiar la API simulada por Fineract en todas las apps (con `CORE=fineract`): eso va en la fase 3, lote A.
