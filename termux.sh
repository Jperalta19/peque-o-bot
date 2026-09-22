#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

cd "$(dirname "$0")"
command -v python >/dev/null || { echo "Instala Python con: pkg install python"; exit 1; }
command -v ffmpeg >/dev/null || { echo "Instala ffmpeg con: pkg install ffmpeg"; exit 1; }

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf 'Edita .env y configura TELEGRAM_TOKEN antes de iniciar.\n'
  exit 1
fi

network_is_available() {
  python - <<'PY'
import urllib.request

try:
    request = urllib.request.Request("https://api.telegram.org", method="HEAD")
    with urllib.request.urlopen(request, timeout=8):
        pass
except Exception:
    raise SystemExit(1)
PY
}

while true; do
  if python bot.py; then
    bot_status=0
  else
    bot_status=$?
  fi

  if [[ "$bot_status" == "130" || "$bot_status" == "143" ]]; then
    printf 'Bot detenido por el usuario.\n'
    exit 0
  fi

  printf 'El bot se detuvo (código %s). Esperando conexión para reiniciar...\n' "$bot_status" >&2
  until network_is_available; do
    printf 'Sin conexión con api.telegram.org. Reintentando en 15 segundos...\n' >&2
    sleep 15
  done
  printf 'Conexión recuperada. Reiniciando el bot en 3 segundos...\n' >&2
  sleep 3
done
