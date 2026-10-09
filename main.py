
import os
import asyncio
import logging
from pathlib import Path

from aiohttp import web
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# تنظیمات
BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = "https://my-football-career.fadehost.app"
GAME_SHORT_NAME = "Myfootballcareer"
PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("MyFootballCareer")

# کاهش لاگ‌های غیرضروری کتابخانه‌ها
logging.getLogger("httpx").setLevel(logging.WARNING)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال دکمه ورود به بازی."""
    if update.effective_message:
        await update.effective_message.reply_game(
            game_short_name=GAME_SHORT_NAME
        )


async def game_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """پاسخ سریع به درخواست ورود به بازی."""
    query = update.callback_query

    if query is None:
        return

    try:
        if query.game_short_name == GAME_SHORT_NAME:
            await query.answer(url=GAME_URL)
        else:
            await query.answer()

    except BadRequest as exc:
        message = str(exc).lower()

        if (
            "query is too old" in message
            or "response timeout expired" in message
            or "query id is invalid" in message
        ):
            # درخواست منقضی شده؛ دیگر قابل پاسخ‌دادن نیست.
            logger.warning(
                "Expired Telegram callback ignored. "
                "The user may need to tap again."
            )
            return

        logger.error("Telegram rejected callback: %s", exc)

    except Exception:
        logger.exception("Unexpected error in game callback")


async def health(request: web.Request):
    return web.Response(
        text="My Football Career is running! ⚽",
        content_type="text/plain",
    )


async def home(request: web.Request):
    index_file = BASE_DIR / "index.html"

    if not index_file.is_file():
        return web.Response(
            text="index.html not found",
            status=500,
        )

    return web.FileResponse(index_file)


async def start_web_server():
    """اجرای سایت بازی روی پورت هاست."""
    web_app = web.Application()
    web_app.router.add_get("/", home)
    web_app.router.add_get("/health", health)

    runner = web.AppRunner(web_app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT,
    )
    await site.start()

    logger.info("Web server started on port %s", PORT)
    return runner


async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    # سرور بازی و بات در یک اپ اجرا می‌شوند.
    runner = await start_web_server()

    bot_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(game_callback))

    try:
        await bot_app.initialize()
        await bot_app.start()

        if bot_app.updater is None:
            raise RuntimeError("Telegram updater is unavailable.")

        await bot_app.updater.start_polling(
            drop_pending_updates=False,
        )

        logger.info("My Football Career bot started successfully.")

        # زنده نگه‌داشتن فرایند
        await asyncio.Event().wait()

    finally:
        if bot_app.updater and bot_app.updater.running:
            await bot_app.updater.stop()

        if bot_app.running:
            await bot_app.stop()

        await bot_app.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
