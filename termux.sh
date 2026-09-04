#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

if ! command -v proot-distro >/dev/null 2>&1; then
    echo "Error: no se encontró proot-distro en Termux." >&2
    echo "Instálalo con: pkg install proot-distro" >&2
    exit 1
fi

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TERMUX_HOME="${HOME:?No se pudo determinar el HOME de Termux}"

case "$PROJECT_DIR" in
    "$TERMUX_HOME"/*)
        PROJECT_IN_UBUNTU="/root/${PROJECT_DIR#"$TERMUX_HOME"/}"
        ;;
    *)
        echo "Error: coloca el proyecto dentro del HOME de Termux: $TERMUX_HOME" >&2
        exit 1
        ;;
esac

printf -v ubuntu_command 'cd %q && exec ./iniciar.sh' "$PROJECT_IN_UBUNTU"
exec proot-distro login --termux-home ubuntu -- bash -lc "$ubuntu_command"
