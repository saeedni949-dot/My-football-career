import asyncio
import logging
import os
from pathlib import Path

from aiohttp import web
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# My Football Career V4.4
BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = os.getenv("GAME_URL", "https://my-football-career.fadehost.app")
GAME_SHORT_NAME = os.getenv("GAME_SHORT_NAME", "Myfootballcareer")
PORT = int(os.getenv("PORT", "8080"))
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger("MyFootballCareer")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send Telegram's game launch button."""
    message = update.effective_message
    if message is None:
        return
    try:
        await message.reply_game(game_short_name=GAME_SHORT_NAME)
    except Exception:
        logger.exception("Could not send the game launch button.")
        await message.reply_text(
            "فعلاً ارسال دکمه بازی ممکن نشد. چند لحظه دیگر دوباره /start را بزن."
        )


async def game_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Answer Telegram game callbacks quickly to avoid expired-query errors."""
    query = update.callback_query
    if query is None:
        return

    try:
        if getattr(query, "game_short_name", None) == GAME_SHORT_NAME:
            await query.answer(url=GAME_URL)
        else:
            await query.answer()
    except BadRequest as exc:
        message = str(exc).lower()
        if any(
            phrase in message
            for phrase in (
                "query is too old",
                "response timeout expired",
                "query id is invalid",
            )
        ):
            logger.warning(
                "Expired Telegram callback ignored; the user can tap the game again."
            )
            return
        logger.error("Telegram rejected callback: %s", exc)
    except Exception:
        logger.exception("Unexpected error while answering a game callback.")


async def health(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "ok",
            "service": "My Football Career",
            "version": "4.4.0",
        }
    )


async def home(request: web.Request) -> web.StreamResponse:
    if not INDEX_FILE.is_file():
        logger.error("Game file is missing: %s", INDEX_FILE)
        return web.Response(
            text="index.html not found. Upload the game HTML beside main.py.",
            status=500,
            content_type="text/plain",
        )
    return web.FileResponse(INDEX_FILE)


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", home)
    app.router.add_get("/index.html", home)
    app.router.add_get("/health", health)
    app.router.add_get("/healthz", health)

    runner = web.AppRunner(app, access_log=logger)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("Web server listening on port %s", PORT)
    return runner


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing. Set it in your hosting dashboard."
        )
    if not GAME_URL.startswith(("https://", "http://")):
        raise RuntimeError("GAME_URL must start with https:// or http://")
    if not GAME_SHORT_NAME:
        raise RuntimeError("GAME_SHORT_NAME cannot be empty.")

    runner = None
    bot_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    try:
        runner = await start_web_server()
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CallbackQueryHandler(game_callback))

        await bot_app.initialize()
        await bot_app.start()
        if bot_app.updater is None:
            raise RuntimeError("Telegram updater is unavailable.")

        await bot_app.updater.start_polling(drop_pending_updates=False)
        logger.info("My Football Career V4.4 bot started.")
        await asyncio.Event().wait()
    finally:
        if bot_app.updater is not None and bot_app.updater.running:
            await bot_app.updater.stop()
        if bot_app.running:
            await bot_app.stop()
        # shutdown is safe after initialize; if initialization itself failed,
        # avoid masking the original startup error.
        if getattr(bot_app, "initialized", False):
            await bot_app.shutdown()
        if runner is not None:
            await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by the host.")
