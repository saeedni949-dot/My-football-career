import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = "https://my-football-career.fadehost.app"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_game(
        game_short_name="Myfootballcareer"
    )


async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.game_short_name == "Myfootballcareer":
        await query.answer(
            url=GAME_URL
        )
    else:
        await query.answer()


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(game_callback))

    print("My Football Career bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
