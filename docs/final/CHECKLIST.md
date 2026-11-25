# Lista de verificación de la final

Se revisa completa el **miércoles 2 de diciembre** (víspera) y en versión corta el **jueves a las 7:30**.
Quien marca cada punto es el responsable indicado. Lo que no esté en verde el miércoles a las 20:00 se
avisa en el canal del equipo.

## Equipo físico

| | Qué | Detalle | Responsable |
|---|---|---|---|
| [ ] | Laptop principal | Repo clonado en `main`, `verificar_entorno` todo en verde, apps compiladas | Stefano |
| [ ] | Laptop de respaldo | Lo mismo que la principal, probada recorriendo la demo completa | Joaquin |
| [ ] | Cargadores | Uno por laptop, más uno de celular | Cada dueño |
| [ ] | Adaptador de video | HDMI y USB-C a HDMI, probados con un monitor externo | Stefano |
| [ ] | Internet propio | Punto de acceso móvil con datos y saldo, probado con las dos laptops | Andre |
| [ ] | Extensión eléctrica | Multitoma de 3 metros o más | Sebastian |
| [ ] | USB de respaldo | Video de respaldo (MP4 1080p), PDF del pitch, resumen impreso en PDF y concepto v2 | Stefano |
| [ ] | Resumen impreso | Copias para el jurado, con el QR | Andre |
| [ ] | Puntero o clicker | Con pilas de repuesto (opcional) | Andre |

## Cuentas y accesos

| | Qué | Detalle | Responsable |
|---|---|---|---|
| [ ] | GitHub | Sesión iniciada en las dos laptops con la **cuenta propia de cada integrante** (los commits del evento quedan a su nombre) | Cada integrante |
| [ ] | Plataforma de despliegue | Sesión iniciada y URLs públicas respondiendo (`deploy/URLS.md`, lote A) | Sebastian |
| [ ] | Correo del equipo | Sesión iniciada para recibir datos o avisos de la organización | Andre |
| [ ] | Drive del equipo | El video de respaldo se puede abrir sin conexión (descargado) | Stefano |
| [ ] | Proveedor de IA (opcional) | Clave en el `.env` local, **nunca** en el repositorio. Sin clave, el agente usa plantillas | Andre |

## Software en cada laptop

| | Qué | Cómo se comprueba | Responsable |
|---|---|---|---|
| [ ] | Python 3.10 o más y dependencias | `verificar_entorno` | Stefano |
| [ ] | Node 18 o más y `node_modules` de las tres apps | `verificar_entorno` (compila las tres apps) | Stefano |
| [ ] | Pruebas | `pytest` completo en verde | Joaquin |
| [ ] | Puertos libres | 8000, 5173, 5174 y 5175 (`verificar_entorno`) | Stefano |
| [ ] | Docker Desktop (opcional) | Imágenes de Fineract ya descargadas (`infra/fineract/up.ps1` o `up.sh` probado) | Joaquin |
| [ ] | Modo sin conexión | `scripts/demo_offline` (lote B) probado con el wifi apagado | Joaquin |
| [ ] | ENFEN | Una lectura oficial reciente en `data/enfen_cache.json` y el modo demo probado | Stefano |
| [ ] | Navegador | Pestañas de las tres apps abiertas, zoom al 100%, sin extensiones que muestren avisos | Andre |
| [ ] | Pantalla limpia | Notificaciones silenciadas (modo "No molestar"), escritorio sin archivos personales, sin datos personales a la vista | Cada dueño |

## Datos de la demo

| | Qué | Responsable |
|---|---|---|
| [ ] | `reset_demo` deja la demo limpia en menos de 10 s (lote A) | Sebastian |
| [ ] | Casos estrella E001, E002 y E003 dan su resultado (lote B) | Joaquin |
| [ ] | Cifras del pitch iguales a `resultados/resumen.json` | Andre |

## Versión corta (jueves 7:30 y viernes 8:00)

1. Las dos laptops encendidas y cargando.
2. `verificar_entorno` en verde en las dos.
3. Internet del evento y punto de acceso móvil probados.
4. Proyector o pantalla probados con el adaptador.
5. USB con el video y el PDF a mano.
6. URLs desplegadas respondiendo.
