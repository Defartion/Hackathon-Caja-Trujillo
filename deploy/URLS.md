# URLs de la demo desplegada

Vercel (plan Hobby, gratuito). Proyecto `cuotaflex`, rama de producción `main`: cada push a `main` vuelve a desplegar.
Almacén duradero: Upstash Redis `thinku-kv` (plan Free, us-east-1), conectado al proyecto en Production, Preview y
Development. Ahí duran las llaves del equipo, las cuentas y los préstamos registrados.

| Servicio | URL | Cómo se entra |
|---|---|---|
| Portada | https://cuotaflex.vercel.app/ | elegir el rol |
| App del asesor | https://cuotaflex.vercel.app/asesor/ | usuario + PIN personal (lo crea un supervisor en Equipo) |
| App del cliente | https://cuotaflex.vercel.app/cliente/ | número de préstamo + código (lo da el asesor; demo: préstamos 2 y 4) |
| Tablero | https://cuotaflex.vercel.app/tablero/ | usuario + PIN personal; usar tamaño "Rápido" |
| API (docs) | https://cuotaflex.vercel.app/api/docs | |

Los PIN generales de cada rol siguen sirviendo como llave maestra de demostración (enlace "Entrar con el PIN
general" en cada app). No están en el repo (es público): están en las variables de entorno del proyecto en Vercel.
Pídeselos a Sebastian.

Fecha del despliegue: 2026-11-25. Llaves personales y Upstash: 2026-11-27.
