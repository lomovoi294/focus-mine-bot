import telebot
import os
from telebot import types

t = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(t)

@bot.message_handler(commands=['start'])
def start(m):
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(ur1="https://lomovoi294.github.io/focus-mine-bot/")
    btn = types.InlineKeyboardButton("Шахта 🟢", web_app=web_app)
    markup.add(btn)
    bot.send_message(m.chat.id, "Привет! Это FocusMine.", reply_markup=markup)

@bot.message_handler(commands=['invite'])
def invite(m):
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Твоя ссылка: {link}")

bot.infinity_polling()
