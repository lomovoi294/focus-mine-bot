import telebot
import os
import time
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
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER, is_banned INTEGER DEFAULT 0, last_daily INTEGER DEFAULT 0, boost_end_time INTEGER DEFAULT 0)")
    # Безопасно добавляем колонки, если база старая
    try: conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN last_daily INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN boost_end_time INTEGER DEFAULT 0")
    except: pass
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
        conn.execute("INSERT INTO users (user_id, balance, referrer_id, is_banned, last_daily, boost_end_time) VALUES (?, ?, ?, 0, 0, 0)", [user_id, 0, referrer_id])
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

def get_referrer(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT referrer_id FROM users WHERE user_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def get_referrals_count(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def get_last_daily(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def set_last_daily(user_id, timestamp):
    conn = get_conn()
    conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", [timestamp, user_id])
    conn.commit()
    conn.close()

def get_boost_end_time(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT boost_end_time FROM users WHERE user_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def set_boost_end_time(user_id, timestamp):
    conn = get_conn()
    conn.execute("UPDATE users SET boost_end_time = ? WHERE user_id = ?", [timestamp, user_id])
    conn.commit()
    conn.close()

init_db()

# --- Меню ---
def get_main_menu():
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url="https://lomovoi294.github.io/focus-mine-bot/")
    btn_mine = types.InlineKeyboardButton("Шахта 🟢", web_app=web_app)
    btn_daily = types.InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily_reward")
    btn_profile = types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile")
    btn_shop = types.InlineKeyboardButton("🛒 Магазин", callback_data="shop")
    
    markup.add(btn_mine)
    markup.add(btn_daily, btn_profile)
    markup.add(btn_shop)
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    if is_user_banned(m.from_user.id):
        bot.send_message(m.chat.id, "⛔ Твой аккаунт заблокирован. Доступ закрыт.")
        return

    args = m.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id == m.from_user.id: referrer_id = None
        except ValueError: pass

    add_user(m.from_user.id, referrer_id)
    
    balance = get_balance(m.from_user.id)
    bot.send_message(m.chat.id, f"Привет! Это FocusMine.\nТвой баланс: {balance:.1f} SFP", reply_markup=get_main_menu())

@bot.message_handler(commands=['invite'])
def invite(m):
    if is_user_banned(m.from_user.id): return
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Твоя ссылка для друзей:\n{link}\n\nЗа каждого друга ты получаешь 10% от его майнинга!")

# --- Профиль ---
@bot.callback_query_handler(func=lambda call: call.data == "profile")
def callback_profile(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "⛔ Доступ закрыт.")
        return
        
    balance = get_balance(user_id)
    refs = get_referrals_count(user_id)
    boost_time = get_boost_end_time(user_id)
    
    boost_status = "Не активен"
    if time.time() < boost_time:
        rem = int((boost_time - time.time()) / 60)
        boost_status = f"Активен (осталось {rem} мин.)"
    
    text = (
        f"👤 Профиль игрока\n\n"
        f"🆔 ID: {user_id}\n"
        f"💰 Баланс: {balance:.1f} SFP\n"
        f"🤝 Друзей: {refs}\n"
        f"⚡️ Буст: {boost_status}"
    )
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# --- Магазин ---
@bot.callback_query_handler(func=lambda call: call.data == "shop")
def callback_shop(call):
    user_id = call.from_user.id
    balance = get_balance(user_id)
    
    text = (
        f"🛒 Магазин FocusMine\n\n"
        f"Твой баланс: {balance:.1f} SFP\n\n"
        f"⚡️ Ускоритель x2 (1 час)\n"
        f"Удваивает добычу SFP на 60 минут.\n"
        f"Цена: 500 SFP"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn_buy = types.InlineKeyboardButton("Купить за 500 SFP", callback_data="buy_boost")
    btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")
    markup.add(btn_buy)
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_boost")
def callback_buy_boost(call):
    user_id = call.from_user.id
    balance = get_balance(user_id)
    price = 500
    
    if balance >= price:
        # Списываем деньги
        update_balance(user_id, -price)
        
        # Активируем буст (текущее время + 1 час)
        new_boost_time = int(time.time()) + 3600
        set_boost_end_time(user_id, new_boost_time)
        
        bot.answer_callback_query(call.id, "🔥 Буст активирован на 1 час!")
        
        text = (
            f"✅ Успешная покупка!\n\n"
            f"Ты купил Ускоритель x2 на 1 час.\n"
            f"Теперь твоя добыча удвоена!\n\n"
            f"Остаток на балансе: {get_balance(user_id):.1f} SFP"
        )
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu")
        markup.add(btn_back)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, f"❌ Недостаточно средств!\nНужно 500 SFP, у тебя {balance:.1f} SFP.", show_alert=True)
 # --- Возврат в меню ---
@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def callback_back(call):
    balance = get_balance(call.from_user.id)
    text = f"Привет! Это FocusMine.\nТвой баланс: {balance:.1f} SFP"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu())

# --- Ежедневный бонус ---
@bot.callback_query_handler(func=lambda call: call.data == "daily_reward")
def callback_daily(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "⛔ Доступ закрыт.")
        return

    now = int(time.time())
    last_claim = get_last_daily(user_id)
    
    if now - last_claim >= 86400:
        reward = 50
        update_balance(user_id, reward)
        set_last_daily(user_id, now)
        
        bot.answer_callback_query(call.id, f"🎁 Ты получил {reward} SFP!")
        bot.send_message(call.message.chat.id, f"✅ Бонус получен.\nБаланс: {get_balance(user_id):.1f} SFP", reply_markup=get_main_menu())
    else:
        remaining = 86400 - (now - last_claim)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        bot.answer_callback_query(call.id, f"⏳ Жди еще {hours} ч. {minutes} мин.", show_alert=True)

# --- Прием данных от сайта (с учетом БУСТА) ---
@app.route('/claim')
def claim():
    user_id = request.args.get('user_id')
    seconds = request.args.get('seconds')
    
    if user_id and seconds:
        try:
            user_id = int(user_id)
            raw_points = int(float(seconds))
            
            if is_user_banned(user_id):
                return "OK", 200

            # Античит проверяет СЫРЫЕ секунды (до буста)
            if raw_points > 0 and raw_points <= 60:
                # Проверяем буст
                boost_end = get_boost_end_time(user_id)
                is_boosted = time.time() < boost_end
                
                # Если буст есть, умножаем на 2
                final_points = raw_points * 2 if is_boosted else raw_points
                
                update_balance(user_id, final_points)
                new_balance = get_balance(user_id)
                
                boost_text = " (x2 Буст! 🔥)" if is_boosted else ""
                bot.send_message(user_id, f"✅ Успешно! Ты намайнил {final_points} SFP{boost_text}.\nБаланс: {new_balance:.1f} SFP")
                
                # Реферальные 10%
                referrer = get_referrer(user_id)
                if referrer and referrer != user_id:
                    ref_bonus = int(final_points * 0.10)
                    if ref_bonus > 0:
                        update_balance(referrer, ref_bonus)
                        try:
                            bot.send_message(referrer, f"💸 Твой реферал намайнил {final_points} SFP.\nТебе начислено {ref_bonus} SFP (10%).")
                        except: pass
                        
            else:
                ban_user(user_id)
                print(f"🚫 Пользователь {user_id} забанен за накрутку ({raw_points} сек).")
                
        except Exception as e:
            print(f"Ошибка: {e}")
            
    return "OK", 200

# --- Webhook ---
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
