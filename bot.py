import telebot
import os
from telebot import types
from flask import Flask, request
from flask_cors import CORS
import libsql_client
import asyncio

t = os.environ.get('BOT_TOKEN')
turso_url = os.environ.get('TURSO_URL')
turso_token = os.environ.get('TURSO_TOKEN')

bot = telebot.TeleBot(t, threaded=False)
app = Flask(__name__)
CORS(app)

# --- Функции для работы с Turso ---
async def get_db_connection():
    return libsql_client.create_client(url=turso_url, auth_token=turso_token)

async def init_db():
    async with await get_db_connection() as client:
        await client.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER)")

async def add_user(user_id, referrer_id=None):
    async with await get_db_connection() as client:
        res = await client.execute("SELECT * FROM users WHERE user_id = ?", [user_id])
        if not res.rows:
            await client.execute("INSERT INTO users (user_id, balance, referrer_id) VALUES (?, ?, ?)", [user_id, 0, referrer_id])

async def update_balance(user_id, points):
    async with await get_db_connection() as client:
        await client.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", [points, user_id])

async def get_balance(user_id):
    async with await get_db_connection() as client:
        res = await client.execute("SELECT balance FROM users WHERE user_id = ?", [user_id])
        if res.rows:
            return res.rows[0][0]
        return 0

# Запускаем инициализацию базы при старте
asyncio.run(init_db())

# --- Команды бота ---
@bot.message_handler(commands=['start'])
def start(m):
    args = m.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id == m.from_user.id:
                referrer_id = None
        except ValueError:
            pass

    asyncio.run(add_user(m.from_user.id, referrer_id))

    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url="https://lomovoi294.github.io/focus-mine-bot/")
    btn = types.InlineKeyboardButton("Шахта 🟢", web_app=web_app)
    markup.add(btn)
    
    balance = asyncio.run(get_balance(m.from_user.id))
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
            
            asyncio.run(update_balance(user_id, points))
            new_balance = asyncio.run(get_balance(user_id))
            
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

app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
