#!/usr/bin/env bash
# ¿Está lista esta laptop para la final? Linux, Mac o Git Bash en Windows.
#   scripts/verificar_entorno.sh               todo (pytest rápido y compilación de las apps)
#   scripts/verificar_entorno.sh --rapido      solo lo que no tarda
#   scripts/verificar_entorno.sh --completo    con pytest completo
# Busca un Python (primero el .venv del proyecto) y ejecuta scripts/verificar_entorno.py.
set -u
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROJO=$'\033[31m'
NORMAL=$'\033[0m'
if [ ! -t 1 ] || [ -n "${NO_COLOR:-}" ]; then
  ROJO=""; NORMAL=""
else
  export VERIFICAR_COLOR=1  # Python no siempre detecta la terminal de Git Bash
fi

PYTHON=""
for candidato in "$RAIZ/.venv/bin/python" "$RAIZ/.venv/Scripts/python.exe" python3 python; do
  if command -v "$candidato" >/dev/null 2>&1 && "$candidato" -c "import sys" >/dev/null 2>&1; then
    PYTHON="$candidato"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "${ROJO}[FALLA]${NORMAL} Python: no está instalado"
  echo "          → Instala Python 3.10 o más y crea el entorno: python3 -m venv .venv"
  exit 1
fi

exec "$PYTHON" "$RAIZ/scripts/verificar_entorno.py" "$@"
