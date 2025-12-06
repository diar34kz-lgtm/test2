import logging
import os
from datetime import datetime, time
from dotenv import load_dotenv
import gspread
from pytz import timezone

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
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

# Внутренний список платежей на день
daily_payments = []

# Файл, куда сохраняем chat_id для ежедневной отправки
CHAT_FILE = "chat_id.txt"


def save_chat_id(chat_id):
    with open(CHAT_FILE, "w") as f:
        f.write(str(chat_id))


def get_chat_id():
    if not os.path.exists(CHAT_FILE):
        return None
    with open(CHAT_FILE, "r") as f:
        return int(f.read().strip())


# ---------------------- ПОИСК -----------------------
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


# ---------------------- /PAY ------------------------
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) % 2 != 0:
        await update.message.reply_text("Указывать надо парами: ID/ФИО СУММА")
        return

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

        daily_payments.append((amount, name, phone, bank, receiver))

    await update.message.reply_text("Добавлено в платежку!")


# ---------------------- /PAYMENT --------------------
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not daily_payments:
        await update.message.reply_text("Платежей сегодня нет.")
    else:
        await update.message.reply_text(make_payment_text(daily_payments))


# ------------ АВТО-ОТПРАВКА В 21:00 ПО МОСКВЕ --------
async def send_daily_payment(context: CallbackContext):
    chat_id = get_chat_id()
    if not chat_id:
        return

    if not daily_payments:
        return

    text = make_payment_text(daily_payments)
    await context.bot.send_message(chat_id=chat_id, text=text)

    daily_payments.clear()


# ---------------------- /SETCHAT ---------------------
async def setchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.message.chat_id
    save_chat_id(cid)
    await update.message.reply_text("Этот чат сохранён для ежедневной платежки.")


# ---------------------- /START ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот работает.\n"
        "/pay — добавить в платежку\n"
        "/payment — показать текущую платежку\n"
        "/setchat — выбрать чат для авто-отправки\n\n"
        "Добавление в таблицу работает автоматически."
    )


# --------------- РЕГИСТРАЦИЯ В ТАБЛИЦУ -----------------
async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.split("\n")
    data = {}

    for line in lines:
        if " " not in line:
            continue
        key, value = line.split(" ", 1)
        data[key.lower()] = value.strip()

    full_name = data.get("фио", "")
    phone = data.get("телефон", "")
    bank = data.get("банк", "")
    receiver = data.get("получатель", "—")

    if not full_name or not phone:
        await update.message.reply_text(
            "Ошибка: обязательно укажите:\nФИО ...\nТелефон ..."
        )
        return

    next_id = len(sheet.get_all_values()) + 1

    sheet.append_row([
        next_id,
        full_name,
        phone,
        bank,
        receiver
    ])

    await update.message.reply_text(f"Вы успешно добавлены!\nВаш ID: {next_id}")


# ------------------ ЗАПУСК BOT + WEBHOOK -------------------
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("payment", payment))
    app.add_handler(CommandHandler("setchat", setchat))

    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register_user))

    # JobQueue — ежедневная отправка в 21:00 по Москве
    moscow = timezone("Europe/Moscow")
    app.job_queue.run_daily(
        send_daily_payment,
        time=time(21, 0, tzinfo=moscow),
        name="daily_payment"
    )

    print("Running webhook server...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )


if __name__ == "__main__":
    main()
