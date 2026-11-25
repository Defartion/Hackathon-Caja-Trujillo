# Vista del comité · PDF de los casos estrella

Expedientes que el Asesor de Negocios envía al Asesor de Riesgos y al comité (fase 4, lote C). Cada
PDF es la página `/comite/<id>` de la app del asesor impresa en A4 vertical (3 páginas): ciclo
estimado, plan frente a la cuota fija, Cuota/UN por etapa, escenarios adversos, cronograma, costos,
supuestos y fuentes, explicación del agente y validación con firmas. Datos sintéticos.

| Caso | Crédito | Resultado del motor |
|---|---|---|
| [E001 · Rosa, arroz en Chepén](comite-E001.pdf) | S/ 7,000 · 24 meses · desembolso 01/12/2026 · TEA 45% · factor 0.85 | Plan factible: gracia en la siembra, cuotas en la cosecha y deuda en 0 al mes 12. Cuota/UN máx. 0.85; la cuota fija supera el factor en 10 etapas. |
| [E002 · Martín, pesca en Pacasmayo](comite-E002.pdf) | S/ 5,200 · 12 meses · desembolso 30/06/2027 · TEA 45% · factor 0.85 | Plan factible: 4 meses de gracia en la veda y deuda en 0 al mes 10. |
| [E003 · Luis, bodega en Trujillo](comite-E003.pdf) | Pidió S/ 8,000 · 12 meses · desembolso 01/12/2026 · TEA 45% · factor 0.85 | No factible al monto pedido: el motor sugiere S/ 1,900 y el asesor aplica el ajuste (queda anotado en el expediente). |

La captura de cada caso es la de `data/ciclos/casos_estrella.json` (lote B). Martín se desembolsa el
30/06/2027: con el 30/04/2027 la veda deja cinco meses sin capacidad de pago, más que los 4 meses de
gracia del producto, y el motor no encuentra plan (monto máximo S/ 200).

## Versión con la que se exportaron
Exportados el 25/11/2026 con la API de `main` más las ramas `fase-4/lote-a-plan` (9f25c9e) y
`fase-4/lote-b-ciclo` (84cbd35), todavía sin integrar. **Hay que volver a exportarlos en la
integración del 1 y 2 de diciembre**, cuando los lotes A, B y D estén en `main`.

## Cómo regenerarlos
```bash
PYTHONPATH=src uvicorn cuotaflex.api.main:app --port 8000   # API con los lotes A y B
cd web/asesor && npm run dev                               # app del asesor en :5173
python docs/demo/comite/exportar.py --capturas             # PDF aquí y capturas en web/asesor/docs/
```
El script recorre el asistente como el asesor (carga el caso, estima el ciclo, propone el plan y
aplica el primer ajuste sugerido si no es factible), guarda el expediente y exporta `/comite/<id>`.
Desde el navegador también sirve el botón **Imprimir o guardar en PDF** de la vista del comité.
