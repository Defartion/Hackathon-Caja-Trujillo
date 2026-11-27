# Video de respaldo

Se usa si falla la demo en vivo, el proyector o la laptop (ver [CONTINGENCIAS.md](CONTINGENCIAS.md)). Muestra el
recorrido completo **asesor → agente (chat) → core → cliente → alerta del ENFEN → tablero** en menos de 3 minutos.

| | |
|---|---|
| **Enlace (Drive del equipo)** | _Pendiente: subir el MP4 y el `.srt` y pegar aquí el enlace_ |
| Archivo | `cuotaflex-respaldo-fase2-2026-11-24.mp4` (8.2 MB) y `cuotaflex-respaldo-fase2-2026-11-24.srt` |
| Grabado | 24 nov 2026, sobre `main` de la fase 2 (`cf6d9de`) |
| Formato | 1920×1080, 30 fps, H.264, **2:45**, sin audio, subtítulos incrustados y también en `.srt` |
| Datos | 100% sintéticos; ningún dato personal. El ENFEN es real: Comunicado Oficial N° 20-2026 (13 nov 2026) |

El video **no va en el repositorio** (pesa mucho): se sube al Drive del equipo y se copia al USB de respaldo.
En [`evidencias/`](evidencias/) quedan cuatro fotogramas de muestra: riesgo simulado del asesor, chat del agente,
alerta del ENFEN en la app del cliente y cartera completa en el tablero.

## Guion (lo que se ve y lo que dicen los subtítulos)

| Tiempo | Pantalla | Qué pasa | Subtítulo (resumen) |
|---|---|---|---|
| 0:00 | Portada | Thinku · Cuotas que se adaptan al flujo del negocio | Recorrido de respaldo de la demo |
| 0:05 | **1 · Asesor**, bandeja | Solicitudes sintéticas de La Libertad | La bandeja del asesor |
| 0:11 | Ficha de C00006 | Negocio agrícola en Chepén: pide S/ 4,900 a 18 meses | Pronóstico de ventas con banda p10–p90 |
| 0:21 | Propuesta | S/ 3,600 a 24 meses | La cuota cabe en la capacidad de pago del escenario conservador |
| 0:28 | Bitácora | Selección por simulación entre fija, aplazamientos y estacional | Elige la cuota fija con aplazamientos |
| 0:36 | Riesgo simulado | Default **7.7% → 2.0%** | En los mismos escenarios |
| 0:46 | **2 · Agente** | Pregunta frecuente «¿Por qué bajó el monto?» | Lo explica con la bitácora y marca «Cifras verificadas» |
| 1:03 | Chat | Pregunta libre «¿Y a 18 meses?» | El motor mantiene 24 meses: a 18 la cuota no cabría |
| 1:11 | **3 · Core**, ficha de C00003 | Pescador artesanal en Ascope: cuotas estacionales | Suben en temporada alta y bajan en temporada baja |
| 1:23 | Registro en el core | Registrar, aprobar y desembolsar | Core compatible con Fineract |
| 1:34 | **4 · App del cliente** | Próxima cuota y banner «Alerta El Niño activa» | El ENFEN mantiene la alerta; su crédito tiene la cláusula |
| 1:46 | App del cliente | «Usar alivio» → cuota mínima | La diferencia se reparte, con interés |
| 1:55 | Cronograma | Temporadas y cuotas pagadas | — |
| 2:00 | **5 · Tablero**, distintivo del ENFEN | Alerta de El Niño Costero · Comunicado N° 20-2026 | Se lee del comunicado oficial en PDF |
| 2:07 | Impacto en la cartera | Créditos con cláusula, saldo cubierto y cuotas de alivio | Por rubro y región |
| 2:19 | **6 · Toda la cartera** | Escenario Base, 600 créditos × 200 escenarios | Default **4.8% → 2.1%** |
| 2:33 | Escenario «Año El Niño» | El Niño todos los años | Default **9.2% → 4.5%** |
| 2:39 | Cierre | Cajatón 2026 · Reto NEG-01 | — |

Las cifras de los subtítulos **se leen de la pantalla al grabar**, así que siempre coinciden con lo que se ve.
Las de la cartera completa son las mismas de `resultados/CAMBIOS_FASE2.md` y del pitch. Esa simulación se
calcula antes de grabar y el tablero la muestra «desde caché».

## Relación con los casos estrella (lote B)

Los casos E001, E002 y E003 todavía no están en `main`. Por eso esta versión usa solicitudes de la cartera de
demo que muestran lo mismo:

| Caso estrella | Qué debe mostrar | En esta versión |
|---|---|---|
| E001 · Rosa, agricultora en Chepén | Selección por simulación y menos default que la fija | C00006, agrícola en Chepén (default 7.7% → 2.0%). En esta cartera el motor elige aplazamientos, no estacional |
| E002 · Martín, pescador | Banner del ENFEN, alivio y cartera cubierta en el tablero | C00003, pescador en Ascope (cuotas estacionales y alivio) |
| E003 · Luis, bodeguero con otras deudas | El agente reduce el monto y lo explica en el chat | C00006 en el chat (S/ 4,900 → S/ 3,600) |

**Tras la integración de la fase 3** se vuelve a grabar con los tres casos estrella:

```bash
node docs/final/video/grabar_video.mjs --asesor E001 --chat E003 --cliente E002 --nombre cuotaflex-respaldo-final
```

## Cómo volver a grabarlo (unos 4 minutos)

1. API en modo oficial (lee el ENFEN real):
   `ENFEN_MODO=oficial PYTHONPATH=src uvicorn cuotaflex.api.main:app --port 8000`
   (en PowerShell: `$env:ENFEN_MODO="oficial"; $env:PYTHONPATH="src"; uvicorn cuotaflex.api.main:app --port 8000`).
   Con `ENFEN_MODO=demo` también funciona: el script activa la alerta de demo antes de la app del cliente.
2. Apps compiladas: en `web/asesor`, `web/cliente` y `web/tablero`, `npm run build` y
   `npx vite preview --port 5173` (`5174` y `5175` respectivamente).
3. `node docs/final/video/grabar_video.mjs`: el MP4 y el `.srt` quedan en `~/Videos/Thinku`
   (`--salida` para cambiarlo). Necesita Edge o Chrome y `ffmpeg` en el PATH.

El script ([`video/grabar_video.mjs`](video/grabar_video.mjs)) maneja el navegador sin interfaz con el
protocolo de DevTools. Graba solo la página (1920×940) y deja abajo una franja de 140 px para los
subtítulos, para que nunca tapen la interfaz. Además, muestra un cursor rojo en cada clic y rótulos por sección.

## Antes de la final

- [ ] Subirlo al Drive del equipo y pegar el enlace arriba (Stefano).
- [ ] Copiarlo al USB y probar que se reproduce sin internet en las dos laptops (Stefano).
- [ ] Volver a grabarlo con los casos estrella tras la integración de la fase 3, si cambió la interfaz (Stefano).
- [ ] Revisarlo con Joaquin (casos estrella) y Andre (que el guion del pitch y el video digan lo mismo).
