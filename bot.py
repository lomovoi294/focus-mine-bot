import telebot
import os
import time
import json
import re
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
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER, is_banned INTEGER DEFAULT 0, last_daily INTEGER DEFAULT 0, boost_end_time INTEGER DEFAULT 0, last_income_time INTEGER DEFAULT 0, skin TEXT DEFAULT 'blue', nickname TEXT DEFAULT NULL, agreed INTEGER DEFAULT 0, last_claim_time INTEGER DEFAULT 0)")
    try: conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN last_daily INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN boost_end_time INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN last_income_time INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN skin TEXT DEFAULT 'blue'")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT NULL")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN agreed INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN last_claim_time INTEGER DEFAULT 0")
    except: pass
    
    conn.execute("""CREATE TABLE IF NOT EXISTS withdrawals 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, wallet TEXT, status TEXT DEFAULT 'pending', timestamp INTEGER)""")
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row

def is_user_banned(user_id):
    row = get_user_data(user_id)
    return row[3] == 1 if row else False

def ban_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", [user_id])
    conn.commit()
    conn.close()

def add_user(user_id, referrer_id=None):
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", [user_id])
    if not cursor.fetchone():
        conn.execute("INSERT INTO users (user_id, balance, referrer_id, is_banned, last_daily, boost_end_time, last_income_time, skin, nickname, agreed, last_claim_time) VALUES (?, ?, ?, 0, 0, 0, 0, 'blue', NULL, 0, 0)", [user_id, 0, referrer_id])
        conn.commit()
    conn.close()

def set_agreed(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET agreed = 1 WHERE user_id = ?", [user_id])
    conn.commit()
    conn.close()

def is_agreed(user_id):
    row = get_user_data(user_id)
    if not row: return False
    return row[9] == 1

def update_balance(user_id, points):
    conn = get_conn()
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", [points, user_id])
    conn.commit()
    conn.close()

def get_balance(user_id):
    row = get_user_data(user_id)
    return row[1] if row else 0

def get_referrer(user_id):
    row = get_user_data(user_id)
    return row[2] if row and row[2] else None

def get_referrals_count(user_id):
    conn = get_conn()
    cursor = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", [user_id])
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def get_last_daily(user_id):
    row = get_user_data(user_id)
    return row[4] if row else 0

def set_last_daily(user_id, timestamp):
    conn = get_conn()
    conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", [timestamp, user_id])
    conn.commit()
    conn.close()

def get_boost_end_time(user_id):
    row = get_user_data(user_id)
    return row[5] if row else 0

def set_boost_end_time(user_id, timestamp):
    conn = get_conn()
    conn.execute("UPDATE users SET boost_end_time = ? WHERE user_id = ?", [timestamp, user_id])
    conn.commit()
    conn.close()

def get_last_income_time(user_id):
    row = get_user_data(user_id)
    return row[6] if row else 0

def set_last_income_time(user_id, timestamp):
    conn = get_conn()
    conn.execute("UPDATE users SET last_income_time = ? WHERE user_id = ?", [timestamp, user_id])
    conn.commit()
    conn.close()

def get_skin(user_id):
    row = get_user_data(user_id)
    return row[7] if row else 'blue'

def set_skin(user_id, skin):
    conn = get_conn()
    conn.execute("UPDATE users SET skin = ? WHERE user_id = ?", [skin, user_id])
    conn.commit()
    conn.close()

def get_nickname(user_id):
    row = get_user_data(user_id)
    return row[8] if row and row[8] else None

def set_nickname(user_id, nickname):
    conn = get_conn()
    conn.execute("UPDATE users SET nickname = ? WHERE user_id = ?", [nickname, user_id])
    conn.commit()
    conn.close()

def check_nickname_exists(nickname):
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM users WHERE LOWER(nickname) = LOWER(?)", [nickname])
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_last_claim_time(user_id):
    row = get_user_data(user_id)
    return row[10] if row else 0

def set_last_claim_time(user_id, timestamp):
    conn = get_conn()
    conn.execute("UPDATE users SET last_claim_time = ? WHERE user_id = ?", [timestamp, user_id])
    conn.commit()
    conn.close()

def get_top_players():
    conn = get_conn()
    cursor = conn.execute("SELECT user_id, balance, skin, nickname FROM users ORDER BY balance DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows

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

# --- Система Рангов ---
def get_rank(balance):
    if balance >= 100000: return "👑 Легенда"
    elif balance >= 10000: return "💼 Инвестор"
    elif balance >= 1000: return "⛏ Майнер"
    else: return "🌱 Новичок"

def get_skin_emoji(skin_code):
    emojis = {'blue': '🔵', 'red': '🔴', 'green': '🟢', 'purple': '🟣'}
    return emojis.get(skin_code, '🔵')

def get_skin_name(skin_code):
    names = {'blue': '🔵 Синий', 'red': '🔴 Красный', 'green': '🟢 Зеленый', 'purple': '🟣 Фиолетовый'}
    return names.get(skin_code, '🔵 Синий')

# --- Пассивный доход ---
def collect_income(user_id):
    balance = get_balance(user_id)
    if balance < 10000: return 0, 0
    last_time = get_last_income_time(user_id)
    now = int(time.time())
    if last_time == 0:
        set_last_income_time(user_id, now)
        return 0, 0
    time_passed = now - last_time
    if time_passed > 86400: time_passed = 86400
    hours_passed = time_passed // 3600
    if hours_passed > 0:
        income = hours_passed * 100
        update_balance(user_id, income)
        set_last_income_time(user_id, last_time + (hours_passed * 3600))
        return income, hours_passed
    return 0, 0

# --- Меню ---
def get_main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    web_app = types.WebAppInfo(url="https://lomovoi294.github.io/focus-mine-bot/game2.html")
    
    btn_mine = types.InlineKeyboardButton("🚀 Войти в Шахту", web_app=web_app)
    btn_daily = types.InlineKeyboardButton("🎁 Бонус", callback_data="daily_reward")
    btn_profile = types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    btn_shop = types.InlineKeyboardButton("🛒 Магазин", callback_data="shop")
    btn_withdraw = types.InlineKeyboardButton("💸 Вывод", callback_data="withdraw")
    btn_top = types.InlineKeyboardButton("🏆 Топ", callback_data="top")
    btn_invite = types.InlineKeyboardButton("🤝 Пригласить друга", callback_data="invite")
    btn_faq = types.InlineKeyboardButton("❓ Помощь (FAQ)", callback_data="faq")
    
    markup.add(btn_mine)
    markup.add(btn_daily, btn_profile)
    markup.add(btn_shop, btn_withdraw)
    markup.add(btn_top, btn_invite)
    markup.add(btn_faq)
    return markup

# --- FAQ ---
@bot.callback_query_handler(func=lambda call: call.data == "faq")
def callback_faq(call):
    text = (
        "❓ **Часто задаваемые вопросы**\n"
        "➖➖➖➖➖➖➖➖➖➖\n\n"
        "**1. Как начать майнить?**\n"
        "Нажми «🚀 Войти в Шахту», запусти фокус и удерживай внимание. Не сворачивай приложение, иначе майнинг остановится.\n\n"
        "**2. Почему кнопка «Забрать» не нажимается?**\n"
        "Майнинг длится ровно 60 секунд. Как только лимит закончится, кнопка появится. Больше 60 секунд сидеть на экране нельзя.\n\n"
        "**3. Что такое SFP?**\n"
        "Это внутренняя игровая валюта. Её нельзя купить, её можно только заработать.\n\n"
        "**4. Как вывести SFP?**\n"
        "Нажми «💸 Вывод», укажи TON-кошелек и сумму (мин. 50 000 SFP). Заявка обрабатывается вручную. Комиссия 10%.\n\n"
        "**5. Как купить буст или скин?**\n"
        "Зайди в «🛒 Магазин». Там можно купить ускоритель за SFP или за Telegram Stars, а также скины (навсегда).\n\n"
        "**6. Почему меня забанили?**\n"
        "Бан выдается за использование скриптов/автокликеров, накрутку баланса или частые запросы.\n\n"
        "**7. Где посмотреть реферальную ссылку?**\n"
        "Нажми «🤝 Пригласить друга». Ты получаешь 10% от добычи каждого приглашенного друга.\n\n"
        "**8. Что такое пассивный доход?**\n"
        "Это бонус для ранга «Инвестор» (от 10 000 SFP). Нажми «🏦 Собрать доход» в магазине, чтобы забрать накопленное (макс. за 24 часа)."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# --- Обработка соглашения ---
@bot.callback_query_handler(func=lambda call: call.data == "agree_terms")
def callback_agree(call):
    user_id = call.from_user.id
    set_agreed(user_id)
    bot.answer_callback_query(call.id, "✅ Согласие принято!")
    
    balance = get_balance(user_id)
    rank = get_rank(balance)
    nick = get_nickname(user_id) or "Игрок"
    
    text = (
        f"👋 **Добро пожаловать в FocusMine!**\n\n"
        f"Твой фокус — твой заработок.\n\n"
        f"👤 Твой ник: **{nick}**\n"
        f"🏅 Твой ранг: {rank}\n"
        f"💰 Твой баланс: **{balance:.1f} SFP**"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

# --- Команды ---
@bot.message_handler(commands=['start'])
def start(m):
    if is_user_banned(m.from_user.id):
        bot.send_message(m.chat.id, "⛔ Твой аккаунт заблокирован за нарушение правил.")
        return

    args = m.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id == m.from_user.id: referrer_id = None
        except ValueError: pass

    add_user(m.from_user.id, referrer_id)
    
    if not is_agreed(m.from_user.id):
        text = (
            f"⚖️ **Пользовательское соглашение**\n\n"
            f"Перед началом игры, пожалуйста, ознакомьтесь с нашими правилами.\n\n"
            f"Запрещено: использование скриптов для накрутки, создание мультиаккаунтов, мошенничество.\n\n"
            f"Нажимая кнопку «Согласен», вы подтверждаете, что ознакомились с правилами и принимаете их."
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📄 Читать правила", url="https://lomovoi294.github.io/focus-mine-bot/terms.html"))
        markup.add(types.InlineKeyboardButton("✅ Согласен и продолжить", callback_data="agree_terms"))
        bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        return

    balance = get_balance(m.from_user.id)
    rank = get_rank(balance)
    nick = get_nickname(m.from_user.id) or "Игрок"
    
    text = (
        f"👋 **Добро пожаловать в FocusMine!**\n\n"
        f"Твой фокус — твой заработок. Удерживай внимание, майни SFP и приглашай друзей.\n\n"
        f"👤 Твой ник: **{nick}**\n"
        f"🏅 Твой ранг: {rank}\n"
        f"💰 Твой баланс: **{balance:.1f} SFP**"
    )
    bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(m.from_user.id))

# --- Профиль ---
@bot.callback_query_handler(func=lambda call: call.data == "profile")
def callback_profile(call):
    user_id = call.from_user.id
    if is_user_banned(user_id): return
    balance = get_balance(user_id)
    refs = get_referrals_count(user_id)
    boost_time = get_boost_end_time(user_id)
    boost_status = f"Активен (🔥 {int((boost_time - time.time()) / 60)} мин.)" if time.time() < boost_time else "❌ Не активен"
    rank = get_rank(balance)
    skin_emoji = get_skin_emoji(get_skin(user_id))
    nick = get_nickname(user_id) or "Не задан"
    
    text = (
        f"👤 **Твой профиль** {skin_emoji}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 Ник: **{nick}**\n"
        f"🆔 ID: `{user_id}`\n"
        f"🏅 Ранг: **{rank}**\n"
        f"💰 Баланс: **{balance:.1f} SFP**\n"
        f"🤝 Друзей: **{refs}**\n"
        f"⚡️ Буст x2: {boost_status}\n"
        f"➖➖➖➖➖➖➖➖➖➖"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ Изменить ник", callback_data="change_nick"))
    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# --- Смена ника ---
@bot.callback_query_handler(func=lambda call: call.data == "change_nick")
def callback_change_nick(call):
    msg = bot.send_message(call.message.chat.id, "✏️ Введи свой новый ник (от 3 до 15 символов, только буквы и цифры):")
    bot.register_next_step_handler(msg, process_new_nick)

def process_new_nick(m):
    new_nick = m.text.strip()
    user_id = m.from_user.id
    
    if not re.match(r"^[a-zA-Z0-9_]{3,15}$", new_nick):
        bot.send_message(m.chat.id, "❌ Ник должен быть от 3 до 15 символов. Разрешены только английские буквы, цифры и _.")
        return
        
    if check_nickname_exists(new_nick):
        bot.send_message(m.chat.id, "❌ Этот ник уже занят. Придумай другой.")
        return
        
    set_nickname(user_id, new_nick)
    bot.send_message(m.chat.id, f"✅ Отлично! Твой новый ник: **{new_nick}**", parse_mode='Markdown', reply_markup=get_main_menu(user_id))

# --- Приглашение ---
@bot.callback_query_handler(func=lambda call: call.data == "invite")
def callback_invite(call):
    u = bot.get_me().username
    link = f"https://t.me/{u}?start={call.from_user.id}"
    text = (
        f"🤝 **Реферальная система**\n\n"
        f"Приглашай друзей и получай **10%** от их добычи SFP навсегда!\n\n"
        f"Твоя ссылка:\n`{link}`"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# --- Топ игроков ---
@bot.callback_query_handler(func=lambda call: call.data == "top")
def callback_top(call):
    top_users = get_top_players()
    if not top_users:
        bot.answer_callback_query(call.id, "Пока нет игроков.")
        return
    text = "🏆 **Топ-10 игроков FocusMine**\n➖➖➖➖➖➖➖➖➖➖\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for index, user in enumerate(top_users):
        user_id, balance, skin, nickname = user[0], user[1], user[2], user[3]
        skin_emoji = get_skin_emoji(skin)
        display_name = nickname if nickname else f"ID: {user_id}"
        name = f"{skin_emoji} {display_name}"
        if user_id == admin_id: name += " 👑"
        text += f"{medals[index]} {name} — **{balance:.1f} SFP**\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# --- Магазин ---
@bot.callback_query_handler(func=lambda call: call.data == "shop")
def callback_shop(call):
    user_id = call.from_user.id
    balance = get_balance(user_id)
    current_skin = get_skin(user_id)
    
    text = (
        f"🛒 **Магазин FocusMine**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 Баланс: **{balance:.1f} SFP**\n"
        f"🎨 Текущий скин: {get_skin_name(current_skin)}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"⚡️ **Ускоритель x2 (1 час)**\n"
        f"За SFP: 500 SFP\n"
        f"За Stars: 50 ⭐️\n\n"
        f"🎨 **Скины (навсегда):**\n"
        f"🔴 Красный — 2000 SFP\n"
        f"🟢 Зеленый — 2000 SFP\n"
        f"🟣 Фиолетовый — 3000 SFP\n"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⚡️ Купить Буст (500 SFP)", callback_data="buy_boost"))
    markup.add(types.InlineKeyboardButton("⭐️ Купить Буст (50 Stars)", callback_data="buy_boost_stars"))
    
    if balance >= 10000:
        markup.add(types.InlineKeyboardButton("🏦 Собрать доход", callback_data="collect_income"))
        
    markup.add(types.InlineKeyboardButton("🔴 Купить Красный (2000)", callback_data="buy_skin_red"))
    markup.add(types.InlineKeyboardButton("🟢 Купить Зеленый (2000)", callback_data="buy_skin_green"))
    markup.add(types.InlineKeyboardButton("🟣 Купить Фиолетовый (3000)", callback_data="buy_skin_purple"))
    
    if current_skin != 'blue':
        markup.add(types.InlineKeyboardButton("🔵 Снять скин (Бесплатно)", callback_data="remove_skin"))
        
    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_boost")
def callback_buy_boost(call):
    user_id = call.from_user.id
    if get_balance(user_id) >= 500:
        update_balance(user_id, -500)
        set_boost_end_time(user_id, int(time.time()) + 3600)
        bot.answer_callback_query(call.id, "🔥 Буст активирован!")
        callback_shop(call)
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно SFP!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "buy_boost_stars")
def callback_buy_boost_stars(call):
    prices = [types.LabeledPrice(label="Ускоритель x2 (1 час)", amount=50)]
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Ускоритель x2",
        description="Удваивает добычу SFP на 1 час!",
        invoice_payload="boost_x2_50stars",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    set_boost_end_time(user_id, int(time.time()) + 3600)
    bot.send_message(message.chat.id, "🎉 Оплата прошла успешно! Твой буст x2 активирован на 1 час.")
    bot.send_message(admin_id, f"💰 Пользователь {user_id} купил буст за 50 Stars!")

@bot.callback_query_handler(func=lambda call: call.data == "collect_income")
def callback_collect_income(call):
    user_id = call.from_user.id
    income, hours = collect_income(user_id)
    if income > 0:
        bot.answer_callback_query(call.id, f"💰 Ты получил {income} SFP за {hours} ч.")
        callback_shop(call)
    else:
        bot.answer_callback_query(call.id, "⏳ Ты пока не накопил доход (нужен минимум 1 час).", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_skin_"))
def callback_buy_skin(call):
    user_id = call.from_user.id
    skin = call.data.split("_")[2]
    prices = {"red": 2000, "green": 2000, "purple": 3000}
    price = prices.get(skin, 999999)
    
    if get_skin(user_id) == skin:
        bot.answer_callback_query(call.id, "У тебя уже надет этот скин!", show_alert=True)
        return
        
    if get_balance(user_id) >= price:
        update_balance(user_id, -price)
        set_skin(user_id, skin)
        bot.answer_callback_query(call.id, f"🎨 Скин куплен и надет!")
        callback_shop(call)
    else:
        bot.answer_callback_query(call.id, f"❌ Нужно {price} SFP!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "remove_skin")
def callback_remove_skin(call):
    user_id = call.from_user.id
    set_skin(user_id, 'blue')
    bot.answer_callback_query(call.id, "🔵 Скин снят. Вернули стандартный цвет.")
    callback_shop(call)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def callback_back(call):
    balance = get_balance(call.from_user.id)
    rank = get_rank(balance)
    text = f"🏠 **Главное меню**\n\n💰 Баланс: **{balance:.1f} SFP**\n🏅 Ранг: {rank}"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=get_main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "daily_reward")
def callback_daily(call):
    user_id = call.from_user.id
    if is_user_banned(user_id): return
    now = int(time.time())
    if now - get_last_daily(user_id) >= 86400:
        update_balance(user_id, 50)
        set_last_daily(user_id, now)
        bot.answer_callback_query(call.id, "🎁 Ты получил 50 SFP!")
        bot.send_message(call.message.chat.id, f"✅ Бонус получен. Баланс: {get_balance(user_id):.1f} SFP", reply_markup=get_main_menu(user_id))
    else:
        rem = 86400 - (now - get_last_daily(user_id))
        bot.answer_callback_query(call.id, f"⏳ Жди еще {rem // 3600} ч. {(rem % 3600) // 60} мин.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def callback_withdraw(call):
    user_id = call.from_user.id
    if get_balance(user_id) < 50000:
        bot.answer_callback_query(call.id, f"❌ Минимум 50 000 SFP.\nУ тебя: {get_balance(user_id):.1f}", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "💸 Введи адрес кошелька TON:")
    bot.register_next_step_handler(msg, process_wallet_address)

def process_wallet_address(m):
    msg = bot.send_message(m.chat.id, "Введи сумму SFP (мин. 50 000):")
    bot.register_next_step_handler(msg, process_withdraw_amount, m.text.strip())

def process_withdraw_amount(m, wallet):
    try:
        amount = float(m.text)
        user_id = m.from_user.id
        if amount < 50000 or amount > get_balance(user_id):
            bot.send_message(m.chat.id, "❌ Неверная сумма. Минимум 50 000 SFP.")
            return
        update_balance(user_id, -amount)
        req_id = create_withdrawal(user_id, amount, wallet)
        fee = amount * 0.10
        payout = amount - fee
        bot.send_message(m.chat.id, f"✅ Заявка на {amount} SFP создана!\n(Комиссия 10%: {fee:.1f} SFP)\nК получению: {payout:.1f} SFP. Ожидай.")
        if admin_id:
            nick = get_nickname(user_id) or f"ID: {user_id}"
            text = (f"🔔 **Заявка #{req_id}**\n"
                    f"От: {nick} (`{user_id}`)\n"
                    f"Сумма: **{amount} SFP**\n"
                    f"К выплате (минус 10%): **{payout:.1f} SFP**\n"
                    f"Кошелек: `{wallet}`")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Выплачено", callback_data=f"approve_{req_id}"))
            markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{req_id}"))
            bot.send_message(admin_id, text, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        print(f"Ошибка при выводе: {e}")
        bot.send_message(m.chat.id, f"❌ Ошибка: {e}")

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
            now = int(time.time())
            
            if is_user_banned(user_id): 
                return "OK", 200

            last_claim = get_last_claim_time(user_id)
            if now - last_claim < 5:
                return "OK", 200
            
            if 0 < raw_points <= 60:
                base_points = raw_points * 0.5
                is_boosted = time.time() < get_boost_end_time(user_id)
                final_points = base_points * 2 if is_boosted else base_points
                
                update_balance(user_id, final_points)
                set_last_claim_time(user_id, now)
                
                boost_text = " (x2)" if is_boosted else ""
                bot.send_message(user_id, f"✅ Намайнил {final_points:.1f} SFP{boost_text}.\nБаланс: {get_balance(user_id):.1f} SFP")
                
                referrer = get_referrer(user_id)
                if referrer and referrer != user_id:
                    ref_bonus = int(final_points * 0.10)
                    if ref_bonus > 0:
                        update_balance(referrer, ref_bonus)
                        try: bot.send_message(referrer, f"💸 Реферал намайнил {final_points:.1f} SFP. Тебе +{ref_bonus} SFP.")
                        except: pass
            else:
                ban_user(user_id)
                
        except Exception as e:
            print(f"Ошибка claim: {e}")
            
    return "OK", 200

@app.route('/get_skin/<int:user_id>')
def get_user_skin_route(user_id):
    skin = get_skin(user_id)
    return skin, 200

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
