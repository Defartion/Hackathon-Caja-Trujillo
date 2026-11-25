#!/usr/bin/env bash
# Compila las tres apps para servirlas desde server.py en una sola URL (Vercel u otro host):
#   /asesor/  /cliente/  /tablero/   con la API en /api (misma URL, sin CORS).
# Deja el resultado en public/<app>/. Volver a correrlo cada vez que cambie algo en web/*.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
for app in asesor cliente tablero; do
  echo "== $app"
  (cd "$RAIZ/web/$app" && npm ci --no-audit --no-fund >/dev/null && VITE_API_URL=/api npx vite build --base="/$app/" --outDir "$RAIZ/public/$app" --emptyOutDir)
done
echo "Listo: $(du -sh "$RAIZ/public" | cut -f1) en public/"
