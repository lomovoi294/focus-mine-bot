import telebot
import os
from telebot import types
from flask import Flask, request
from flask_cors import CORS

t = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(t)
app = Flask(__name__)
CORS(app) # Разрешаем запросы с других сайтов

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

@app.route('/claim')
def claim():
    user_id = request.args.get('user_id')
    seconds = request.args.get('seconds')
    if user_id and seconds:
        points = int(float(seconds))
        try:
            bot.send_message(user_id, f"✅ Успешно! Ты намайнил {points} SFP.")
        except Exception as e:
            print(f"Ошибка: {e}")
    return "OK", 200

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
