import os
import asyncio
import json
import logging
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# === НАЛАШТУВАННЯ ЛОГІВ ===
# Це допоможе відстежувати помилки та роботу бота
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# === КОНСТАНТИ ===
TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "users.json"
app = Flask(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Kyiv") # Вказуємо часову зону


# --- Допоміжні функції ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def calculate_water(weight_kg: float) -> float:
    return round(weight_kg * 30 / 1000, 2)


# --- Обробники Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! 💧\nВкажи свій ріст і вагу у форматі: 175 70 (ріст см, вага кг)")

async def handle_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) != 2 or not all(p.replace('.', '', 1).isdigit() for p in parts):
        await update.message.reply_text("⚠️ Вкажи дані у форматі: 175 70")
        return
    height, weight = map(float, parts)
    water = calculate_water(weight)
    context.user_data['water'] = water
    context.user_data['reminder'] = False
    reply_markup = ReplyKeyboardMarkup([["Так"], ["Ні"]], resize_keyboard=True)
    await update.message.reply_text(f"Тобі потрібно пити близько {water} л води на день. 💦\nНагадувати про воду?", reply_markup=reply_markup)

async def handle_reminder_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    choice = update.message.text.lower()
    if choice == "так":
        # Зберігаємо дані користувача у файл
        users[user_id] = {
            "chat_id": update.effective_chat.id,
            "reminder": True,
            "water": context.user_data.get('water', 2.0)
        }
        save_users(users)
        await update.message.reply_text("Добре! Я буду нагадувати кожну годину 💧")
    elif choice == "ні":
        users[user_id] = {
            "chat_id": update.effective_chat.id,
            "reminder": False
        }
        save_users(users)
        await update.message.reply_text("Гаразд! Без нагадувань ☀️")


# --- Функція для нагадувань ---
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Ця функція буде викликатися планувальником для надсилання нагадувань."""
    logger.info("Запуск щогодинного нагадування...")
    users = load_users()
    if not users:
        return

    for user_id, data in users.items():
        if data.get("reminder"):
            chat_id = data["chat_id"]
            water_amount = data.get("water", 2.0)
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"💧 Нагадування! Не забудь випити води. Твоя норма на сьогодні: {water_amount} л."
                )
                logger.info(f"Нагадування надіслано користувачу {user_id}")
            except Exception as e:
                logger.error(f"Не вдалося надіслати повідомлення користувачу {user_id}: {e}")


# --- Обробник помилок ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логує помилки, що виникають в обробниках."""
    logger.error("Exception while handling an update:", exc_info=context.error)


# --- Flask-сервер для Render ---
@app.route('/')
def home():
    return "Бот працює!"


# --- Головна функція запуску ---
async def main() -> None:
    """Налаштування та запуск бота."""
    if not TOKEN:
        logger.error("Помилка: BOT_TOKEN не знайдено у змінних середовища!")
        return

    # Створення додатку
    application = Application.builder().token(TOKEN).build()

    # Додавання обробників
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^(Так|Ні)$"), handle_reminder_choice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data))
    
    # Додавання обробника помилок
    application.add_error_handler(error_handler)

    # Налаштування планувальника
    # Використовуємо CronTrigger для запуску на початку кожної години (напр. 13:00, 14:00)
    scheduler.add_job(
        send_reminder,
        CronTrigger(minute=0),  # Запускати кожну годину на 0-й хвилині
        id="hourly_reminder",
        name="Щогодинне нагадування про воду",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Планувальник запущено.")

    # Запуск бота
    # Ініціалізація, запуск поллінгу, а потім утримання програми активною
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True) # drop_pending_updates - добре для перезапусків
    
    logger.info("✅ Бот запущено!")
    
    # Цей рядок утримує програму працюючою, доки її не зупинять вручну
    await application.updater.idle()


if __name__ == "__main__":
    # Запускаємо Flask у фоновому потоці для Render
    from threading import Thread
    
    def run_flask():
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port)

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаємо основну асинхронну функцію бота
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
