from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from calculate import build_report

from settings import BOT_TOKEN


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("привет")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_report())


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(str(update.effective_chat.id))


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("hello", hello))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("chat_id", chat_id))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
