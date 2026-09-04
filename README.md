# Bot de Telegram para reels

Bot pequeño en Python que recibe enlaces públicos de reels de Instagram y Facebook y devuelve el vídeo en Telegram.

Cada vídeo se envía con el nombre o identificador de la cuenta detectada y el enlace original de la publicación en el caption.

## Requisitos

- Python 3.10 o superior.
- Un token de bot creado con [@BotFather](https://t.me/BotFather).
- Acceso a internet.
- En Termux: `proot-distro` con Ubuntu instalado.

## Termux + Ubuntu

Coloca esta carpeta dentro del directorio HOME de Termux. En Termux instala Ubuntu y las herramientas necesarias:

```bash
pkg update
pkg install proot-distro
proot-distro install ubuntu
```

Arranca el bot desde Termux con:

```bash
cd "$HOME/pequeño bot"
chmod +x termux.sh
./termux.sh
```

El script entra en Ubuntu con `proot-distro login --termux-home`, se relanza dentro de la distro y allí instala Python, crea el entorno virtual, configura `.env` y ejecuta el bot. La primera ejecución puede tardar mientras Ubuntu instala Python y las dependencias.

La primera vez solicita el token de Telegram sin mostrarlo. Las siguientes veces reutiliza la configuración existente y actualiza `yt-dlp`, que debe mantenerse al día porque Instagram y Facebook cambian con frecuencia. Después abre tu bot en Telegram, pulsa `/start` y envíale un enlace.

## Notas

- Solo se aceptan dominios de Instagram y Facebook, y se procesa un enlace por mensaje.
- El archivo debe ser público y pesar menos de 50 MB, que es el límite práctico usado por este bot para enviarlo mediante Telegram.
- Algunas publicaciones requieren autenticación o no son compatibles con `yt-dlp`. Puedes indicar una ruta a un archivo de cookies con `COOKIES_FILE`, pero nunca compartas ese archivo ni lo subas al repositorio.
- Usa el bot únicamente con contenido que tengas permiso para descargar y conservar. Respeta los términos de servicio y los derechos de autor de cada plataforma.

## Comprobaciones locales

```bash
python -m py_compile bot.py
```
