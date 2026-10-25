from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from calculate import build_report, build_today_report, set_pickup_date
from parsers import parse_date
from settings import BOT_TOKEN


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("привет")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_report(), parse_mode=ParseMode.HTML)


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(str(update.effective_chat.id))


async def date_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    arg = " ".join(context.args).strip()
    if not arg:
        await update.message.reply_text(
            "Укажите дату. Например: /date 26.10.2026, /date 1 окт, /date 01 октября 2026"
        )
        return

    try:
        new_date = parse_date(arg)
    except ValueError as e:
        await update.message.reply_text(f"Проблема: {e}. Пример правильной даты: /date 26.10.2026")
        return

    set_pickup_date(new_date)
    await update.message.reply_text(f"Дата получения: {new_date:%d.%m.%Y}")


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_today_report(), parse_mode=ParseMode.HTML)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("hello", hello))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("chat_id", chat_id))
    application.add_handler(CommandHandler("date", date_command))
    application.add_handler(CommandHandler("today", today_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
