import os
import asyncio
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = "https://my-football-career.fadehost.app"

PORT = int(os.getenv("PORT", "8080"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_game(
        game_short_name="Myfootballcareer"
    )


async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.game_short_name == "Myfootballcareer":
        await query.answer(url=GAME_URL)
    else:
        await query.answer()


async def health(request):
    return web.Response(text="My Football Career is running! ⚽")


async def start_web_server():
    app = web.Application()

    # صفحه اصلی بازی
    app.router.add_get("/", lambda request: web.FileResponse("index.html"))

    # تست سلامت
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print(f"Web server running on port {PORT}")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    bot_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    bot_app.add_handler(
        CommandHandler("start", start)
    )

    bot_app.add_handler(
        CallbackQueryHandler(game_callback)
    )

    await bot_app.initialize()
    await bot_app.start()

    await bot_app.updater.start_polling()

    await start_web_server()

    print("My Football Career bot is running...")

    # برنامه را زنده نگه می‌دارد
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
