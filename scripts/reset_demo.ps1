# Deja la demo limpia: vacía el core simulado y siembra los préstamos de demo.
# Uso: .\scripts\reset_demo.ps1 [-Api http://localhost:8000] [-Pin 3333]
param([string]$Api = $(if ($env:PUBLIC_API_URL) { $env:PUBLIC_API_URL } else { "http://localhost:8000" }),
      [string]$Pin = $(if ($env:PIN_SUPERVISOR) { $env:PIN_SUPERVISOR } else { "3333" }))
$ErrorActionPreference = "Stop"
$headers = @{}
if ((Invoke-RestMethod "$Api/auth/config").auth) {
  $token = (Invoke-RestMethod -Method Post "$Api/auth/login" -ContentType "application/json" `
            -Body (@{ rol = "supervisor"; pin = $Pin } | ConvertTo-Json)).token
  $headers["Authorization"] = "Bearer $token"
}
$t = [Diagnostics.Stopwatch]::StartNew()
$r = Invoke-RestMethod -Method Post "$Api/admin/reset" -Headers $headers
Write-Host "Demo reiniciada: $($r.prestamos) préstamos sembrados ($($r.sembrados.loanId -join ', '))"
Write-Host "Listo en $([math]::Round($t.Elapsed.TotalSeconds,1)) s"
