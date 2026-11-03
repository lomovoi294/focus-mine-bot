import telebot
import os
from telebot import types
from flask import Flask, request
from flask_cors import CORS
import libsql

t = os.environ.get('BOT_TOKEN')
turso_url = os.environ.get('TURSO_URL')
turso_token = os.environ.get('TURSO_TOKEN')

bot = telebot.TeleBot(t, threaded=False)
app = Flask(__name__)
CORS(app)

def get_conn():
    return libsql.connect(turso_url, auth_token=turso_token)

def init_db():
    conn = get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER, is_banned INTEGER DEFAULT 0)")
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except:
        pass
    conn.commit()
    conn.close()

def is_user_banned(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT is_banned FROM users WHERE user_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def ban_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", [user_id])
    conn.commit()
    conn.close()

def add_user(user_id, referrer_id=None):
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", [user_id])
    if not cursor.fetchone():
        conn.execute("INSERT INTO users (user_id, balance, referrer_id, is_banned) VALUES (?, ?, ?, 0)", [user_id, 0, referrer_id])
        conn.commit()
    conn.close()

def update_balance(user_id, points):
    conn = get_conn()
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", [points, user_id])
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT balance FROM users WHERE user_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

init_db()

@bot.message_handler(commands=['start'])
def start(m):
    if is_user_banned(m.from_user.id):
        bot.send_message(m.chat.id, "⛔ Твой аккаунт заблокирован за попытку накрутки. Доступ закрыт.")
        return

    args = m.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id == m.from_user.id: referrer_id = None
        except ValueError: pass

    add_user(m.from_user.id, referrer_id)
    
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url="https://lomovoi294.github.io/focus-mine-bot/")
    btn = types.InlineKeyboardButton("Шахта 🟢", web_app=web_app)
    markup.add(btn)
    
    balance = get_balance(m.from_user.id)
    bot.send_message(m.chat.id, f"Привет! Это FocusMine.\nТвой баланс: {balance:.1f} SFP", reply_markup=markup)

@bot.message_handler(commands=['invite'])
def invite(m):
    if is_user_banned(m.from_user.id): return
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Твоя ссылка: {link}")

@app.route('/claim')
def claim():
    user_id = request.args.get('user_id')
    seconds = request.args.get('seconds')
    
    if user_id and seconds:
        try:
            user_id = int(user_id)
            points = int(float(seconds))
            
            if is_user_banned(user_id):
                return "OK", 200

            if points > 0 and points <= 60:
                update_balance(user_id, points)
                new_balance = get_balance(user_id)
                bot.send_message(user_id, f"✅ Успешно! Ты намайнил {points} SFP.\nТвой новый баланс: {new_balance:.1f} SFP")
            else:
                ban_user(user_id)
                print(f"🚫 Пользователь {user_id} забанен за накрутку ({points} сек).")
                try:
                    bot.send_message(user_id, "⛔ Ты заблокирован за попытку взлома системы.")
                except:
                    pass
                
        except Exception as e:
            print(f"Ошибка: {e}")
            
    return "OK", 200
  @app.route('/' + t, methods=['POST'])def getMessage():
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
