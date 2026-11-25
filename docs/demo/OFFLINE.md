# Demo sin conexión

## Preparar una vez con conexión

Instala Python 3.10 o posterior, Node.js, curl y las dependencias. Desde la raíz del repositorio en Bash:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m playwright install chromium

export VITE_API_URL=http://127.0.0.1:8000
for app in asesor cliente tablero; do
    (cd "web/$app" && npm ci && npm run build) || exit 1
done
```

En PowerShell desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium

$env:VITE_API_URL = 'http://127.0.0.1:8000'
foreach ($app in 'asesor', 'cliente', 'tablero') {
    Push-Location "web/$app"
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "Falló npm ci en $app" }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Falló la compilación de $app" }
    } finally {
        Pop-Location
    }
}
```

El valor `VITE_API_URL` queda incorporado al compilar. Vuelve a compilar si las apps se construyeron con otra dirección. Conserva `.venv`, `node_modules` y `dist` para la final.

## Arrancar sin conexión

En macOS, Linux o WSL2:

```bash
./scripts/demo_offline.sh
```

En Windows con PowerShell:

```powershell
.\scripts\demo_offline.ps1
```

Espera **Demo local lista**. Abre [Asesor](http://127.0.0.1:5173), [Cliente](http://127.0.0.1:5174/?demo=1) y [Tablero](http://127.0.0.1:5175). Sigue el [guion de los tres casos](CASOS_ESTRELLA.md). Para Martín, añade `&demo=1` a la URL con el número del préstamo. Pulsa **Ctrl+C** en la terminal para detener la demo. Los préstamos, sesiones y alertas de demo se reinician al volver a arrancar.

Los lanzadores usan el core local en memoria, ENFEN en modo demo y el agente con plantillas. El tablero usa un solo proceso de simulación. Los puertos locales requeridos son 8000 y 5173–5175. La primera preparación descarga dependencias. El arranque sirve las compilaciones locales.

El espejo real es una demostración separada. Consulta la [guía de Fineract en PowerShell y WSL2](../../infra/fineract/README.md#windows-con-docker-desktop) si quieres mostrarlo con Docker Desktop.

## Verificar los recorridos y regenerar capturas

```bash
python -m pytest tests/e2e --capturas
```

Se puede ejecutar sin `--capturas` para conservar las imágenes existentes. El comando usa el intérprete del entorno preparado. Las pruebas levantan sus propios servicios en localhost, bloquean cualquier recurso HTTP externo del navegador y fallan si se detecta un intento. Se validan los recorridos del asesor, cliente, ENFEN, tablero y caída de API, así como la explicación del monto de Luis.

Ante la caída deliberada de la API, Chromium informa `ERR_CONNECTION_REFUSED`. Solo se admite ese diagnóstico de transporte del origen local para el que se provoca el corte. Cualquier error de JavaScript u otro error de consola falla la prueba. [Asesor ante la caída](capturas/14-sin-api-asesor.png) · [Cliente ante la caída](capturas/15-sin-api-cliente.png) · [Tablero ante la caída](capturas/16-sin-api-tablero.png)

El 24 de noviembre pasaron los cinco recorridos bajo bloqueo de red en macOS y se comprobaron el arranque y el cierre de ambos lanzadores. La app del asesor, la app del cliente y el tablero cargaron sus recursos en localhost. El lanzador PowerShell se ejecutó con PowerShell 7.7 en macOS.

En macOS se puede aplicar el bloqueo además a los procesos de la API, Vite y Chromium. El siguiente perfil limita su salida a loopback y permite repetir las pruebas sin cambiar la configuración de Wi-Fi del equipo.

```bash
perfil=$(mktemp)
cat > "$perfil" <<'PERFIL'
(version 1)
(allow default)
(deny network-outbound)
(allow network-outbound (remote ip "localhost:*"))
PERFIL
/usr/bin/sandbox-exec -f "$perfil" .venv/bin/python -m pytest tests/e2e --capturas
rm "$perfil"
```
