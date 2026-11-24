#!/usr/bin/env bash
# Inicia la demo local con las tres aplicaciones compiladas.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
raiz="$PWD"
python_ejecutable="${CUOTAFLEX_PYTHON:-$raiz/.venv/bin/python}"
if [[ ! -x "$python_ejecutable" && -z "${CUOTAFLEX_PYTHON:-}" ]]; then
    python_ejecutable=python3
fi
if ! "$python_ejecutable" -c 'import uvicorn, pypdf' 2>/dev/null; then
    printf 'Prepara el entorno de Python antes de desconectarte. Consulta docs/demo/OFFLINE.md.\n' >&2
    exit 1
fi
command -v node >/dev/null || { printf 'Node.js debe estar instalado.\n' >&2; exit 1; }

apps=(asesor cliente tablero)
puertos=(5173 5174 5175)
for app in "${apps[@]}"; do
    if [[ ! -f "web/$app/dist/index.html" || ! -f "web/$app/node_modules/vite/bin/vite.js" ]]; then
        printf 'Falta preparar web/%s. Consulta docs/demo/OFFLINE.md.\n' "$app" >&2
        exit 1
    fi
done

temporal="$(mktemp -d "${TMPDIR:-/tmp}/cuotaflex-offline.XXXXXX")"
procesos=()
limpiar() {
    if (( ${#procesos[@]} )); then
        kill "${procesos[@]}" 2>/dev/null || true
        wait "${procesos[@]}" 2>/dev/null || true
    fi
    rm -rf -- "$temporal"
}
trap limpiar EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

export ENFEN_MODO=demo ENFEN_REVISION_AUTOMATICA=0 CUOTAFLEX_LLM=0 CUOTAFLEX_SIM_PROCESOS=1
export PYTHONPATH="$raiz/src" NOTIFICACIONES_ARCHIVO="$temporal/notificaciones.json"
unset FINERACT_URL FINERACT_USER FINERACT_PASSWORD

"$python_ejecutable" -m uvicorn cuotaflex.api.main:app --host 127.0.0.1 --port 8000 &
procesos+=("$!")
for i in "${!apps[@]}"; do
    (
        cd -- "web/${apps[i]}"
        exec node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port "${puertos[i]}" --strictPort
    ) &
    procesos+=("$!")
done

urls=(http://127.0.0.1:8000/motor/parametros)
for puerto in "${puertos[@]}"; do
    urls+=("http://127.0.0.1:$puerto")
done
for i in "${!urls[@]}"; do
    inicio=$SECONDS
    until curl --noproxy '*' --fail --silent --max-time 1 "${urls[i]}" >/dev/null; do
        if ! kill -0 "${procesos[i]}" 2>/dev/null || (( SECONDS - inicio >= 75 )); then
            printf 'No arrancó %s. Revisa el registro y si el puerto está ocupado.\n' "${urls[i]}" >&2
            exit 1
        fi
        sleep 0.25
    done
    if ! kill -0 "${procesos[i]}" 2>/dev/null; then
        printf 'El proceso de %s terminó. Revisa si el puerto está ocupado.\n' "${urls[i]}" >&2
        exit 1
    fi
done
printf '\nDemo local lista. Presiona Ctrl+C para detenerla.\n'
printf 'Asesor   %s\nCliente  %s/?demo=1\nTablero  %s\n' "${urls[1]}" "${urls[2]}" "${urls[3]}"
while true; do
    for proceso in "${procesos[@]}"; do
        if ! kill -0 "$proceso" 2>/dev/null; then
            printf 'Un servicio de la demo terminó. Revisa el registro.\n' >&2
            exit 1
        fi
    done
    sleep 1
done
