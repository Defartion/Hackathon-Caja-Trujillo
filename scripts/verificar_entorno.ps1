<#
.SYNOPSIS
  ¿Está lista esta laptop para la final? Windows (PowerShell 5.1 o 7).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\verificar_entorno.ps1
  powershell -ExecutionPolicy Bypass -File scripts\verificar_entorno.ps1 -Rapido
  powershell -ExecutionPolicy Bypass -File scripts\verificar_entorno.ps1 -Completo
.NOTES
  Busca un Python (primero el .venv del proyecto) y ejecuta scripts\verificar_entorno.py.
#>
param(
  [switch]$Rapido,
  [switch]$Completo,
  [switch]$SinPruebas,
  [switch]$SinCompilar,
  [switch]$Ayuda
)

$raiz = Split-Path -Parent $PSScriptRoot
$script = Join-Path $raiz 'scripts\verificar_entorno.py'

function Test-Python([string]$Ruta, [string[]]$Previos) {
  # El alias "python" de la Microsoft Store existe aunque Python no esté instalado: hay que ejecutarlo.
  try {
    & $Ruta @Previos -c 'import sys' *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

$python = $null
$previos = @()
foreach ($ruta in @((Join-Path $raiz '.venv\Scripts\python.exe'), (Join-Path $raiz '.venv/bin/python'))) {
  if ((Test-Path $ruta) -and (Test-Python $ruta @())) { $python = $ruta; break }
}
if (-not $python) {
  foreach ($candidato in @(@('py', '-3'), @('python3'), @('python'))) {
    $nombre = $candidato[0]
    $extra = @($candidato | Select-Object -Skip 1)
    if ((Get-Command $nombre -ErrorAction SilentlyContinue) -and (Test-Python $nombre $extra)) {
      $python = $nombre; $previos = $extra; break
    }
  }
}

if (-not $python) {
  Write-Host '[FALLA]' -ForegroundColor Red -NoNewline
  Write-Host ' Python: no está instalado'
  Write-Host '          -> Instala Python 3.10 o más y crea el entorno: py -3 -m venv .venv'
  exit 1
}

$argumentos = @()
if ($Rapido) { $argumentos += '--rapido' }
if ($Completo) { $argumentos += '--completo' }
if ($SinPruebas) { $argumentos += '--sin-pruebas' }
if ($SinCompilar) { $argumentos += '--sin-compilar' }
if ($Ayuda) { $argumentos += '--help' }
$argumentos += $args

& $python @previos $script @argumentos
exit $LASTEXITCODE
