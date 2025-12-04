# Telegram bot — ready for Render

Этот репозиторий содержит подготовленный Telegram-бот (webhook) для развертывания на Render.com.

**Важно**: не добавляйте `service_account.json` в репозиторий. Загружайте его в Render Dashboard (Files).

## Файлы
- bot.py — код бота (использует webhook)
- requirements.txt — зависимости
- render.yaml — конфиг для Render
- .gitignore — исключения

## Быстрый старт (локально)
1. Установи зависимости: `pip install -r requirements.txt`
2. Создай `.env` со значениями:
   - BOT_TOKEN
   - WEBHOOK_URL
   - SPREADSHEET_ID
   - SERVICE_ACCOUNT_FILE (если локально — путь к файлу service_account.json)
3. Запусти: `python bot.py`

## Развёртывание на Render
1. Создай репозиторий на GitHub и залей файлы (НЕ загружай service_account.json).
2. На Render -> New -> Web Service -> подключи репозиторий; render.yaml автоматически настроит сервис.
3. В Dashboard -> Environment -> добавь переменные:
   - BOT_TOKEN
   - WEBHOOK_URL (пример: https://<имя-сервиса>.onrender.com)
   - SPREADSHEET_ID
   - SERVICE_ACCOUNT_FILE = service_account.json
4. Dashboard -> Files -> Upload -> загрузи service_account.json
5. Deploy

## Тестирование
После деплоя проверь логи в Render Dashboard — бот должен установить webhook и слушать порт.
