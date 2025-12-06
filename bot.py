import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import gspread

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ----------------------- ЛОГИ -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

print("STARTING BOT...")

# --------------------- ЗАГРУЗКА .env ----------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")
PORT = int(os.getenv("PORT", "8000"))

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN is required")
if not WEBHOOK_URL:
    raise SystemExit("WEBHOOK_URL is required")
if not SPREADSHEET_ID:
    raise SystemExit("SPREADSHEET_ID is required")

# --------------------- GOOGLE SHEETS ----------------
gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# ---------------------- /START ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправьте данные в формате:\n\n"
        "ФИО Иванов Петр\n"
        "Телефон 89112223344\n"
        "Банк Тинькофф\n"
        "Получатель Иванова Ирина\n"
    )

# --------------- ОБРАБОТКА ДОБАВЛЕНИЯ В ТАБЛИЦУ -----------------
async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.split("\n")
    data = {}

    # Разбираем строки формата "Ключ значение"
    for line in lines:
        if " " not in line:
            continue
        key, value = line.split(" ", 1)
        data[key.lower()] = value.strip()

    # Извлекаем
    full_name = data.get("фио", "")
    phone = data.get("телефон", "")
    bank = data.get("банк", "")
    receiver = data.get("получатель", "—")

    # Проверка обязательных полей
    if not full_name or not phone:
        await update.message.reply_text(
            "Ошибка: обязательно укажите:\n"
            "ФИО ...\n"
            "Телефон ..."
        )
        return

    # ID = следующая строка
    next_id = len(sheet.get_all_values()) + 1

    # Запись в таблицу (строгая структура)
    sheet.append_row([
        next_id,
        full_name,
        phone,
        bank,
        receiver
    ])

    # Ответ
    await update.message.reply_text(f"Вы успешно добавлены!\nВаш ID: {next_id}")

# ------------------ ЗАПУСК BOT + WEBHOOK -------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register_user))

    print("Running webhook server...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )


if __name__ == "__main__":
    main()
