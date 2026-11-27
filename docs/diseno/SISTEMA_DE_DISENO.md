# Sistema de diseño de Thinku

Una sola identidad para las tres apps (asesor, cliente y tablero) y la portada. Moderno, pero serio:
es una herramienta de crédito de Caja Trujillo.

**Nombre.** El sistema se llamaba CuotaFlex y ahora se muestra como **Thinku**: logo, títulos de pestaña, portada,
acceso, agente, avisos por SMS, exportaciones (`thinku-<tabla>-<fecha>.<formato>`) y gráficos ("Fija" frente a
"Thinku"). El nombre va en un solo color junto al símbolo. Lo interno no cambia: el paquete `cuotaflex`, las
variables `CUOTAFLEX_*` y las claves guardadas `cuotaflex.*` siguen igual para no romper sesiones ni despliegues.

## Ideas que lo guían

1. **El rojo es Caja Trujillo.** Se usa para la marca y para la acción principal de cada pantalla.
   No se usa como adorno (se quitaron las líneas rojas bajo las cabeceras).
2. **Las cifras mandan.** Montos, cuotas y KPI van en Archivo condensada y con números tabulares. Es el dato
   que miran el asesor, el cliente y el supervisor.
3. **Un solo adorno, y con sentido: el ritmo de cuotas.** Barras que suben y bajan con la temporada frente a la
   línea de una cuota fija. Es la idea del producto. Aparece en el símbolo de la marca, en la pantalla de acceso,
   en la portada y, con los datos reales, en la tarjeta de la próxima cuota del cliente.
4. **Calma alrededor.** Hojas blancas con borde fino sobre un fondo gris azulado. La sombra queda solo para lo que
   flota: menús, chat del agente, modales y barras fijas.

## Tokens (`web/*/src/tema.css`)

| Token | Valor | Uso |
|---|---|---|
| `--cf-rojo` | `#C8102E` | marca, acción principal (hover `--cf-rojo-hover` `#A50D26`) |
| `--cf-rojo-osc` / `--cf-rojo-suave` | `#8E0B20` / `#FDECEF` | textos y fondos de alerta |
| `--cf-tinta` (= `--cf-gris-900`) | `#172033` | texto y menú lateral |
| `--cf-gris-600` | `#5A6478` | texto secundario (5.9:1 sobre blanco) |
| `--cf-gris-200` / `--cf-gris-100` | `#E2E6ED` / `#EEF1F5` | bordes finos / fondos de grupos |
| `--cf-fondo` | `#F2F4F7` | fondo de las apps |
| `--cf-azul` | `#0B5CAD` | serie Thinku en gráficos, enlaces, foco |
| `--cf-verde`, `--cf-ambar` | `#1A7F37`, `#B7791F` | estados (con su versión `-osc` para texto y `-suave` para fondo) |
| `--cf-radio-sm` / `--cf-radio` / `--cf-radio-lg` | 8 / 12 / 16 px | controles / tarjetas pequeñas / hojas |
| `--cf-superficie` / `--cf-superficie-alt` | `#FFFFFF` / `#F7F8FA` | tarjetas, campos y menús / fila resaltada |
| `--cf-elevada` | `#FFFFFF` | lo seleccionado sobre un riel gris (segmentos, pestañas) |
| `--cf-lateral` | `#172033` | barra lateral del asesor y del supervisor |
| `--cf-vidrio` / `--cf-velo` | blanco 92 % / tinta 45 % | barras fijas translúcidas / fondo detrás de modales y hojas |
| `--cf-rojo-texto` | `#C8102E` | rojo para texto e iconos (en oscuro pasa a `#FF7A8F`) |
| `--cf-graf-*` | ver abajo | colores de los gráficos, con su versión oscura |

`--cf-blanco` queda solo para texto sobre rojo, verde o tinta; las superficies usan `--cf-superficie`, así el tema
oscuro cambia una variable y no cada regla.

Gráficos: la cuota fija va en pizarra `#8792A6` y Thinku en azul `#0B5CAD`. El par pasa el control de distinción
para visión normal y daltonismo (ΔE 21; el gris anterior, `#57606A`, quedaba en 12.8). El texto de las leyendas usa la tinta.

## Tema oscuro

Se elige en el perfil del cliente (Claro, Oscuro o Automático), con el interruptor de la barra lateral del asesor y del
supervisor, en el menú del cliente, en la pantalla de acceso y en la portada. Sin elección sigue al sistema.

- **Cómo funciona.** `apariencia.tsx` pone `data-tema="oscuro"` en `<html>` y guarda la elección en `localStorage`
  (`cuotaflex.tema`, la misma clave en las tres apps y la portada). Un script en línea de cada `index.html` aplica el
  tema antes de pintar, para que no haya un destello blanco.
- **Paleta.** Fondo azul noche `#0D121C`, superficies un paso más claras (`#151C29`), tinta `#E7EBF2`. El rojo de la
  marca no cambia en botones ni en bandas; el rojo, azul, verde y ámbar de texto pasan a versiones más claras.
- **Gráficos.** Las reglas `:is(.recharts-wrapper, .cf-graf) [fill="…"]` de `tema.css` cambian los colores de datos sin
  tocar los componentes. La pareja oscura Thinku `#55A3F0` / cuota fija `#626E83` se validó contra `#151C29`
  (ΔE 19.3 con visión normal, 18.3 con deuteranopía). Para muestras de color en HTML (leyendas) se usa `colorTema()`.
- **Papel siempre claro.** El expediente del comité lleva `.cf-claro` y se ve como una hoja blanca; al imprimir
  o guardar en PDF todo vuelve al tema claro.

## Exportar

`exportar.ts` y `MenuExportar.tsx` (copias idénticas) generan los archivos en el navegador, sin dependencias nuevas:

| Formato | Qué lleva |
|---|---|
| PDF | Helvetica estándar, A4 vertical u horizontal según las columnas, banda de la marca, resumen, tablas con cabecera repetida y número de página |
| Excel (.xlsx) | hoja "Resumen" y una hoja por tabla, con formato de soles, porcentaje y fecha, fila de títulos fija y filtros |
| CSV | la tabla principal, UTF-8 con BOM para que Excel lea las tildes |
| JSON | valores sin formato (números, fechas ISO, porcentajes como fracción) y la descripción de cada columna |
| Texto (.txt) | resumen y columnas alineadas |

Está en el cronograma del cliente ("Descargar"), la bandeja, la lista y el detalle de préstamos del asesor, y los
resultados de cada corrida del tablero.

## Vistas amplias, columnas a elección y paneles plegables

- **Más espacio para los datos.** El contenido del asesor llega a 1600 px (con margen lateral que crece con la
  pantalla) y el tablero a 1280 px, con gráficos de 280 px de alto.
- **Columnas de la bandeja.** El botón "Columnas" abre un panel con vistas rápidas (Esenciales, Recomendadas,
  Capacidad y riesgo, Todas), las 13 columnas opcionales y la altura de filas (Cómodas o Compactas). "Código" siempre
  se muestra. La elección se guarda en el navegador (`cuotaflex.bandeja.columnas` y `cuotaflex.bandeja.filas`) y
  "Restablecer" vuelve a la vista recomendada. En el teléfono la tabla muestra código, rubro y monto, y el botón
  no aparece.
- **Tablas anchas.** Si las columnas no entran, la tabla se desliza de lado: "Código" y "Ver" quedan fijos y una sombra
  suave en el borde avisa que hay más columnas a ese lado. El foco del teclado se dibuja alrededor de toda la fila.
- **Menús plegables.** La barra lateral del asesor y la del supervisor se pliegan a una columna de iconos con el botón
  de la esquina (`<IconoPanel />`). Los nombres siguen disponibles para lectores de pantalla y como ayuda al pasar el
  mouse. La preferencia (`cuotaflex.menu`) es la misma en las dos apps.
- **Controles del supervisor.** "1. Elige un escenario" y "2. Ajustes avanzados" se abren y cierran como acordeón;
  cerrados muestran un resumen ("Base", "Con cambios"). El botón de la esquina reduce el panel a un riel de 64 px con
  el escenario activo y el botón de simular, para dejar el ancho a los resultados.
- **Recordar preferencias.** `useGuardado()` (en `apariencia.tsx`) guarda un valor de texto en `localStorage` y
  vuelve al valor inicial si lo guardado no es válido.

## Tipografía

**Archivo** (Omnibus-Type, fundidora argentina; licencia OFL), variable en peso y ancho. Va empaquetada con cada app
(`@fontsource-variable/archivo`), así que funciona sin internet, como pide la demo sin conexión.

- Texto: 14 px en asesor y tablero, 16 px en el cliente.
- Títulos: peso 680–720, interletrado ligeramente negativo.
- Cifras grandes: clase `.cf-cifra` o `font-stretch: var(--cf-cifra-ancho)` (84 %) con `tabular-nums`.

## Componentes compartidos (copias idénticas en las 3 apps)

| Archivo | Qué tiene |
|---|---|
| `tema.css` | tokens, base, marca, ritmo de cuotas y pantalla de acceso |
| `marca.tsx` | `<Marca />` (símbolo y nombre), `<Simbolo />` y `<Ritmo />` |
| `sesion.tsx` | `<ConSesion>`: ingresar, crear cuenta o PIN; `usuarioSesion()`, `perfilSesion()` y `cerrarSesion()` |
| `apariencia.tsx` | tema claro u oscuro (`useTema()`, `<BotonTema />`, `<SelectorTema />`, `colorTema()`), `useGuardado()` y `<IconoPanel />` |
| `exportar.ts` | PDF, XLSX, CSV, JSON y TXT a partir de un `Documento` (resumen y tablas) |
| `MenuExportar.tsx` | botón "Exportar" con los cinco formatos, navegable con el teclado |

Cada app se compila sola (Docker copia solo `web/<app>/`), por eso van copiados. **Si cambias uno, copia la versión de
`web/asesor/src/` a las otras dos.** `tests/test_web_tema.py` falla si las copias se separan.

## De dónde salió cada decisión

Se mezclaron las referencias con una sola regla: que todo se vea de la misma familia.

- **ui-ux-pro-max-skill:** para banca y finanzas recomienda estilo sobrio de tipo suizo, accesible y que transmita
  confianza. De ahí salen la paleta contenida, las reglas de contraste 4.5:1, los objetivos táctiles de 44 px y los
  formularios con errores junto al campo.
- **anthropics/skills (frontend-design):** una idea fuerte y lo demás tranquilo (el ritmo de cuotas), tipografía elegida
  para el tema y textos simples desde el punto de vista de quien usa la app.
- **vercel-labs/agent-skills (web-design-guidelines):** foco visible, `autocomplete` en cada campo, pegar permitido,
  `aria-live` en avisos, `prefers-reduced-motion`, `…` en estados de carga y transiciones solo de propiedades concretas.
- **RareUI:** la entrada del PIN en casillas, al estilo de su OTP Input, hecha en CSS sin dependencias nuevas.
- **Lucian UX/UI:** patrones de acceso (pestañas con indicador que se desliza, medidor de seguridad de la contraseña,
  la tarjeta que se sacude ante una contraseña incorrecta), reescritos con los tokens del sistema.

No se agregaron Tailwind ni librerías de animación: el diseño vive en CSS con variables, como ya estaba el proyecto.

## Accesibilidad

Contraste AA en texto, foco visible en todo control, navegación por teclado en las pestañas de acceso (flechas),
errores asociados a su campo (`aria-describedby`) y movimiento reducido cuando el sistema lo pide.

## Capturas

| | |
|---|---|
| ![Acceso del asesor](capturas/01-acceso-asesor.png) | ![Crear cuenta en el celular](capturas/02-crear-cuenta-cliente.png) |
| ![Bandeja del asesor](capturas/03-asesor-bandeja.png) | ![Ficha y propuesta del agente](capturas/04-asesor-ficha.png) |
| ![Inicio del cliente](capturas/05-cliente-inicio.png) | ![Tablero del supervisor](capturas/06-tablero.png) |
| ![Inicio del cliente en tema oscuro](capturas/07-cliente-inicio-oscuro.png) | ![Detalle de una cuota](capturas/08-cliente-detalle-cuota.png) |
| ![Elegir qué cuota pagar](capturas/09-cliente-pagar-cuota.png) | ![Detalle de un préstamo registrado](capturas/10-asesor-prestamo.png) |
| ![Regla del ajuste por visita](capturas/11-asesor-regla.png) | ![Tablero en tema oscuro](capturas/12-tablero-oscuro.png) |
| ![Columnas de la bandeja](capturas/13-asesor-columnas.png) | ![Bandeja con el menú plegado y filas compactas](capturas/14-asesor-menu-plegado.png) |
| ![Paso 1 del tablero cerrado](capturas/15-tablero-escenario-cerrado.png) | ![Tablero con menú y controles plegados](capturas/16-tablero-plegado.png) |
