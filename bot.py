import asyncio
from html import escape
import logging
import re
import sys

import httpx
from telegram import Bot, InputMediaDocument, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from constants import API_PREFIX
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


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(str(update.effective_chat.id))


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
        "/quando (или /когда) — отчёт по назначениям: когда получать новое назначение и следующее лекарство.\n\n"
        "/backup — скачать бэкап данных (файлы prescriptions и deleted).\n\n"
        "/chat_id — показать ID текущего чата.\n\n"
        "/help — это сообщение со списком команд."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def send_reminder() -> None:
    """Автономная отправка напоминания в группу CHAT_ID (вызов из крона)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(_api_url("/reminder/"))
        if r.status_code == 404:
            logger.info("reminder: нет напоминаний на сегодня")
            return
        r.raise_for_status()
        async with Bot(settings.BOT_TOKEN) as bot:
            await bot.send_message(
                chat_id=settings.CHAT_ID, text=r.text, parse_mode=ParseMode.HTML
            )
    except Exception as e:  # непредвиденная ошибка — в лог, наружу ничего
        logger.error("reminder failed: %s", e)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("hello", hello))
    application.add_handler(CommandHandler("chat_id", chat_id))
    application.add_handler(CommandHandler("quando", quando_command))
    application.add_handler(MessageHandler(filters.Regex(r"^/когда(?:@\w+)?(?:\s|$)"), quando_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reminder":
        asyncio.run(send_reminder())
    else:
        main()
