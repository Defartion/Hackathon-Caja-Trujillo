# Disparador ENFEN y notificaciones (fase 2 · lote C)

La cláusula El Niño de CuotaFlex se activa con el **comunicado oficial del ENFEN**, no con un interruptor
manual, y el cliente recibe avisos simulados por SMS o WhatsApp.

Al 23 nov 2026 rige la **Alerta de El Niño Costero**: el ENFEN la activó en el Comunicado Oficial
N° 03-2026 (13 feb 2026) y la mantiene en el N° 20-2026 (13 nov 2026), con magnitud extraordinaria
prevista hasta febrero de 2027.

## Fuentes oficiales (verificadas el 23 nov 2026)

| Fuente | URL | Uso |
|---|---|---|
| gob.pe · SENAMHI, colección "Comunicados oficiales del ENFEN" | <https://www.gob.pe/institucion/senamhi/colecciones/1308-comunicados-enfen> | Principal. Tarjetas con fecha, más reciente primero. Cada ficha enlaza el PDF en `cdn.www.gob.pe` |
| ENFEN (IMARPE), comunicados | <https://enfen.imarpe.gob.pe/comunicados/> | Segunda fuente. Recuadro "Último comunicado" con descarga directa del PDF (`?wpdmdl=…`) |
| SINIA (MINAM) | p. ej. <https://sinia.minam.gob.pe/documentos/comunicado-oficial-enfen-ndeg-14-2026> | Solo referencia manual: no tiene un listado consultable y va atrasado frente a las otras dos |

El lector consulta **las dos primeras y se queda con el comunicado más reciente** que liste cualquiera de
ellas; si la descarga falla, usa la otra. Así no depende de una sola fuente.

## Cómo se lee un comunicado

1. Página de la colección de cada fuente → comunicado más reciente.
2. Descarga del PDF (máximo 20 MB).
3. Texto de la primera página con `pypdf` (`requirements-lote-c-enfen.txt`).
4. Expresiones regulares sobre el texto normalizado (sin tildes, en minúsculas, con un solo espacio), así
   que no importan las tildes, las mayúsculas ni los saltos de línea.

Lo que se aprendió con los 39 PDF de 2022-2026:

- **El formato cambió en septiembre de 2026.** Hasta el N° 16-2026 el PDF dice "Estado del sistema de
  alerta: Alerta de El Niño Costero". Desde el N° 17-2026 solo aparece la línea "Alerta de El Niño
  Costero¹" debajo de la fecha. El parser busca primero la etiqueta y, si no está, la línea suelta.
- La llamada a nota va pegada al estado ("Costero1", "No activo1") y a veces hay mayúsculas
  ("ALERTA DE LA NIÑA COSTERA").
- Existe una serie de **comunicados extraordinarios** (p. ej. el N° 01-2025).
- **Erratas de fecha:** el N° 17-2026 dice "28 septiembre 2027". Si la fecha del PDF es futura y su año no
  coincide con el del número, se usa el año del número y queda una advertencia en la respuesta.
- La magnitud (débil, moderada, fuerte o extraordinaria) se toma de la primera mención en el resumen, que
  corresponde a El Niño costero (región Niño 1+2). "Muy fuerte" se refiere al Pacífico central y se ignora.

## Modos y variables de entorno

| Variable | Valores | Efecto |
|---|---|---|
| `ENFEN_MODO` | `demo` (por defecto) · `oficial` | `oficial` lee el último comunicado real. `demo` no usa internet: el estado lo fija `POST /alertas/enfen/demo` |
| `ENFEN_REVISION_AUTOMATICA` | `1` para activar | Al iniciar la API, un hilo revisa el ENFEN cada 6 h. Apagado por defecto (y en las pruebas) |
| `ENFEN_REVISION_HORAS` | número, por defecto `6` | Intervalo de la revisión automática |
| `NOTIFICACIONES_ARCHIVO` | ruta · vacío | Bitácora del outbox. Por defecto `data/outbox.jsonl`; vacía, solo memoria |
| `NOTIFICACIONES_CANAL` | `sms` (por defecto) · `whatsapp` | Canal de los clientes que no tienen uno registrado |

El modo por defecto es `demo` para que las pruebas y la demo no dependan de internet. No exportes
`ENFEN_MODO=oficial` en la terminal donde corres `pytest`: las pruebas del lote B de la fase 1 esperan el
modo demo.

**Caché y respaldo:** cada lectura oficial se guarda en `data/enfen_cache.json` y vale 6 h. Si la red
falla, se devuelve la última lectura con `desactualizado: true` y no se reintenta durante 10 minutos (así
las solicitudes de la app del cliente no se quedan esperando). Si no hay red ni caché, `GET /alertas/enfen`
responde 503 y el alivio queda deshabilitado. Una fuente atrasada nunca reemplaza un comunicado más nuevo.
Si el día de la final no hay internet, el respaldo manual es el modo demo.

## Endpoints (`/alertas`)

| Método y ruta | Qué hace |
|---|---|
| `GET /alertas/enfen` | Estado vigente: `estado`, `etiqueta`, `activo`, `numero`, `fecha`, `fuente`, `url_fuente`, `desactualizado`, `advertencias` |
| `POST /alertas/enfen/revisar` | Fuerza una lectura. Si el estado cambió, registra el evento y genera las notificaciones |
| `POST /alertas/enfen/demo` | Solo en modo demo. Cuerpo: `{"estado": "ALERTA_NINO", "magnitud": "fuerte"}` |
| `GET /alertas/eventos` | Cambios de estado detectados (origen, estado anterior y nuevo, avisos enviados) |
| `GET /alertas/impacto` | Préstamos activos con cláusula El Niño: número, saldo y cuotas de alivio, por rubro, por región y por rubro × región |
| `GET /alertas/notificaciones?loanId=` | Bandeja de salida, del más reciente al más antiguo |
| `POST /alertas/notificaciones/generar-recordatorios?hoy=&canal=` | Recordatorio 3 días antes del vencimiento y aviso de temporada baja. `hoy` simula otra fecha |
| `POST /alertas/notificaciones/enviar` | Simula el envío: `pendiente` → `enviado-simulado` |
| `POST /alertas/demo/cartera?n=20` | Registra en el core créditos sintéticos activos con región y canal, para mostrar el impacto |

`activo` solo es verdadero con **ALERTA_NINO**. **VIGILANCIA_NINO** genera un aviso preventivo, sin alivio.

### App del cliente (fase 1)

`GET /cliente/el-nino` (`estado_el_nino()`) conserva el formato `{"activo", "desde", "fuente"}`; `fuente`
es `demo` o `enfen`. Solo con Vigilancia se agrega `aviso`. En modo demo, el interruptor de la app
(`POST /cliente/el-nino`) sigue funcionando: activo fija ALERTA_NINO e inactivo NO_ACTIVO, y genera los
mismos avisos.

## Notificaciones

Todo es simulado: no se envía ningún SMS ni WhatsApp real. Cada mensaje guarda canal, destinatario
(`loanId`), plantilla, texto, fecha y estado.

| Plantilla | Cuándo |
|---|---|
| `recordatorio_cuota` | 3 días antes del vencimiento, con monto y fecha |
| `temporada_baja` | La próxima cuota es de temporada baja (mensaje positivo) |
| `alerta_el_nino` | El estado cambia a Alerta de El Niño Costero: "puedes usar tu alivio", con instrucciones |
| `vigilancia_el_nino` | El estado cambia a Vigilancia: aviso preventivo, sin alivio |
| `aplazamiento_confirmado` | El cliente confirma un aplazamiento: nuevo monto y costo adicional |

Los avisos de El Niño solo van a préstamos activos con la cláusula (rubros expuestos) y con alivio por usar.
Ningún SMS pasa de 160 caracteres **GSM-7**: en ese canal se quitan las tildes de á, í, ó y ú, porque con
ellas el teléfono usa UCS-2 y solo caben 70 caracteres. WhatsApp conserva las tildes.

Ejemplo (SMS): `Rosa: el ENFEN declaro Alerta de El Niño Costero. Puedes usar tu alivio y pagar solo la cuota
minima. En la app toca 'Usar alivio'. Caja Trujillo`

## Guion para la demo

```bash
ENFEN_MODO=demo PYTHONPATH=src uvicorn cuotaflex.api.main:app --reload
# PowerShell: $env:ENFEN_MODO="demo"; $env:PYTHONPATH="src"; uvicorn cuotaflex.api.main:app --reload
curl -X POST "localhost:8000/alertas/demo/cartera?n=20"                       # cartera con región
curl -X POST localhost:8000/alertas/enfen/demo -H "Content-Type: application/json" \
     -d '{"estado": "ALERTA_NINO", "magnitud": "extraordinaria"}'               # el cambio en vivo
curl localhost:8000/alertas/notificaciones                                      # avisos generados
```

En el tablero (5175), el distintivo de la cabecera pasa a rojo; al hacer clic muestra el impacto. En la app
del cliente (5174), un préstamo con cláusula muestra el banner "Alerta El Niño activa".

Con `ENFEN_MODO=oficial`, el distintivo muestra el comunicado real ("Comunicado N° 20-2026, 13 nov 2026") con
el enlace al PDF.

### Evidencias (23 nov 2026)

Capturas en [`docs/fases/fase-2/evidencias/lote-c/`](../../../docs/fases/fase-2/evidencias/lote-c/):

| Captura | Qué muestra |
|---|---|
| `01-tablero-enfen-oficial.png` | Modo oficial: distintivo con el Comunicado N° 20-2026 real y la corrida Base del tablero |
| `02-tablero-impacto-cartera.png` | Panel de impacto: 11 de 20 préstamos con cláusula, S/ 77,900 cubiertos, por rubro y región |
| `03-cabecera-vigilancia-demo.png` | Modo demo en Vigilancia de El Niño Costero (ámbar, sin alivio) |
| `04-cabecera-alerta-demo.png` | Modo demo en Alerta de El Niño Costero |
| `05-cliente-banner-alerta.png` | App del cliente con el banner "Alerta El Niño activa" tras el cambio en vivo |

## Límites conocidos

- El cronograma del core solo guarda el mes de cada cuota; para el recordatorio se asume que vence el día 28.
- El core no guarda la región de los clientes que crea la app del asesor; aparecen como "Sin región". La
  cartera de demo sí la trae.
- El aviso de aplazamiento se genera con un middleware que observa `POST /cliente/prestamos/{id}/aplazamiento`,
  para no tocar ese router. Al integrar se puede reemplazar por una llamada directa desde el router del cliente.
- El outbox vive en memoria; `data/outbox.jsonl` es una bitácora y no se vuelve a cargar al reiniciar,
  porque los préstamos del core de demo también empiezan de cero.
