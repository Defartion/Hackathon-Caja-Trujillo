# Inicia la demo local con las tres aplicaciones compiladas.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = $env:CUOTAFLEX_PYTHON
if (-not $python) {
    $python = Join-Path $raiz ".venv/Scripts/python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        $python = (Get-Command python -CommandType Application | Select-Object -First 1).Source
    }
}
$node = (Get-Command node -CommandType Application | Select-Object -First 1).Source
$curl = (Get-Command curl.exe, curl -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1).Source
if (-not $curl) {
    throw "Se requiere curl para comprobar los servicios en localhost."
}
& $python -c "import uvicorn, pypdf"
if ($LASTEXITCODE -ne 0) {
    throw "Prepara el entorno de Python antes de desconectarte. Consulta docs/demo/OFFLINE.md."
}

$apps = [ordered]@{ asesor = 5173; cliente = 5174; tablero = 5175 }
foreach ($app in $apps.Keys) {
    $carpeta = Join-Path $raiz "web/$app"
    if (-not (Test-Path (Join-Path $carpeta "dist/index.html") -PathType Leaf) -or
        -not (Test-Path (Join-Path $carpeta "node_modules/vite/bin/vite.js") -PathType Leaf)) {
        throw "Falta preparar web/$app. Consulta docs/demo/OFFLINE.md."
    }
}
$temporal = Join-Path ([System.IO.Path]::GetTempPath()) ("cuotaflex-offline-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $temporal | Out-Null
$variables = @{
    ENFEN_MODO = "demo"
    ENFEN_REVISION_AUTOMATICA = "0"
    CUOTAFLEX_SIM_PROCESOS = "1"
    CUOTAFLEX_LLM = "0"
    PYTHONPATH = (Join-Path $raiz "src")
    NOTIFICACIONES_ARCHIVO = (Join-Path $temporal "notificaciones.json")
    FINERACT_URL = $null
    FINERACT_USER = $null
    FINERACT_PASSWORD = $null
}
$anteriores = @{}
$servicios = [ordered]@{}
$api = "http://127.0.0.1:8000/motor/parametros"

try {
    foreach ($nombre in $variables.Keys) {
        $anteriores[$nombre] = [Environment]::GetEnvironmentVariable($nombre, "Process")
        [Environment]::SetEnvironmentVariable($nombre, $variables[$nombre], "Process")
    }
    $servicios[$api] = Start-Process -PassThru -NoNewWindow -WorkingDirectory $raiz -FilePath $python `
        -ArgumentList "-m", "uvicorn", "cuotaflex.api.main:app", "--host", "127.0.0.1", "--port", "8000"
    foreach ($app in $apps.Keys) {
        $puerto = $apps[$app]
        $servicios["http://127.0.0.1:$puerto"] = Start-Process -PassThru -NoNewWindow -FilePath $node `
            -WorkingDirectory (Join-Path $raiz "web/$app") `
            -ArgumentList "node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", $puerto, "--strictPort"
    }

    foreach ($url in $servicios.Keys) {
        $reloj = [Diagnostics.Stopwatch]::StartNew()
        $listo = $false
        while (-not $listo) {
            if ($servicios[$url].HasExited -or $reloj.Elapsed.TotalSeconds -ge 75) {
                throw "No arrancó $url. Revisa el registro y si el puerto está ocupado."
            }
            & $curl --noproxy "*" --fail --silent --max-time 1 $url | Out-Null
            $listo = ($LASTEXITCODE -eq 0) -and (-not $servicios[$url].HasExited)
            if (-not $listo) {
                Start-Sleep -Milliseconds 250
            }
        }
    }

    Write-Host "`nDemo local lista. Presiona Ctrl+C para detenerla."
    Write-Host "Asesor   http://127.0.0.1:5173"
    Write-Host "Cliente  http://127.0.0.1:5174/?demo=1"
    Write-Host "Tablero  http://127.0.0.1:5175"
    while ($true) {
        foreach ($proceso in $servicios.Values) {
            if ($proceso.HasExited) {
                throw "Un servicio de la demo terminó. Revisa el registro."
            }
        }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($proceso in $servicios.Values) {
        if (-not $proceso.HasExited) {
            Stop-Process -Id $proceso.Id -ErrorAction SilentlyContinue
            $null = $proceso.WaitForExit(3000)
        }
    }
    foreach ($nombre in $anteriores.Keys) {
        [Environment]::SetEnvironmentVariable($nombre, $anteriores[$nombre], "Process")
    }
    Remove-Item -LiteralPath $temporal -Recurse -Force
}
