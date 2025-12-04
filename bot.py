import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import gspread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

print("STARTING BOT...")

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

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1


def find_row(query):
    if query.isdigit():
        return int(query)

    all_rows = sheet.get_all_values()
    for i, row in enumerate(all_rows, start=1):
        if len(row) >= 2:
            name = row[1]
            if query.lower() in name.lower():
                return i
    return None


def make_payment_text(payments):
    months = {
        "January": "января", "February": "февраля", "March": "марта",
        "April": "апреля", "May": "мая", "June": "июня",
        "July": "июля", "August": "августа", "September": "сентября",
        "October": "октября", "November": "ноября", "December": "декабря"
    }

    now = datetime.now()
    header = f"ЗП промы Саратов {now.day} {months[now.strftime('%B')]}:\n"

    lines = [header]

    for amount, name, phone, bank, receiver in payments:
        receiver_text = ""
        if receiver and receiver != "—":
            if receiver.lower().startswith("получатель"):
                receiver_text = f"({receiver})"
            else:
                receiver_text = f"(получатель {receiver})"

        lines.append(f"{amount}₽ {name} {phone} {bank} {receiver_text}")

    return "\n".join(lines)


async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) % 2 != 0:
        await update.message.reply_text("Указывать надо парами: ID/ФИО СУММА")
        return

    payments = []

    for i in range(0, len(args), 2):
        query = args[i]
        amount = args[i + 1]

        row_id = find_row(query)
        if not row_id:
            await update.message.reply_text(f"Не найдено: {query}")
            continue

        row = sheet.row_values(row_id)

        name = row[1]
        phone = row[2] if len(row) > 2 else ""
        bank = row[3] if len(row) > 3 else ""
        receiver = row[4] if len(row) > 4 else ""

        payments.append((amount, name, phone, bank, receiver))

    if not payments:
        await update.message.reply_text("Нет найденных данных.")
        return

    await update.message.reply_text(make_payment_text(payments))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот на webhooks.\n/pay ID/ФИО СУММА")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay", pay))

    # PTB 21.x – правильный запуск webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )


if __name__ == "__main__":
    main()
