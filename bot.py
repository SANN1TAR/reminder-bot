# Бот для напоминаний в Telegram
# Вход: команды от пользователя (/add, /list, /del)
# Выход: сообщения в Telegram, напоминания каждый день в 9:00

import json
import os
from datetime import date, timedelta, datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

REMINDERS_FILE = os.path.join(os.path.dirname(__file__), "reminders.json")


def load():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save(reminders):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ну здарова. Записываю напоминалки.\n\n"
        "/add ДД.ММ текст — добавить\n"
        "/add ДД.ММ.ГГГГ текст — добавить с годом (посчитаю сколько лет)\n"
        "  Пример: /add 25.04.1990 Днюха у Васи\n\n"
        "/list — показать все\n"
        "/del N — удалить по номеру"
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Формат: /add ДД.ММ текст или /add ДД.ММ.ГГГГ текст\n"
            "Пример: /add 25.04.1990 Днюха у Васи"
        )
        return

    date_str = context.args[0]
    text = " ".join(context.args[1:])

    try:
        parts = date_str.split(".")
        if len(parts) == 2:
            day, month = int(parts[0]), int(parts[1])
            year = None
            datetime(2000, month, day)
        elif len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            datetime(year, month, day)
        else:
            raise ValueError
    except Exception:
        await update.message.reply_text("Дата кривая. Нужно ДД.ММ или ДД.ММ.ГГГГ, например 25.04.1990")
        return

    reminders = load()
    entry = {"date": f"{parts[0]}.{parts[1]}", "text": text}
    if year:
        entry["year"] = year
    reminders.append(entry)
    reminders.sort(key=lambda x: (int(x["date"].split(".")[1]), int(x["date"].split(".")[0])))
    save(reminders)

    if year:
        await update.message.reply_text(f"Записал: {date_str} — {text}")
    else:
        await update.message.reply_text(f"Записал: {date_str} — {text}")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = load()
    if not reminders:
        await update.message.reply_text("Пусто. Добавь что-нибудь через /add")
        return

    lines = [f"{i}. {r['date']} — {r['text']}" for i, r in enumerate(reminders, 1)]
    await update.message.reply_text("\n".join(lines))


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи номер: /удалить 2")
        return

    try:
        n = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Номер должен быть числом")
        return

    reminders = load()
    if n < 1 or n > len(reminders):
        await update.message.reply_text(f"Нет такого номера. Всего записей: {len(reminders)}")
        return

    removed = reminders.pop(n - 1)
    save(reminders)
    await update.message.reply_text(f"Удалил: {removed['date']} — {removed['text']}")


async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    today_str = today.strftime("%d.%m")
    tomorrow_str = tomorrow.strftime("%d.%m")

    reminders = load()
    for r in reminders:
        year = r.get("year")
        if r["date"] == today_str:
            if year:
                age = today.year - year
                msg = f"Сегодня: {r['text']}, исполняется {age} лет"
            else:
                msg = f"Сегодня: {r['text']}"
            await context.bot.send_message(chat_id=OWNER_ID, text=msg)
        elif r["date"] == tomorrow_str:
            if year:
                age = tomorrow.year - year
                msg = f"Завтра: {r['text']}, исполняется {age} лет"
            else:
                msg = f"Завтра: {r['text']}"
            await context.bot.send_message(chat_id=OWNER_ID, text=msg)


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("del", cmd_delete))

    # Проверка каждый день в 9:00
    app.job_queue.run_daily(
        daily_check,
        time=datetime.strptime("09:00", "%H:%M").time()
    )

    print("Бот запущен. Ctrl+C чтобы остановить.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
