from html import escape
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from calculate import build_report, build_input_report, build_today_report, set_pickup_date
from parsers import parse_date, parse_drugs
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


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # context.args разбивает по пробелам и теряет переводы строк, берём сырой текст
    body = re.sub(r"^/new(@\w+)?", "", update.message.text or "", count=1).strip()

    if not body:
        await update.message.reply_text(
            "Нужно прислать данные в том же сообщении, после команды, по одному препарату на строку. Например:\n\n"
            "/new\n"
            "Левотироксин натрия, 200, 1\n"
            "Гидрокортизон, 200, 2\n"
            "Десмопрессин, 180, 2"
        )
        return

    drugs, errors = parse_drugs(body)
    if errors:
        msg = "<b>Данные не сохранены.</b> Ошибки:\n\n" + "\n".join(
            f"- {escape(e)}" for e in errors
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    await update.message.reply_text(build_input_report(drugs), parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Доступные команды:</b>\n\n"
        "/hello — поздороваться.\n\n"
        "/today — отчёт на сегодня: сколько таблеток осталось до следующего назначения.\n\n"
        "/report — полный отчёт по всем препаратам с датой ближайшего следующего назначения.\n\n"
        "/date — установить дату получения препаратов. Например:\n"
        "<code>/date 26.10.2026</code>, <code>/date 1 окт</code>, <code>/date 01 октября 2026</code>\n\n"
        "/new — добавить препараты. Данные присылаются в том же сообщении после команды, "
        "по одному препарату на строку в формате «название, количество, приёмов в день». Например:\n"
        "<code>/new\n"
        "Левотироксин натрия, 200, 1\n"
        "Гидрокортизон, 200, 2\n"
        "Десмопрессин, 180, 2</code>\n\n"
        "/chat_id — показать ID текущего чата.\n\n"
        "/help — это сообщение со списком команд."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("hello", hello))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("chat_id", chat_id))
    application.add_handler(CommandHandler("date", date_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
