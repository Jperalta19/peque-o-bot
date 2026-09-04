import asyncio
import logging
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import json
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
MAX_FILE_SIZE = 50 * 1024 * 1024
SUPPORTED_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "fb.watch",
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}
URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def is_supported_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower().rstrip(".") in SUPPORTED_HOSTS


def extract_supported_url(text: str) -> str | None:
    for candidate in URL_PATTERN.findall(text):
        clean_url = candidate.rstrip(".,!?)]}")
        if is_supported_url(clean_url):
            return clean_url
    return None


def download_reel(url: str, output_dir: str) -> tuple[Path, str]:
    output_template = str(Path(output_dir) / "reel.%(ext)s")
    options = {
        "outtmpl": output_template,
        "format": "best[ext=mp4][filesize<50M]/best[filesize<50M]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": MAX_FILE_SIZE,
        "quiet": True,
        "no_warnings": True,
        "retries": 2,
        "socket_timeout": DOWNLOAD_TIMEOUT,
    }

    cookies_file = os.getenv("COOKIES_FILE", "").strip()
    if cookies_file:
        options["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)

    downloaded_files = [path for path in Path(output_dir).glob("reel.*") if path.is_file()]
    if not downloaded_files:
        raise RuntimeError("No se encontró un archivo descargado.")

    file_path = downloaded_files[0]
    if file_path.stat().st_size > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        raise RuntimeError("El reel supera el límite de 50 MB de Telegram.")
    account_name = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or "Cuenta no identificada"
    )
    return file_path, str(account_name)


def explain_download_error(error: Exception) -> str:
    error_text = str(error).lower()
    if any(term in error_text for term in ("sign in", "login", "cookies", "authentication", "private")):
        return (
            "La plataforma requiere iniciar sesión o el contenido no es público. "
            "Configura COOKIES_FILE con cookies.txt de tu navegador."
        )
    if any(term in error_text for term in ("requested format", "format is not available")):
        return "No hay un formato compatible disponible para ese reel."
    if any(term in error_text for term in ("too large", "filesize", "50 mb")):
        return "El reel supera el límite de 50 MB de Telegram."
    return "No se pudo obtener el vídeo. Comprueba que el enlace sea público y válido."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.message.reply_text(
        "Envíame el enlace público de Instagram, Facebook o TikTok y lo descargaré.\n\n"
        "Usa /info para conocer el bot o /status para comprobar el servicio.\n"
        "Descarga únicamente contenido que tengas derecho a guardar."
    )


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.message.reply_text(
        "Bot descargador de vídeos públicos de Instagram, Facebook y TikTok.\n\n"
        "Envíame un enlace compatible y recibirás el vídeo con la cuenta detectada y el enlace "
        "de la publicación. El límite de envío es de 50 MB.\n\n"
        "Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/info - Ver este resumen\n"
        "/status - Consultar el estado del servicio"
    )


def read_battery_status() -> str:
    battery_command = "/data/data/com.termux/files/usr/bin/termux-battery-status"
    try:
        result = subprocess.run(
            [battery_command],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )
        battery = json.loads(result.stdout)
        percentage = battery.get("percentage")
        status = battery.get("status") or "desconocido"
        if percentage is None:
            return "No disponible"
        return f"{percentage}% ({status})"
    except (FileNotFoundError, json.JSONDecodeError, subprocess.SubprocessError, OSError):
        return "No disponible (instala Termux:API y ejecuta termux-battery-status en Termux)"


def check_internet() -> str:
    started_at = time.monotonic()
    try:
        request = urllib.request.Request("https://api.telegram.org", method="HEAD")
        with urllib.request.urlopen(request, timeout=8):
            elapsed = (time.monotonic() - started_at) * 1000
        return f"Conectada ({elapsed:.0f} ms)"
    except (OSError, urllib.error.URLError):
        return "Sin conexión"


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    battery, internet = await asyncio.gather(
        asyncio.to_thread(read_battery_status),
        asyncio.to_thread(check_internet),
    )
    await update.message.reply_text(
        "Estado del servicio\n\n"
        "Bot: Activo y respondiendo\n"
        f"Conexión a internet: {internet}\n"
        f"Batería de la tablet: {battery}"
    )


async def configure_commands(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Iniciar el bot"),
            BotCommand("info", "Resumen y descripción del bot"),
            BotCommand("status", "Estado, batería y conexión"),
        ]
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not update.message or not update.message.text:
        return

    url = extract_supported_url(update.message.text)
    if not url:
        await update.message.reply_text(
            "No detecté un enlace compatible. Envíame una URL pública de Instagram, Facebook o TikTok."
        )
        return

    status_message = await update.message.reply_text("Descargando el reel...")
    await update.message.chat.send_action(ChatAction.UPLOAD_VIDEO)

    try:
        with tempfile.TemporaryDirectory(prefix="telegram-reel-") as temp_dir:
            file_path, account_name = await asyncio.to_thread(download_reel, url, temp_dir)
            with file_path.open("rb") as video:
                await update.message.reply_video(
                    video=video,
                    caption=f"Cuenta: {account_name}\nPublicación: {url}",
                    supports_streaming=True,
                )
        await status_message.delete()
    except yt_dlp.utils.DownloadError as error:
        logger.warning("yt-dlp no pudo descargar %s: %s", url, error, exc_info=True)
        await status_message.edit_text(
            f"{explain_download_error(error)}\n\n"
            "Instagram, Facebook y TikTok pueden exigir cookies incluso para publicaciones "
            "visibles desde un navegador."
        )
    except TelegramError:
        logger.exception("Telegram no pudo recibir el vídeo de %s", url)
        await status_message.edit_text(
            "La descarga terminó, pero Telegram no pudo recibir el vídeo. "
            "Comprueba el tamaño del archivo y vuelve a intentarlo."
        )
    except Exception:
        logger.exception("Error inesperado procesando %s", url)
        await status_message.edit_text("Ocurrió un error inesperado. Revisa la consola del bot.")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Falta TELEGRAM_TOKEN. Cópialo en un archivo .env.")

    for proxy_variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(proxy_variable, None)

    telegram_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=30,
        httpx_kwargs={"trust_env": False},
    )
    polling_request = HTTPXRequest(
        connection_pool_size=2,
        connect_timeout=30,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=30,
        httpx_kwargs={"trust_env": False},
    )
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(telegram_request)
        .get_updates_request(polling_request)
        .post_init(configure_commands)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        bootstrap_retries=-1,
        timeout=30,
    )


if __name__ == "__main__":
    main()
