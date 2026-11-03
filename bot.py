import telebot
import os
from telebot import types
from flask import Flask, request
import json

t = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(t)
app = Flask(__name__)

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

@bot.message_handler(content_types=['web_app_data'])
def web_app(web_app_message):
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
        print(f"Ошибка: {e}")

@app.route('/' + t, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f'https://focus-mine-bot.onrender.com/{t}')
    return "Webhook установлен!", 200

if name == "main":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
