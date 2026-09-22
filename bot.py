"""Telegram bot for downloading public media from Instagram, Facebook and X."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
MAX_FILE_SIZE = 45 * 1024 * 1024
MAX_VIDEO_HEIGHT = 720
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
SUPPORTED_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "fb.watch",
    "m.facebook.com",
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
}


def is_supported_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in SUPPORTED_HOSTS


def extract_supported_url(text: str) -> str | None:
    for candidate in URL_PATTERN.findall(text):
        candidate = candidate.rstrip(".,!?)]}>")
        if is_supported_url(candidate):
            return candidate
    return None


def media_kind(url: str) -> str:
    path = urlparse(url).path.lower()
    if "story" in path:
        return "historia"
    if "reel" in path or "/reels" in path:
        return "reel"
    if "facebook.com" in url and ("watch" in path or "/videos" in path):
        return "video de Facebook"
    if "x.com" in url or "twitter.com" in url:
        return "video de X"
    return "publicación"


def _size(format_info: dict, duration: float | None) -> int | None:
    value = format_info.get("filesize") or format_info.get("filesize_approx")
    if value:
        return int(value)
    bitrate = format_info.get("tbr")
    if bitrate and duration:
        return int(float(bitrate) * 1000 * duration / 8 * 1.15)
    return None


def select_format(info: dict, max_height: int | None = MAX_VIDEO_HEIGHT) -> tuple[str, int, int]:
    """Choose the best known video format that Telegram can receive."""
    duration = info.get("duration")
    formats = info.get("formats") or []
    has_ffmpeg = shutil.which("ffmpeg") is not None
    audio_only = [
        item for item in formats
        if item.get("vcodec") in {None, "none"} and item.get("acodec") not in {None, "none"}
    ]
    best_audio = max(audio_only, key=lambda item: item.get("abr") or item.get("tbr") or 0, default=None)
    audio_size = _size(best_audio, duration) if best_audio else None
    candidates: list[tuple[str, int, int, float]] = []

    for item in formats:
        if item.get("vcodec") in {None, "none"}:
            continue
        if max_height is not None and (item.get("height") or 0) > max_height:
            continue
        video_size = _size(item, duration)
        if video_size is None:
            continue
        if item.get("acodec") not in {None, "none"}:
            expression, total_size = str(item["format_id"]), video_size
        elif has_ffmpeg and best_audio and audio_size is not None:
            expression = f"{item['format_id']}+{best_audio['format_id']}"
            total_size = video_size + audio_size
        else:
            expression, total_size = str(item["format_id"]), video_size
        if total_size <= MAX_FILE_SIZE:
            candidates.append((expression, total_size, item.get("height") or 0, item.get("tbr") or 0))

    if not candidates:
        raise RuntimeError("No hay un formato conocido que quepa por debajo de 45 MB.")
    selected = max(candidates, key=lambda item: (item[2], item[3]))
    return selected[0], selected[2], selected[1]


def _cookie_options() -> dict:
    configured = os.getenv("COOKIES_FILE", "").strip()
    if not configured:
        return {}
    cookie_path = Path(configured).expanduser()
    if not cookie_path.is_absolute():
        cookie_path = Path(__file__).resolve().parent / cookie_path
    if not cookie_path.is_file():
        raise FileNotFoundError(f"No existe COOKIES_FILE: {cookie_path}")
    return {"cookiefile": str(cookie_path)}


def download_media(url: str, output_dir: str) -> tuple[Path, str, int, int]:
    output_template = str(Path(output_dir) / "media.%(ext)s")
    common = {"quiet": True, "no_warnings": True, "noplaylist": True, **_cookie_options()}
    with yt_dlp.YoutubeDL(common) as analyzer:
        info = analyzer.extract_info(url, download=False)
        format_expression, height, estimated_size = select_format(info)

    options = {
        **common,
        "outtmpl": output_template,
        "format": format_expression,
        "max_filesize": MAX_FILE_SIZE,
        "retries": 2,
        "socket_timeout": DOWNLOAD_TIMEOUT,
        "restrictfilenames": True,
    }
    if shutil.which("ffmpeg"):
        options["merge_output_format"] = "mp4"
    with yt_dlp.YoutubeDL(options) as downloader:
        downloaded = downloader.extract_info(url, download=True)

    files = [path for path in Path(output_dir).glob("media.*") if path.is_file()]
    if not files:
        raise RuntimeError("La plataforma no devolvió ningún archivo multimedia.")
    file_path = files[0]
    if file_path.stat().st_size > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        raise RuntimeError("El archivo supera el límite seguro de 45 MB de Telegram.")
    account = downloaded.get("uploader_id") or downloaded.get("uploader") or downloaded.get("channel") or "cuenta desconocida"
    return file_path, str(account), height, estimated_size or file_path.stat().st_size


def friendly_error(error: Exception) -> str:
    text = str(error).lower()
    if any(word in text for word in ("login", "sign in", "authentication", "private", "cookies")):
        return "Ese contenido requiere iniciar sesión o es privado. Configura COOKIES_FILE con un cookies.txt local."
    if "49 mb" in text or "filesize" in text or "too large" in text:
        return "El vídeo supera el límite de 49 MB de Telegram."
    if "ffmpeg" in text or "merge" in text:
        return "Falta ffmpeg para unir vídeo y audio. Instálalo con `apt install ffmpeg`."
    return "No se pudo descargar. Comprueba que el enlace siga siendo público y válido."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.message.reply_text(
        "Envíame un enlace público de Instagram, Facebook o X.\n\n"
        "Admito reels, publicaciones, vídeos y, cuando la plataforma lo permita, historias.\n"
        "Usa /info para ver detalles. Descarga solo contenido que tengas derecho a conservar."
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.message.reply_text(
        "Descargador multimedia\n\n"
        "Instagram: reels, publicaciones y URLs de historias públicas.\n"
        "Facebook: reels y vídeos públicos.\n"
        "X: vídeos incluidos en publicaciones.\n\n"
        "Límite: 49 MB por archivo. Algunas URLs requieren COOKIES_FILE."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not update.message or not update.message.text:
        return
    url = extract_supported_url(update.message.text)
    if not url:
        await update.message.reply_text("No detecté una URL compatible de Instagram, Facebook o X.")
        return

    kind = media_kind(url)
    status = await update.message.reply_text(f"Descargando {kind}... Esto puede tardar un momento.")
    try:
        with tempfile.TemporaryDirectory(prefix="telegram-media-") as temp_dir:
            path, account, height, estimated = await asyncio.to_thread(download_media, url, temp_dir)
            with path.open("rb") as media:
                await update.message.reply_video(
                    video=media,
                    caption=f"{kind.title()} de {account}\nCalidad: {height}p\n{url}",
                    supports_streaming=True,
                )
        await status.delete()
    except (RuntimeError, FileNotFoundError, yt_dlp.utils.DownloadError) as error:
        logger.warning("No se pudo descargar %s: %s", url, error)
        await status.edit_text(friendly_error(error))
    except Exception:
        logger.exception("Error procesando %s", url)
        await status.edit_text("Ocurrió un error inesperado. Revisa los logs del bot.")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Falta TELEGRAM_TOKEN. Configúralo en .env.")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES, bootstrap_retries=-1)


if __name__ == "__main__":
    main()
