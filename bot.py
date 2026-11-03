import telebot
import os
import time
import json
from telebot import types
from flask import Flask, request
from flask_cors import CORS
import libsql

# --- Настройки ---
t = os.environ.get('BOT_TOKEN')
turso_url = os.environ.get('TURSO_URL')
turso_token = os.environ.get('TURSO_TOKEN')
admin_id = int(os.environ.get('ADMIN_ID', 0))

bot = telebot.TeleBot(t, threaded=False)
app = Flask(__name__)
CORS(app)

# --- База данных ---
def get_conn():
    return libsql.connect(turso_url, auth_token=turso_token)

def init_db():
    conn = get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER, is_banned INTEGER DEFAULT 0, last_daily INTEGER DEFAULT 0, boost_end_time INTEGER DEFAULT 0)")
    try: conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN last_daily INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN boost_end_time INTEGER DEFAULT 0")
    except: pass
    
    conn.execute("""CREATE TABLE IF NOT EXISTS withdrawals 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, wallet TEXT, status TEXT DEFAULT 'pending', timestamp INTEGER)""")
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

def create_withdrawal(user_id, amount, wallet):
    conn = get_conn()
    cursor = conn.execute("INSERT INTO withdrawals (user_id, amount, wallet, timestamp) VALUES (?, ?, ?, ?)", [user_id, amount, wallet, int(time.time())])
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return req_id

def get_withdrawal(req_id):
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM withdrawals WHERE id = ?", [req_id])
    row = cursor.fetchone()
    conn.close()
    return row

def update_withdrawal_status(req_id, status):
    conn = get_conn()
    conn.execute("UPDATE withdrawals SET status = ? WHERE id = ?", [status, req_id])
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
    btn_withdraw = types.InlineKeyboardButton("💸 Вывести SFP", callback_data="withdraw")
    
    markup.add(btn_mine)
    markup.add(btn_daily, btn_profile)
    markup.add(btn_shop, btn_withdraw)
    return markup

# --- Команды ---
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

@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.from_user.id != admin_id: return
    bot.send_message(m.chat.id, "🛠 Админ-панель активна.")

# --- Профиль ---
@bot.callback_query_handler(func=lambda call: call.data == "profile")
def callback_profile(call):
    user_id = call.from_user.id
    if is_user_banned(user_id): return
    balance = get_balance(user_id)
    refs = get_referrals_count(user_id)
    boost_time = get_boost_end_time(user_id)
    boost_status = f"Активен (осталось {int((boost_time - time.time()) / 60)} мин.)" if time.time() < boost_time else "Не активен"
    
    text = f"👤 Профиль\n\n🆔 ID: {user_id}\n💰 Баланс: {balance:.1f} SFP\n🤝 Друзей: {refs}\n⚡️ Буст: {boost_status}"
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# --- Магазин ---
@bot.callback_query_handler(func=lambda call: call.data == "shop")
def callback_shop(call):
    user_id = call.from_user.id
    balance = get_balance(user_id)
    text = f"🛒 Магазин\n\nБаланс: {balance:.1f} SFP\n\n⚡️ Ускоритель x2 (1 час)\nЦена: 500 SFP"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Купить за 500 SFP", callback_data="buy_boost"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_boost")
def callback_buy_boost(call):
    user_id = call.from_user.id
    if get_balance(user_id) >= 500:
        update_balance(user_id, -500)
        set_boost_end_time(user_id, int(time.time()) + 3600)
        bot.answer_callback_query(call.id, "🔥 Буст активирован!")
        bot.edit_message_text(f"✅ Успешно! Буст x2 активирован.\nБаланс: {get_balance(user_id):.1f} SFP", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно SFP!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def callback_back(call):
    bot.edit_message_text(f"Главное меню.\nБаланс: {get_balance(call.from_user.id):.1f} SFP", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu())

# --- Ежедневный бонус ---
@bot.callback_query_handler(func=lambda call: call.data == "daily_reward")
def callback_daily(call):
    user_id = call.from_user.id
    if is_user_banned(user_id): return
    now = int(time.time())
    if now - get_last_daily(user_id) >= 86400:
        update_balance(user_id, 50)
        set_last_daily(user_id, now)
        bot.answer_callback_query(call.id, "🎁 Ты получил 50 SFP!")
        bot.send_message(call.message.chat.id, f"✅ Бонус получен. Баланс: {get_balance(user_id):.1f} SFP", reply_markup=get_main_menu())
    else:
        rem = 86400 - (now - get_last_daily(user_id))
        bot.answer_callback_query(call.id, f"⏳ Жди еще {rem // 3600} ч. {(rem % 3600) // 60} мин.", show_alert=True)

# --- Вывод ---
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def callback_withdraw(call):
    user_id = call.from_user.id
    if get_balance(user_id) < 1000:
        bot.answer_callback_query(call.id, f"❌ Минимум 1000 SFP.\nУ тебя: {get_balance(user_id):.1f}", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "💸 Введи адрес кошелька TON:")
    bot.register_next_step_handler(msg, process_wallet_address)

def process_wallet_address(m):
    msg = bot.send_message(m.chat.id, "Введи сумму SFP (мин. 1000):")
    bot.register_next_step_handler(msg, process_withdraw_amount, m.text.strip())

def process_withdraw_amount(m, wallet):
    try:
        amount = float(m.text)
        user_id = m.from_user.id
        if amount < 1000 or amount > get_balance(user_id):
            bot.send_message(m.chat.id, "❌ Неверная сумма.")
            return
        update_balance(user_id, -amount)
        req_id = create_withdrawal(user_id, amount, wallet)
        bot.send_message(m.chat.id, f"✅ Заявка на {amount} SFP создана! Ожидай.")
        
        if admin_id:
            text = f"🔔 Заявка #{req_id}\nОт: {user_id}\nСумма: {amount} SFP\nКошелек: {wallet}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Выплачено", callback_data=f"approve_{req_id}"))
            markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{req_id}"))
            bot.send_message(admin_id, text, parse_mode='Markdown', reply_markup=markup)
    except ValueError:
        bot.send_message(m.chat.id, "❌ Введи число.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def callback_admin_action(call):
    if call.from_user.id != admin_id: return
    action, req_id = call.data.split("_")
    req = get_withdrawal(int(req_id))
    if not req or req[4] != 'pending': return
        
    user_id, amount = req[1], req[2]
    if action == "approve":
        update_withdrawal_status(int(req_id), "approved")
        bot.edit_message_text(f"✅ Заявка {req_id} одобрена.", call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, f"🎉 Вывод {amount} SFP одобрен!")
    else:
        update_balance(user_id, amount)
        update_withdrawal_status(int(req_id), "rejected")
        bot.edit_message_text(f"❌ Заявка {req_id} отклонена.", call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, f"⚠️ Вывод отклонен. {amount} SFP возвращены.")

# --- ПРИЕМ ДАННЫХ ОТ САЙТА ---
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

            if 0 < raw_points <= 60:
                is_boosted = time.time() < get_boost_end_time(user_id)
                final_points = raw_points * 2 if is_boosted else raw_points
                
                update_balance(user_id, final_points)
                boost_text = " (x2)" if is_boosted else ""
                bot.send_message(user_id, f"✅ Намайнил {final_points} SFP{boost_text}.\nБаланс: {get_balance(user_id):.1f} SFP")
                
                referrer = get_referrer(user_id)
                if referrer and referrer != user_id:
                    ref_bonus = int(final_points * 0.10)
                    if ref_bonus > 0:
                        update_balance(referrer, ref_bonus)
                        try: 
                            bot.send_message(referrer, f"💸 Реферал намайнил {final_points} SFP. Тебе +{ref_bonus} SFP.")
                        except: 
                            pass
            else:
                ban_user(user_id)
        except Exception as e:
            print(f"Ошибка claim: {e}")
            
        if is_user_banned(user_id):        
            return "OK", 200
        
        if 0 < raw_points <= 60:
            is_boosted = time.time() < get_boost_end_time(user_id)
            final_points = raw_points * 2 if is_boosted else raw_points
        
            update_balance(user_id, final_points)
            boost_text = " (x2)" if is_boosted else ""
            bot.send_message(user_id, f"✅ Намайнил {final_points} SFP{boost_text}.\nБаланс: {get_balance(user_id):.1f} SFP")
                
            referrer = get_referrer(user_id)
            if referrer and referrer != user_id:
                ref_bonus = int(final_points * 0.10)
                if ref_bonus > 0:
                    update_balance(referrer, ref_bonus)
                    try: 
                        bot.send_message(referrer, f"💸 Реферал намайнил {final_points} SFP. Тебе +{ref_bonus} SFP.")
                    except:
                        pass
        else:
            ban_user(user_id)
            
        except Exception as e:
            print(f"Ошибка claim: {e}")
            
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
