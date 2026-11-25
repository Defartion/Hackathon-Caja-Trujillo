# Contingencias de la final

Cada contingencia tiene un responsable, un tiempo máximo de reacción y una forma de practicarla antes del
evento. **Se ensayan todas el miércoles 2 de diciembre.** Durante la presentación, quien detecta el problema
lo dice en voz baja al responsable y Andre sigue hablando: el jurado no tiene que ver la reparación.

## Las cinco principales

| Si pasa esto | Se nota porque | Qué hacemos | Responsable | Reacción |
|---|---|---|---|---|
| **No hay internet** | Las apps desplegadas no cargan o el ENFEN no responde | Pasar al **modo sin conexión**: `scripts/demo_offline` (lote B) levanta la API local con `ENFEN_MODO=demo`, el core simulado, el agente sin proveedor de IA y las tres apps compiladas. Alternativa: el punto de acceso móvil | Joaquin | 2 min |
| **Fineract no arranca** | `GET /core/estado` dice "no disponible" | Seguir con el **core simulado**: la demo no depende de Fineract (es un espejo). Se muestra el GIF `infra/fineract/demo-espejo.gif` si preguntan. Con el espejo automático del lote A, `CORE_ESPEJO=0` | Sebastian | 1 min |
| **Falla el proveedor de IA** | El chat tarda o responde con plantilla | Nada que hacer en vivo: el agente **ya cae solo a plantillas** con cifras verificadas. Si tarda mucho, reiniciar la API con `CUOTAFLEX_LLM=0` | Andre | Inmediato (1 min si hay que reiniciar) |
| **Falla el proyector** | No hay imagen o se corta | Probar el otro adaptador; si no, **girar la laptop** hacia el jurado y poner el **video de respaldo** desde el USB | Stefano | 2 min |
| **Falla la laptop principal** | Se cuelga, no enciende o no ve el proyector | Pasar a la **segunda laptop**, que tiene todo listo y verificado; quien la tiene la enciende apenas empieza la presentación | Joaquin | 3 min |

## Otras que conviene tener previstas

| Si pasa esto | Qué hacemos | Responsable | Reacción |
|---|---|---|---|
| La URL desplegada no responde | Usar la versión local (o el modo sin conexión) | Sebastian | 2 min |
| La API se cuelga o los datos quedan raros | Reiniciar la API y correr `reset_demo` (lote A) | Sebastian | 1 min |
| El ENFEN oficial no responde | La API usa la caché con "desactualizado"; para el cambio en vivo, `ENFEN_MODO=demo` | Stefano | 1 min |
| Un paso de la demo falla en vivo | No depurar frente al jurado: saltar a ese caso en el **video de respaldo** | Andre | Inmediato |
| Nos recortan el tiempo | Usar la versión de 3 minutos del guion (lote D) | Andre | Inmediato |
| Un error después del congelamiento | No se cambia código: se esquiva con la contingencia que corresponda | Joaquin | — |

## Cómo practicarlas el miércoles 2

1. **Sin internet:** apagar el wifi y recorrer los tres casos estrella con `scripts/demo_offline`.
2. **Fineract:** detener los contenedores y comprobar que la app del asesor y la del cliente siguen funcionando.
3. **IA:** iniciar la API sin clave y hacer las preguntas del guion en el chat.
4. **Proyector:** conectar las dos laptops a un monitor externo con cada adaptador.
5. **Laptop:** cronometrar el cambio de la principal a la de respaldo con la demo abierta.
6. **Video:** reproducirlo desde el USB en las dos laptops, sin internet.
