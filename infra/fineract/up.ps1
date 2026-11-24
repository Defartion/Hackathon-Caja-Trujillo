$ErrorActionPreference = "Stop"

$entorno = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path -LiteralPath $entorno -PathType Leaf)) {
    $entorno = Join-Path $PSScriptRoot ".env.example"
}
$compose = @("compose", "--env-file", $entorno, "-f", (Join-Path $PSScriptRoot "docker-compose.yml"))

$reloj = [System.Diagnostics.Stopwatch]::StartNew()
& docker @compose up --detach --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) {
    & docker @compose ps --all
    throw "Docker Compose no pudo levantar Fineract."
}

$direccion = & docker @compose port fineract 8443
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose no pudo identificar el puerto de Fineract."
}
$baseUrl = "https://$($direccion.Trim())/fineract-provider"
& curl.exe --noproxy "*" --insecure --fail --silent --show-error --max-time 10 "$baseUrl/actuator/health" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "La API de Fineract no respondió en $baseUrl."
}

Write-Output "Fineract listo en $([math]::Round($reloj.Elapsed.TotalSeconds)) s."
Write-Output "API $baseUrl/api/v1"
Write-Output "Swagger $baseUrl/swagger-ui/index.html"
