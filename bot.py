import telebot
import os
from telebot import types

t = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(t)

@bot.message_handler(commands=['start'])
def start(m):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Шахта 🟢", url="https://google.com")
    markup.add(btn)
    bot.send_message(m.chat.id, "Привет! Это FocusMine.", reply_markup=markup)

@bot.message_handler(commands=['invite'])
def invite(m):
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Твоя ссылка: {link}")

bot.infinity_polling()