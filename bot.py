from html import escape
import logging
import re

import httpx
from telegram import InputMediaDocument, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from calculate import build_report, build_input_report, build_today_report, set_pickup_date
from constants import API_PREFIX
from parsers import parse_date, parse_drugs
import settings
from settings import BOT_TOKEN

logger = logging.getLogger(__name__)

_CD_RE = re.compile(r'filename="?([^";]+)"?')


def _api_url(path: str) -> str:
    return settings.API_URL.rstrip("/") + API_PREFIX + path


def _filename(header: str | None, fallback: str) -> str:
    if header and (m := _CD_RE.search(header)):
        return m.group(1)
    return fallback


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


async def quando_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(_api_url("/quando/"))
    except httpx.HTTPError as e:
        logger.error("quando request failed: %s", e)
        await update.message.reply_text("Сервер недоступен. Попробуйте позже.")
        return
    if r.status_code != 200:
        await update.message.reply_text(f"Не удалось получить отчёт (HTTP {r.status_code}).")
        return
    await update.message.reply_text(r.text, parse_mode=ParseMode.HTML)


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    endpoints = [("/prescriptions/backup/", "prescriptions"),
                 ("/prescriptions/backup-deleted/", "deleted")]
    files: list[tuple[str, bytes]] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            for path, kind in endpoints:
                r = await client.get(_api_url(path))
                if r.status_code == 200:
                    name = _filename(r.headers.get("content-disposition"), f"{kind}.jsonl")
                    files.append((name, r.content))
                elif r.status_code == 404:
                    continue
                else:
                    await update.message.reply_text(f"Ошибка бэкапа ({kind}): HTTP {r.status_code}.")
                    return
    except httpx.HTTPError as e:
        logger.error("backup request failed: %s", e)
        await update.message.reply_text("Сервер недоступен. Попробуйте позже.")
        return

    if not files:
        await update.message.reply_text(
            "Бэкап данных: файлов пока нет (ещё не было ни одного назначения или удаления)."
        )
    elif len(files) == 1:
        name, data = files[0]
        await update.message.reply_document(document=data, filename=name, caption="Бэкап данных")
    else:
        media = [
            InputMediaDocument(media=data, filename=name,
                               caption="Бэкап данных" if i == 0 else None)
            for i, (name, data) in enumerate(files)
        ]
        await update.message.reply_media_group(media=media)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Доступные команды:</b>\n\n"
        "/hello — поздороваться.\n\n"
        "/today — отчёт на сегодня: сколько таблеток осталось до следующего назначения.\n\n"
        "/report — полный отчёт по всем препаратам с датой ближайшего следующего назначения.\n\n"
        "/quando (или /когда) — отчёт по назначениям: когда получать новое назначение и следующее лекарство.\n\n"
        "/date — установить дату получения препаратов. Например:\n"
        "<code>/date 26.10.2026</code>, <code>/date 1 окт</code>, <code>/date 01 октября 2026</code>\n\n"
        "/new — добавить препараты. Данные присылаются в том же сообщении после команды, "
        "по одному препарату на строку в формате «название, количество, приёмов в день». Например:\n"
        "<code>/new\n"
        "Левотироксин натрия, 200, 1\n"
        "Гидрокортизон, 200, 2\n"
        "Десмопрессин, 180, 2</code>\n\n"
        "/backup — скачать бэкап данных (файлы prescriptions и deleted).\n\n"
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
    application.add_handler(CommandHandler("quando", quando_command))
    application.add_handler(MessageHandler(filters.Regex(r"^/когда(?:@\w+)?(?:\s|$)"), quando_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
