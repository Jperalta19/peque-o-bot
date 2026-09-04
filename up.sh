#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

if ! command -v git >/dev/null 2>&1; then
    echo "Error: no se encontró git en el entorno actual." >&2
    echo "En Ubuntu instala git con: apt update && apt install -y git" >&2
    echo "En Termux instala git con: pkg install git" >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: esta carpeta no es un repositorio Git." >&2
    exit 1
fi

branch="$(git branch --show-current)"
if [[ -z "$branch" ]]; then
    echo "Error: no se pudo determinar la rama actual." >&2
    exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
    echo "Error: el repositorio no tiene configurado el remoto origin." >&2
    exit 1
fi

echo "Actualizando origin/$branch..."
git pull --rebase --autostash origin "$branch"

echo "Cambios actualizados. Iniciando el bot dentro de Ubuntu..."
exec ./termux.sh
