"""Optional WSGI entrypoint for webhook hosting; polling is recommended."""

import asyncio
import json
import os
from typing import Any, Callable

from telegram import Update
from telegram.ext import Application

from bot import handle_message, info, start


def build_application() -> Application:
    from telegram.ext import CommandHandler, MessageHandler, filters

    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Falta TELEGRAM_TOKEN")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application


async def process_update(payload: dict[str, Any]) -> None:
    application = build_application()
    await application.initialize()
    try:
        await application.process_update(Update.de_json(payload, application.bot))
    finally:
        await application.shutdown()


def app(environ: dict[str, Any], start_response: Callable[..., object]) -> list[bytes]:
    if environ.get("REQUEST_METHOD") != "POST":
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"Only POST is supported."]
    length = int(environ.get("CONTENT_LENGTH", "0"))
    payload = json.loads(environ["wsgi.input"].read(length))
    asyncio.run(process_update(payload))
    start_response("200 OK", [("Content-Type", "application/json")])
    return [b'{"ok":true}']
