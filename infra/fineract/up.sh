#!/usr/bin/env bash
set -euo pipefail

directorio="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
entorno="$directorio/.env"
if [[ ! -f "$entorno" ]]; then
    entorno="$directorio/.env.example"
fi

compose=(docker compose --env-file "$entorno" -f "$directorio/docker-compose.yml")
inicio=$SECONDS
if ! "${compose[@]}" up --detach --wait --wait-timeout 300; then
    "${compose[@]}" ps --all
    exit 1
fi

direccion="$("${compose[@]}" port fineract 8443)"
base_url="https://$direccion/fineract-provider"
curl --noproxy '*' --insecure --fail --silent --show-error --max-time 10 \
    "$base_url/actuator/health" >/dev/null

printf 'Fineract listo en %s s.\nAPI %s/api/v1\nSwagger %s/swagger-ui/index.html\n' \
    "$((SECONDS - inicio))" "$base_url" "$base_url"
