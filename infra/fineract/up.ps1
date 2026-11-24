param(
    [ValidateRange(1, 1800)][int]$EsperaSegundos = 300,
    [switch]$SinDescargas
)

$ErrorActionPreference = "Stop"
$docker = (Get-Command docker -CommandType Application | Select-Object -First 1).Source
$curl = (Get-Command curl.exe, curl -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1).Source
if (-not $curl) {
    throw "Instala curl o usa infra/fineract/up.sh desde Ubuntu en WSL2."
}
$tipo = & $docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $tipo -ne "linux") {
    throw "Inicia Docker Desktop en modo contenedores Linux y verifica la integración con WSL2."
}

$entorno = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path -LiteralPath $entorno -PathType Leaf)) {
    $entorno = Join-Path $PSScriptRoot ".env.example"
}
$compose = @("compose", "--env-file", $entorno, "-f", (Join-Path $PSScriptRoot "docker-compose.yml"))
$opciones = @("up", "--detach", "--wait", "--wait-timeout", $EsperaSegundos)
if ($SinDescargas) {
    $opciones += @("--pull", "never")
}

$reloj = [System.Diagnostics.Stopwatch]::StartNew()
& $docker @compose @opciones
if ($LASTEXITCODE -ne 0) {
    & $docker @compose ps --all
    & $docker @compose logs --tail 50 db fineract
    throw "Docker Compose no pudo levantar Fineract. Consulta el procedimiento WSL2 en infra/fineract/README.md."
}

$direccion = & $docker @compose port fineract 8443
if ($LASTEXITCODE -ne 0 -or -not $direccion) {
    throw "Docker Compose no pudo identificar el puerto de Fineract."
}
$baseUrl = "https://$($direccion.Trim())/fineract-provider"
& $curl --noproxy "*" --insecure --fail --silent --show-error --max-time 10 "$baseUrl/actuator/health" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "La API de Fineract no respondió en $baseUrl."
}

$reloj.Stop()
Write-Output "Fineract listo en $([math]::Round($reloj.Elapsed.TotalSeconds)) s."
Write-Output "API $baseUrl/api/v1"
Write-Output "Swagger $baseUrl/swagger-ui/index.html"

$contenedores = & $docker @compose ps --quiet
if ($LASTEXITCODE -eq 0 -and $contenedores) {
    & $docker stats --no-stream --format "table {{.Name}}`t{{.MemUsage}}" @contenedores
}
