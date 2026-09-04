#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

if [[ "${BOT_IN_UBUNTU:-}" != "1" ]]; then
    if ! command -v proot-distro >/dev/null 2>&1; then
        echo "Error: no se encontró proot-distro en Termux." >&2
        echo "Instálalo con: pkg install proot-distro" >&2
        exit 1
    fi

    if command -v termux-wake-lock >/dev/null 2>&1; then
        termux-wake-lock
        wake_lock_active=1
        trap 'if (( wake_lock_active == 1 )); then termux-wake-unlock; fi' EXIT INT TERM
    else
        echo "Aviso: termux-wake-lock no está disponible; Android podría suspender el proceso." >&2
        echo "Instálalo con: pkg install termux-tools" >&2
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

    printf -v ubuntu_command 'cd %q && exec bash ./termux.sh' "$PROJECT_IN_UBUNTU"
    while true; do
        if proot-distro login --termux-home ubuntu -- env BOT_IN_UBUNTU=1 bash -lc "$ubuntu_command"; then
            exit 0
        else
            proot_status=$?
        fi
        echo "La sesión de Ubuntu terminó (código $proot_status). Reintentando en 15 segundos..." >&2
        sleep 15
    done
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: no se encontró python3 dentro de Ubuntu." >&2
    if command -v apt >/dev/null 2>&1; then
        echo "Instalando Python dentro de Ubuntu..."
        apt update
        apt install -y python3 python3-venv python3-pip
    else
        echo "Instálalo con: apt update && apt install -y python3 python3-venv python3-pip" >&2
        exit 1
    fi
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "Error: falta python3-venv dentro de Ubuntu." >&2
    if command -v apt >/dev/null 2>&1; then
        apt update
        apt install -y python3-venv python3-pip
    else
        exit 1
    fi
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_MAJOR="${PYTHON_VERSION%%.*}"
PYTHON_MINOR="${PYTHON_VERSION#*.}"
if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 10) )); then
    echo "Error: se necesita Python 3.10 o superior. Detectado: $PYTHON_VERSION" >&2
    exit 1
fi

if [[ ! -d .venv ]]; then
    echo "Creando entorno virtual..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt

if [[ ! -f .env ]]; then
    cp .env.example .env
fi

if grep -q '^TELEGRAM_TOKEN=pon_aqui_el_token_del_bot$' .env; then
    printf "Introduce el token de Telegram (la entrada no se mostrará): "
    read -r -s telegram_token
    printf '\n'

    if [[ -z "$telegram_token" ]]; then
        echo "Error: el token no puede estar vacío." >&2
        exit 1
    fi
    if [[ ! "$telegram_token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
        echo "Error: el formato del token no parece válido." >&2
        exit 1
    fi

    sed -i "s/^TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=$telegram_token/" .env
    echo "Token guardado en .env"
fi

echo "Iniciando bot dentro de Ubuntu..."
while true; do
    if python bot.py; then
        bot_status=0
    else
        bot_status=$?
    fi
    if (( bot_status == 130 || bot_status == 143 )); then
        echo "Bot detenido por el usuario."
        exit 0
    fi
    echo "El bot se detuvo (código $bot_status). Reintentando en 15 segundos..." >&2
    sleep 15
done
