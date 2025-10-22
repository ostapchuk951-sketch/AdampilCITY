import os
import asyncio
import json
import logging
from datetime import datetime
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# === ЛОГИ ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# === КОНСТАНТИ ===
TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "users.json"
app = Flask(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")

# --- Допоміжні функції ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def calculate_water(weight_kg: float) -> float:
    return round(weight_kg * 30 / 1000, 2)

# --- Telegram обробники ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! 💧\nВкажи свій ріст і вагу у форматі: 175 70 (ріст см, вага кг)"
    )

async def handle_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) != 2 or not all(p.replace(".", "", 1).isdigit() for p in parts):
        await update.message.reply_text("⚠️ Вкажи дані у форматі: 175 70")
        return
    height, weight = map(float, parts)
    water = calculate_water(weight)
    context.user_data["water"] = water
    context.user_data["reminder"] = False
    reply_markup = ReplyKeyboardMarkup([["Так"], ["Ні"]], resize_keyboard=True)
    await update.message.reply_text(
        f"Тобі потрібно пити близько {water} л води на день. 💦\nНагадувати про воду?",
        reply_markup=reply_markup,
    )

async def handle_reminder_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    choice = update.message.text.lower()
    if choice == "так":
        users[user_id] = {
            "chat_id": update.effective_chat.id,
            "reminder": True,
            "water": context.user_data.get("water", 2.0),
        }
        save_users(users)
        await update.message.reply_text("Добре! Я буду нагадувати кожну годину 💧")
    elif choice == "ні":
        users[user_id] = {
            "chat_id": update.effective_chat.id,
            "reminder": False,
        }
        save_users(users)
        await update.message.reply_text("Гаразд! Без нагадувань ☀️")

# --- Нагадування ---
async def send_reminder(application: Application):_
