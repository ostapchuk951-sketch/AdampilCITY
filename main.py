import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
ApplicationBuilder,
CommandHandler,
MessageHandler,
filters,
ContextTypes,
)


TOKEN = os.getenv("BOT_TOKEN") # Токен з BotFather
app = Flask(__name__)


# --- Логіка розрахунку води ---
def calculate_water(weight_kg: float) -> float:
"""Розрахунок потреби у воді: 30 мл на 1 кг ваги"""
return round(weight_kg * 30 / 1000, 2) # у літрах


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


reply_markup = ReplyKeyboardMarkup([
["Так"], ["Ні"]
], resize_keyboard=True)


await update.message.reply_text(
f"Тобі потрібно пити близько {water} л води на день. 💦\nНагадувати про воду?",
reply_markup=reply_markup
)


async def handle_reminder_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
choice = update.message.text.lower()
if choice == "так":
context.user_data['reminder'] = True
await update.message.reply_text("Добре! Я буду нагадувати кожну годину 💧")
elif choice == "ні":
context.user_data['reminder'] = False
await update.message.reply_text("Гаразд! Без нагадувань ☀️")
else:
await update.message.reply_text("Вибери 'Так' або 'Ні'")


# --- Flask webhook ---
@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
update = Update.de_json(request.get_json(force=True), bot.application.bot)
bot.application.update_queue.put(update)
return "OK", 200


@app.route('/')
def index():
return "Bot is running!"


# --- Головний запуск ---
if __name__ == '__main__':
from telegram.ext import Application


bot = Application.builder().token(TOKEN).build()


bot.add_handler(CommandHandler('start', start))
bot.add_handler(MessageHandler(filters.Regex(r'^\d+\s+\d+$'), handle_data))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_choice))


port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
