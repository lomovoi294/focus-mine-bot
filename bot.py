import telebot
import os
from telebot import types
from flask import Flask
import threading

# --- Настройка бота ---
t = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(t)

@bot.message_handler(commands=['start'])
def start(m):
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url="https://lomovoi294.github.io/focus-mine-bot/")
    btn = types.InlineKeyboardButton("Шахта 🟢", web_app=web_app)
    markup.add(btn)
    bot.send_message(m.chat.id, "Привет! Это FocusMine.", reply_markup=markup)

@bot.message_handler(commands=['invite'])
def invite(m):
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Твоя ссылка: {link}")

# --- Запуск бота в фоне ---
def run_bot():
    bot.infinity_polling()

# --- Мини-сервер для Render ---
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running"

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
