# Bot descargador de Telegram

Bot en Python para recibir enlaces y devolver vídeos de:

- Instagram: reels, publicaciones y, si la URL es pública, historias.
- Facebook: reels y vídeos públicos.
- X/Twitter: vídeos incluidos en publicaciones.

Todos los vídeos se descargan como máximo a 720p para reducir el tamaño del archivo y acelerar el envío.

Usa `yt-dlp` y limita cada archivo a 49 MB para poder enviarlo por Telegram.

## Instalación en Linux

```bash
sudo apt install ffmpeg
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y pon el token creado por `@BotFather`. Después:

```bash
python bot.py
```

En Telegram envía `/start` y luego una URL compatible.

## Termux

Instala Python y ffmpeg con `pkg install python ffmpeg`, crea el entorno virtual e instala `requirements.txt` igual que en Linux. El script `termux.sh` automatiza esos pasos y arranca el bot. Si se corta la conexión o el polling termina, espera a que `api.telegram.org` vuelva a responder y reinicia el bot automáticamente. Para detenerlo, usa `Ctrl+C`.

## Cookies opcionales

Instagram, Facebook o X pueden exigir sesión aunque una publicación parezca visible. Exporta un archivo Netscape `cookies.txt` localmente y configura `COOKIES_FILE`; no lo subas al repositorio.

## Limitaciones

Las historias privadas, cuentas privadas y publicaciones protegidas no se pueden descargar sin una sesión autorizada. El bot no evita controles de acceso ni descarga contenido sin permiso. Las plataformas pueden cambiar sus endpoints y romper temporalmente `yt-dlp`, por lo que conviene mantenerlo actualizado.
