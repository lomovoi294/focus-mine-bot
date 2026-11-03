import telebot
import os
import sqlite3
from telebot import types
from flask import Flask, request
from flask_cors import CORS

t = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(t)
app = Flask(__name__)
CORS(app)

# --- База данных ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Таблица пользователей: ID, баланс, реферер
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER)''')
    conn.commit()
    conn.close()

# init_db()

def add_user(user_id, referrer_id=None):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not c.fetchone():
        c.execute('INSERT INTO users (user_id, balance, referrer_id) VALUES (?, ?, ?)', (user_id, 0, referrer_id))
        conn.commit()
    conn.close()

def update_balance(user_id, points):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (points, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0

# --- Команды бота ---
@bot.message_handler(commands=['start'])
def start(m):
    # Обработка реферальной ссылки
    args = m.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id == m.from_user.id:
                referrer_id = None # Защита от самого себя
        except ValueError:
            pass

    add_user(m.from_user.id, referrer_id)

    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url="https://lomovoi294.github.io/focus-mine-bot/")
    btn = types.InlineKeyboardButton("Шахта 🟢", web_app=web_app)
    markup.add(btn)
    
    balance = get_balance(m.from_user.id)
    bot.send_message(m.chat.id, f"Привет! Это FocusMine.\nТвой баланс: {balance:.1f} SFP", reply_markup=markup)

@bot.message_handler(commands=['invite'])
def invite(m):
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Твоя ссылка: {link}")

# --- Прием данных от сайта ---
@app.route('/claim')
def claim():
    user_id = request.args.get('user_id')
    seconds = request.args.get('seconds')
    
    if user_id and seconds:
        try:
            user_id = int(user_id)
            points = int(float(seconds))
            
            # Начисляем баланс
            update_balance(user_id, points)
            new_balance = get_balance(user_id)
            
            # Отправляем сообщение
            bot.send_message(user_id, f"✅ Успешно! Ты намайнил {points} SFP.\nТвой новый баланс: {new_balance:.1f} SFP")
            
        except Exception as e:
            print(f"Ошибка начисления: {e}")
            
    return "OK", 200

# --- Webhook для команд ---
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
