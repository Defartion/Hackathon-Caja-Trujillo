#!/usr/bin/env bash
# Deja la demo limpia: vacía el core simulado y siembra los préstamos de demo.
# Uso: scripts/reset_demo.sh [URL_API] [PIN_SUPERVISOR]
set -euo pipefail
API="${1:-${PUBLIC_API_URL:-http://localhost:8000}}"
PIN="${2:-${PIN_SUPERVISOR:-3333}}"
AUTH=()
if curl -fsS "$API/auth/config" | grep -q '"auth":true'; then
  RESP=$(curl -sS -X POST "$API/auth/login" -H 'Content-Type: application/json' \
         -d "{\"rol\":\"supervisor\",\"pin\":\"$PIN\"}")
  TOKEN=$(printf '%s' "$RESP" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("token",""))' 2>/dev/null || true)
  if [ -z "$TOKEN" ]; then echo "No se pudo iniciar sesión como supervisor (¿PIN correcto?)." >&2; exit 1; fi
  AUTH=(-H "Authorization: Bearer $TOKEN")
fi
inicio=$(date +%s)
curl -fsS -X POST "$API/admin/reset" "${AUTH[@]}" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("Demo reiniciada:", d["prestamos"], "préstamos sembrados", [s["loanId"] for s in d["sembrados"]])'
echo "Listo en $(( $(date +%s) - inicio )) s"
