import os
import asyncio
import json
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,  # <-- ВАЖЛИВО: Цей імпорт має бути на місці!
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# === КОНСТАНТИ ===
TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "users.json"
app = Flask(__name__)
scheduler = AsyncIOScheduler()


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
    """Розрахунок потреби у воді: 30 мл на 1 кг ваги"""
    return round(weight_kg * 30 / 1000, 2)


# --- Обробники ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! 💧\nВкажи свій ріст і вагу у форматі: 175 70 (ріст см, вага кг)"
    )


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

    await update.message.reply_text(
        f"Тобі потрібно пити близько {water} л води на день. 💦\nНагадувати про воду?",
        reply_markup=reply_markup
    )


async def handle_reminder_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()

    choice = update.message.text.lower()
    if choice == "так":
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


# --- Flask endpoint (для Render) ---
@app.route('/')
def home():
    return "Бот працює!"


# --- Запуск ---
def main():
    """Головна функція для налаштування та запуску бота."""
    app_telegram = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    # Додавання обробників (handlers) у правильному порядку
    app_telegram.add_handler(CommandHandler("start", start))
    
    # 1. Обробник для кнопок "Так" / "Ні" (більш конкретний, тому він перший)
    app_telegram.add_handler(MessageHandler(filters.Regex("^(Так|Ні)$"), handle_reminder_choice))
    
    # 2. Обробник для всіх інших текстових повідомлень (більш загальний, тому він другий)
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data))

    scheduler.start()
    print("✅ Бот запущений")

    app_telegram.run_polling()


if __name__ == "__main__":
    main()
