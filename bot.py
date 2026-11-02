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
@bot.message_handler(content_types=['web_app_data'])
def web_app(web_app_message):
    import json
    try:
        data = json.loads(web_app_message.web_app_data.data)
        if data.get("action") == "claim":
            seconds = float(data.get("seconds", 0))
            points = int(seconds)
            bot.send_message(
                web_app_message.chat.id, 
                f"✅ Успешно! Ты намайнил {points} SFP."
            )
    except Exception as e:
        bot.send_message(web_app_message.chat.id, "Ошибка при обработке данных.")
if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
