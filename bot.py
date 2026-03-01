# -*- coding: utf-8 -*-
import telebot
from telebot import types
import time
import re
import json
import os
import datetime  # уже есть в файле, используем datetime.datetime/ date
from collections import defaultdict
import threading

TOKEN = "8446171144:AAGFCANz0Zg7ZvLFootABJ866pkm6dhoeNg"
bot = telebot.TeleBot(TOKEN)
ADMIN_CHAT_ID = 5782683757

# словарь для хранения активности
user_messages = defaultdict(list)

STAR_SHOP = {
    "coins_5000":  {"coins": 5000,  "stars": 3},
    "coins_10000": {"coins": 10000, "stars": 15},
    "coins_50000": {"coins": 50000, "stars": 25},
    "coins_100000":{"coins": 100000,"stars": 50},
}

ROLES_DB = "roles_time.json"

# === ИНИЦИАЛИЗАЦИЯ ФАЙЛА АКТИВНОСТИ ===
ACTIVITY_FILE = "activity.json"

# если файла нет — создаём пустой словарь {}
if not os.path.exists(ACTIVITY_FILE):
    with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4, ensure_ascii=False)

# загружаем активность
with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
    activity_data = json.load(f)

# 🔹 Функция автосохранения активности
def autosave_activity():
    def convert(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return obj

    while True:
        try:
            # преобразуем все datetime в строки
            def recursive_convert(data):
                if isinstance(data, dict):
                    return {k: recursive_convert(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [recursive_convert(v) for v in data]
                else:
                    return convert(data)

            safe_data = recursive_convert(activity_data)
            with open("activity.json", "w", encoding="utf-8") as f:
                json.dump(safe_data, f, ensure_ascii=False, indent=2)
            print("✅ Автосохранение активности выполнено")
        except Exception as e:
            print(f"⚠ Ошибка при автосохранении: {e}")
        time.sleep(60)  # ждать 1 минуту

COINS_FILE = "coins.json"

def load_roles():
    try:
        with open(ROLES_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_roles(data):
    with open(ROLES_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Загрузка данных о монетах
def load_coins():
    if os.path.exists(COINS_FILE):
        try:
            with open(COINS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Ошибка при загрузке монет: {e}")
    return {}

# Сохранение данных о монетах
def save_coins():
    try:
        with open(COINS_FILE, "w", encoding="utf-8") as f:
            json.dump(coins_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Ошибка при сохранении монет: {e}")

# Инициализация данных о монетах
coins_data = load_coins()

IMMUNE_FILE = "immune_users.json"

# Загрузка данных об иммунитете
def load_immune_users():
    if os.path.exists(IMMUNE_FILE):
        try:
            with open(IMMUNE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Нормализуем ключи в строки и значения в int
                try:
                    return {str(k): int(v) for k, v in data.items()}
                except Exception:
                    return data
        except Exception as e:
            print(f"⚠ Ошибка при загрузке данных об иммунитете: {e}")
    return {}

# Сохранение данных об иммунитете
def save_immune_users(data):
    try:
        # Убедимся, что ключи — строки и значения — целые числа
        safe = {str(k): int(v) for k, v in (data or {}).items()}
        with open(IMMUNE_FILE, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Ошибка при сохранении данных об иммунитете: {e}")

# ====== Активность ======
# `activity_data` уже загружен выше из файла; убедимся, что это словарь.
if not isinstance(activity_data, dict):
    activity_data = {}

# --- БЕЗОПАСНОЕ Сохранение activity (конвертирует datetime -> ISO строки) ---
def _safe_convert(obj):
    if isinstance(obj, dict):
        return {k: _safe_convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_convert(v) for v in obj]
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return obj

def save_activity():
    try:
        with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump(activity_data, f, ensure_ascii=False, indent=4)
        print("✅ Данные об активности успешно сохранены.")
    except Exception as e:
        print(f"⚠ Ошибка при сохранении данных об активности: {e}")

# `load_roles` / `save_roles` определены выше; тут дублирование удалено.

def remove_role(chat_id, user_id, role_name):
    try:
        # снимаем админку / роль
        bot.promote_chat_member(
            chat_id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_video_chats=False
        )
        return True
    except Exception as e:
        print("REMOVE ROLE ERROR:", e)
        return False

def _activity_add(user, chat_id=None):
    user_id = str(user.id)
    # Если данных о пользователе нет, создаём запись
    if user_id not in activity_data:
        activity_data[user_id] = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": getattr(user, "last_name", None),
            "all": {"messages": 0},
            "by_chat": {}
        }
    # Обновляем имя пользователя, если оно изменилось
    if user.username:
        activity_data[user_id]["username"] = user.username
    if user.first_name:
        activity_data[user_id]["first_name"] = user.first_name
    if getattr(user, "last_name", None):
        activity_data[user_id]["last_name"] = user.last_name

    # Увеличиваем общий счётчик сообщений
    activity_data[user_id]["all"]["messages"] += 1
    # Увеличиваем счётчик сообщений по чатам
    if chat_id is not None:
        chat_id = str(chat_id)
        if chat_id not in activity_data[user_id]["by_chat"]:
            activity_data[user_id]["by_chat"][chat_id] = 0
        activity_data[user_id]["by_chat"][chat_id] += 1

    # Сохраняем данные об активности
    save_activity()

def _display_name(user_id: int, chat_id: int = None) -> str:
    """Красиво показываем имя: First Last -> @username -> ID.
       Работает с ключами `activity_data` в виде строк и безопасно пытается
       подтянуть данные через `get_chat_member` (конвертирует ID в int).
    """
    uid = str(user_id)
    d = activity_data.get(uid, {})
    first = d.get("first_name")
    last = d.get("last_name")
    uname = d.get("username")

    name = None
    if first or last:
        name = f"{first or ''} {last or ''}".strip()
    if not name and uname:
        name = f"@{uname}"

    # если до сих пор пусто — пробуем подтянуть из чата
    if not name and chat_id is not None:
        try:
            member = bot.get_chat_member(chat_id, int(uid))
            u = member.user
            first = first or (u.first_name or None)
            last = last or (getattr(u, "last_name", None))
            uname = uname or (u.username or None)

            if first or last:
                name = f"{first or ''} {last or ''}".strip()
            if not name and uname:
                name = f"@{uname}"

            # кэшируем обратно
            dd = activity_data.setdefault(uid, {})
            if first:
                dd["first_name"] = first
            if last:
                dd["last_name"] = last
            if uname:
                dd["username"] = uname
            save_activity()
        except Exception:
            pass

    return name or f"ID:{uid}"

def check_leader_and_promote(chat_id: int):
    if not activity_data:
        return

    # сортируем по общему числу сообщений
    leaderboard = sorted(activity_data.items(),
                         key=lambda x: x[1]["all"]["messages"],
                         reverse=True)

    if not leaderboard:
        return

    top_uid, top_stats = leaderboard[0]
    now_dt = datetime.datetime.utcnow()

    leader_since = top_stats.get("leader_since")

    # приводим leader_since к datetime, если это строка
    if leader_since:
        if isinstance(leader_since, str):
            try:
                then_dt = datetime.datetime.fromisoformat(leader_since)
            except Exception:
                then_dt = now_dt
        elif isinstance(leader_since, datetime.datetime):
            then_dt = leader_since
        else:
            then_dt = now_dt
    else:
        # отмечаем время первого попадания в лидерство в ISO-строке
        top_stats["leader_since"] = now_dt.isoformat()
        save_activity()
        return

    # 12 часов на первом месте — выдаём 300 монет за лидерство
    try:
        if (now_dt - then_dt).total_seconds() >= 12 * 3600:
            reward_coins = 300
            add_coins(int(top_uid), reward_coins, bypass_block=True)
            bot.send_message(chat_id, f"👑 {_display_name(top_uid, chat_id)} держится на первом месте 12 часов! Получено {reward_coins} монет за лидерство! 💰")
            # обновляем метку в ISO-формате
            top_stats["leader_since"] = now_dt.isoformat()
            save_activity()
    except Exception as e:
        print(f"Ошибка при выдаче награды: {e}")

from telebot import types
import sys, os

# 🔑 Твой Telegram ID
OWNER_ID = 5782683757  
ADMIN_USER_ID = OWNER_ID

# ⚙ Меню управления
@bot.message_handler(commands=["control"])
def cmd_control(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ У вас нет прав для управления ботом.")
        return

    markup = types.InlineKeyboardMarkup()
    stop_btn = types.InlineKeyboardButton("⛔ Остановить бота", callback_data="stop_bot")
    restart_btn = types.InlineKeyboardButton("🔄 Перезапустить бота", callback_data="restart_bot")
    markup.add(stop_btn, restart_btn)

    bot.send_message(message.chat.id, "⚙ Управление ботом:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buystar_"))
def process_buy(call):
    product_key = call.data.replace("buystar_", "")
    # Для оплаты Stars используем STAR_SHOP (dict с coins/stars)
    product = STAR_SHOP.get(product_key)

    if not product:
        print(f"[DEBUG] Товар не найден: {product_key}")  # Отладочное сообщение
        bot.answer_callback_query(call.id, "❌ Товар не найден")
        return

    print(f"[DEBUG] Найден товар: {product_key} -> {product}")  # Отладочное сообщение

    prices = [
        types.LabeledPrice(
            label=f"{product['coins']} монет",
            amount=product["stars"]  # ⚠️ amount = КОЛ-ВО STARS
        )
    ]

    bot.send_invoice(
        chat_id=call.from_user.id,
        title="Покупка монет",
        description=f"{product['coins']} монет за ⭐ {product['stars']}",
        invoice_payload=product_key,  # ✅ ВАЖНО
        provider_token="",  # Убедитесь, что токен провайдера указан
        currency="XTR",
        prices=prices
)


    bot.answer_callback_query(call.id)

# 🔘 Обработка кнопок
@bot.callback_query_handler(func=lambda call: call.data in ["stop_bot", "restart_bot"])
def handle_control(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return

    if call.data == "stop_bot":
        bot.send_message(call.message.chat.id, "⛔ Бот выключается...")
        sys.exit(0)

    elif call.data == "restart_bot":
        bot.send_message(call.message.chat.id, "🔄 Бот перезапускается...")
        python = sys.executable
        os.execl(python, python, *sys.argv)

# 🔹 Команда для ручного сохранения активности
@bot.message_handler(commands=["saveactivity"])
def cmd_saveactivity(message):
    if message.from_user.id != OWNER_ID:  # только владелец
        bot.reply_to(message, "⛔ У тебя нет прав для этой команды!")
        return

    try:
        with open("activity.json", "w", encoding="utf-8") as f:
            json.dump(activity_data, f, ensure_ascii=False, indent=2)
        bot.reply_to(message, "✅ Активность успешно сохранена!")
    except Exception as e:
        bot.reply_to(message, f"⚠ Ошибка при сохранении: {e}")


# =============== АКТИВНОСТЬ ===============

# Duplicate activity file loading removed — handled earlier in the file.
from datetime import timezone

# =============== ВСПОМОГАТЕЛЬНОЕ ===============
def is_admin(chat_id, user_id) -> bool:
    """Проверка, что пользователь админ чата."""
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "creator")
    except Exception:
        return False

def role_watcher():
    while True:
        roles = load_roles()
        now = int(time.time())
        changed = False

        for key in list(roles.keys()):
            data = roles[key]
            # Пропускаем служебные/битые записи, чтобы поток не падал
            if not isinstance(data, dict):
                continue
            if "expire" not in data or "chat_id" not in data or "user_id" not in data or "role" not in data:
                continue

            if data["expire"] == 0:
                continue  # навсегда

            try:
                expire_ts = int(data["expire"])
            except Exception:
                continue

            if now >= expire_ts:
                chat_id = data["chat_id"]
                user_id = data["user_id"]
                role = data["role"]

                try:
                    remove_role(chat_id, user_id, role)
                except:
                    pass

                try:
                    bot.send_message(
                        user_id,
                        f"⏳ Срок роли *{role}* истёк.\nРоль была автоматически снята.",
                        parse_mode="Markdown"
                    )
                except:
                    pass

                del roles[key]
                changed = True

        if changed:
            save_roles(roles)

        time.sleep(60)

def parse_time_to_seconds(s: str):
    """'30m' -> 1800; '2h' -> 7200; '1d' -> 86400"""
    if not s:
        return 3600
    m = re.fullmatch(r"(\d+)\s*([mhd])", s.strip().lower())
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    if unit == "m": return value * 60
    if unit == "h": return value * 3600
    if unit == "d": return value * 86400
    return None

# Список запрещённых слов для антиспама/антимата
banned_words = [
    "Сука", "сука", "Блять", "блять", "Пизда", "пизда", "Хуй", "хуй", "Ебать", "ебать", "Еблан", "еблан", "Пидор", "пидор", "Пидрила", "пидрила", "Мудак", "мудак","Долбоёб", "долбоёб", "Пиздец", "пиздец", "Гандон", "гандон", "Залупа", "залупа","Пиздюк", "пиздюк", "Пидорас", "пидорас", "Ебаный", "ебаный", "Ебать", "ебать", "Еблан", "еблан", "Пиздабол", "пиздабол", "Мудак", "мудак","Долбоёб", "долбоёб", "Пиздец", "пиздец", "Гандон", "гандон", "Залупа", "залупа","Хуесос","хуесос","Пидорас","пидорас","Ебать","ебать","Ебаный","ебаный","Блядь","блядь","Бля","бля","Пизда","пизда","Хуй","хуй","Пиздюк","пиздюк","Пидор","пидор","Пидрила","пидрила","Мудак","мудак","Долбоёб","долбоёб","Пиздец","пиздец","Гандон","гандон","Залупа","залупа",""
    # добавь свои слова через запятую
]

# Приведём слова к нижнему регистру и уберём пустые строки
banned_words = [w.lower() for w in banned_words if isinstance(w, str) and w.strip()]

# ===== Антиспам (личные сообщения) =====
PRIVATE_SPAM_FILE = "private_spam.json"
private_spam_blocks = {}  # { uid(str): until_timestamp }

def load_private_spam():
    global private_spam_blocks
    if os.path.exists(PRIVATE_SPAM_FILE):
        try:
            with open(PRIVATE_SPAM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # ensure numeric
                private_spam_blocks = {k: float(v) for k, v in data.items()}
        except Exception:
            private_spam_blocks = {}
    else:
        private_spam_blocks = {}

def save_private_spam():
    try:
        with open(PRIVATE_SPAM_FILE, "w", encoding="utf-8") as f:
            json.dump(private_spam_blocks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Ошибка при сохранении private_spam: {e}")

load_private_spam()

# ===================== АВТОМОДЕРАЦИЯ ======================
@bot.message_handler(func=lambda m: bool(getattr(m, "text", None)) and not m.text.startswith("/"))
def message_handler_all(message):
    user_id = message.from_user.id
    now = time.time()

    # Отслеживаем активность
    try:
        _activity_add(message.from_user, message.chat.id)
    except Exception:
        pass

    # Инициализация списка сообщений
    uid = str(user_id)
    if user_id not in user_messages:
        user_messages[user_id] = []

    # Добавляем таймстамп и оставляем последние 10 секунд
    user_messages[user_id].append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t <= 10]

    GROUP_THRESHOLD = 5
    PRIVATE_THRESHOLD = 6

    # Спам-проверка
    try:
        if message.chat.type == "private":
            if len(user_messages[user_id]) >= PRIVATE_THRESHOLD:
                block_seconds = 10 * 60
                private_spam_blocks[uid] = time.time() + block_seconds
                save_private_spam()
                bot.reply_to(message, f"⚠️ {message.from_user.first_name}, слишком много сообщений в ЛС. Начисления монет/XP отключены на 10 минут.")
                try:
                    admin_text = f"⚠️ Пользователь @{message.from_user.username or message.from_user.first_name} (ID:{uid}) заблокирован от начислений на 10 минут из-за спама в ЛС."
                    bot.send_message(ADMIN_CHAT_ID, admin_text)
                except Exception:
                    pass
                user_messages[user_id] = []
                return
        else:
            if len(user_messages[user_id]) >= GROUP_THRESHOLD:
                try:
                    if not is_admin(message.chat.id, user_id):
                        # Если у пользователя нет истории мутов/банов — даём предупреждение
                        uid_str = str(user_id)
                        has_history = (int(mute_history.get(uid_str, {}).get("count", 0)) > 0) or any((int(tb.get("user_id")) == user_id) for tb in temp_bans)
                        if not has_history:
                            add_warning_for(user_id, by="auto", reason="spam", chat_id=message.chat.id)
                            bot.reply_to(message, f"⚠️ {message.from_user.first_name}, это считается спамом — вы получили предупреждение.")
                        else:
                            seconds = apply_escalating_mute(message.chat.id, user_id)
                            if seconds == 0:
                                bot.reply_to(message, f"🚫 {message.from_user.first_name} забанен навсегда.")
                            elif seconds:
                                hrs = seconds // 3600
                                bot.reply_to(message, f"⚠️ {message.from_user.first_name}, слишком много сообщений! Мут на {hrs} часов.")
                        user_messages[user_id] = []
                        return
                except Exception:
                    pass
    except Exception:
        pass

    # Проверка на мат/запрещённые слова
    try:
        text_lower = (message.text or "").lower()
        if any(bw.lower() in text_lower for bw in banned_words):
            if message.chat.type == "private":
                add_warning_for(user_id, by="auto", reason="profanity_private")
                bot.reply_to(message, f"⛔ {message.from_user.first_name}, запрещённые слова в личке — предупреждение.")
            else:
                try:
                    uid_str = str(user_id)
                    has_history = (int(mute_history.get(uid_str, {}).get("count", 0)) > 0) or any((int(tb.get("user_id")) == user_id) for tb in temp_bans)
                    if not has_history:
                        add_warning_for(user_id, by="auto", reason="profanity", chat_id=message.chat.id)
                        bot.reply_to(message, f"⛔ {message.from_user.first_name}, запрещённые слова — предупреждение.")
                    else:
                        seconds = apply_escalating_mute(message.chat.id, user_id)
                        if seconds == 0:
                            bot.reply_to(message, f"🚫 {message.from_user.first_name} забанен навсегда.")
                        elif seconds:
                            hrs = seconds // 3600
                            bot.reply_to(message, f"⛔ {message.from_user.first_name}, запрещённые слова! Мут на {hrs} часов.")
                except Exception:
                    pass
    except Exception:
        pass

    # Сохраняем короткую историю сообщений
    try:
        with open('user_messages.json', 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in user_messages.items()}, f, ensure_ascii=False)
    except Exception:
        pass

    # Если есть активный приватный блок — не начисляем
    try:
        blocked_until = private_spam_blocks.get(uid, 0)
        if message.chat.type == "private" and blocked_until and time.time() < blocked_until:
            rem = int(blocked_until - time.time())
            mins = rem // 60
            bot.reply_to(message, f"❌ Начисления временно отключены. Подождите {mins} мин.")
            return
    except Exception:
        pass

    # Начисляем монеты и XP
    try:
        add_coins(user_id, 1)
    except Exception:
        pass

    try:
        level_up, new_level, total_xp = add_xp(user_id, message.from_user.username or message.from_user.first_name, amount=5)
        if level_up:
            bot.reply_to(message, f"🎉 {message.from_user.first_name} повысил уровень до {new_level}! (Всего XP: {total_xp})")
    except Exception:
        pass

def add_xp_with_rewards(user_id, username, amount=5):
    level_up, new_level, total_xp = add_xp(user_id, username, amount)
    if level_up:
        reward = new_level * 10 
        add_coins(user_id, reward)
        bot.send_message(user_id, f"🎉 Поздравляем! Вы достигли уровня {new_level} и получили {reward} монет!")
    return level_up, new_level, total_xp

def send_days_to_summer(chat_id, topic_id):
    today = datetime.date.today()
    next_summer = datetime.date(today.year, 6, 1)
    if today > next_summer:
        next_summer = datetime.date(today.year + 1, 6, 1)
    days_left = (next_summer - today).days

    bot.send_message(
        chat_id=chat_id,
        text=f"🌞 До лета осталось {days_left} дней! Ожидаем...",
        message_thread_id=topic_id 
    )
    
def schedule_daily_message(chat_id, topic_id):
    def task():
        while True:
            now = datetime.datetime.now()
            target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
            if now > target_time:
                target_time += datetime.timedelta(days=1)
            time_to_wait = (target_time - now).total_seconds()
            time.sleep(time_to_wait)
            send_days_to_summer(chat_id, topic_id)

    threading.Thread(target=task, daemon=True).start()

# ====== Глобальная активность ======
@bot.message_handler(commands=["globalactivity"])
def cmd_globalactivity(message):
    if not activity_data:
        bot.reply_to(message, "📊 Пока нет данных об активности.")
        return

    totals = []
    for uid, data in activity_data.items():
        total_msgs = data.get("all", {}).get("messages", 0)
        # Получаем юзернейм или имя
        username = data.get("username")
        if username:
            name = f"@{username}"
        else:
            name = data.get("first_name") or f"ID:{uid}"
        # XP и уровень (если есть)
        xp_entry = xp_data.get(str(uid), {})
        xp = xp_entry.get("xp", 0)
        level = xp_entry.get("level", 1)
        totals.append((name, total_msgs, xp, level))

    totals.sort(key=lambda x: x[1], reverse=True)
    top_list = totals[:5]

    text = "🏆 Топ-5 самых активных:\n\n"
    for i, (name, count, xp, level) in enumerate(top_list, start=1):
        text += f"{i}. {name} — {count} сообщений — XP: {xp} — Уровень: {level}\n"

    bot.send_message(message.chat.id, text)
# ====== Команда для получения ID темы ======
@bot.message_handler(commands=['getid'])
def get_topic_id(message):
    bot.reply_to(
        message,
        f"Chat ID: {message.chat.id}\nTopic ID: {message.message_thread_id}"
    )
# =============== ЛОГ МЕССЕДЖЕЙ ДЛЯ АКТИВНОСТИ ===============
def _log_message_activity(message):
    user_id = str(message.from_user.id)
    chat_id = str(message.chat.id)

    if user_id not in activity_data:
        activity_data[user_id] = {
            "all": {"messages": 0},
            "chats": {}
        }

    activity_data[user_id]["all"]["messages"] += 1

    if chat_id not in activity_data[user_id]["chats"]:
        activity_data[user_id]["chats"][chat_id] = {"messages": 0}
    activity_data[user_id]["chats"][chat_id]["messages"] += 1

    # безопасное сохранение
    save_activity()

def unmute_user(chat_id, user_id):
    try:
        bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            ),
            until_date=0
        )
        bot.send_message(chat_id, f"🔊 Мут снят с пользователя ID {user_id}.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Не удалось снять мут: <code>{e}</code>")

# =============== ОСНОВНЫЕ КОМАНДЫ ===============
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message, "👋 Привет! Я бот группы. Введи /help, чтобы увидеть список команд.")

@bot.message_handler(commands=['help', 'commands'])
def cmd_help(message):
    cmds = [
        "<b>Общее</b>",
        "/start – начать",
        "/help – список команд",
        "/pay @username (количество) – перевести монеты пользователю",
        "/rules – правила",
        "/lessons [день] – расписание уроков (Пн/Вт/.. или полное имя)",
        "/homework [день] – показать ДЗ (в группе). В ЛС админ задаёт ДЗ: /homework [день] [текст]",
        "/activity – показать свою активность",
        "/activity [ответ] – показать активность другого пользователя",
        "/globalactivity – показать топ-5 активности",
        "/level - показывает ваш уровень",
        "/daily - ежедневная награда",
        "/shop - Открыть магазин",
        "/privateblocks - показать активные блокировки начислений (только админ)",
        "/unblockprivate [user_id] - снять блокировку начислений (только админ)",
        "/appeal - отправить апелляцию (в ЛС боту)",
        "",
        "<b>Модерация (только админы)</b>",
        "/ban [время] – бан по ответу на сообщение (30m/2h/1d), по умолчанию 1h",
        "/mute [время] – мут по ответу (30m/2h/1d), по умолчанию 1h",
        "/unmute – снять мут по ответу",
        "/warn @username [причина] – предупреждение",
        "/clearwarns @username – очистить предупреждения",
        "/warnslist @username – показать количество предупреждений",
        "",
        "<b>Жалобы</b>",
        "/report [жалоба] – отправить жалобу (только в ЛС боту). Жалобы сохраняются."
        ,
        "",
        "<b>Примечание по покупкам</b>",
        "Покупка ролей в магазине НЕ предоставляет права автоматически — выдача должностей вручную админом.",
    ]

    bot.send_message(
        message.chat.id,
        "\n".join(cmds),
        parse_mode="HTML"
    )

poll_data = {"question": "", "options": [], "votes": {}}

@bot.message_handler(commands=["shopstars"])
def shop_stars(message):
    markup = types.InlineKeyboardMarkup(row_width=1)

    for key, item in STAR_SHOP.items():
        markup.add(
            types.InlineKeyboardButton(
                f"💰 {item['coins']} монет — ⭐ {item['stars']}",
                callback_data=f"buystar_{key}"
            )
        )

    bot.send_message(
        message.chat.id,
        "⭐ Покупка монет за Telegram Stars:",
        reply_markup=markup
    )

@bot.message_handler(commands=['poll'])
def create_poll(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может создавать голосования.")
        return

    parts = message.text.split("\n")
    if len(parts) < 3:
        bot.reply_to(message, "❗ Используйте: /poll [вопрос]\n[вариант 1]\n[вариант 2]\n...")
        return

    question = parts[0][6:]  # Убираем "/poll "
    options = parts[1:]

    # Создаём кнопки для голосования
    markup = types.InlineKeyboardMarkup()
    for i, option in enumerate(options):
        markup.add(types.InlineKeyboardButton(option, callback_data=f"vote_{i}"))

    # Отправляем сообщение с голосованием
    bot.send_message(message.chat.id, f"📊 {question}", reply_markup=markup)

    # Сохраняем данные о голосовании
    poll_data["question"] = question
    poll_data["options"] = options
    poll_data["votes"] = {i: [] for i in range(len(options))}  # Инициализация голосов
    
    # =============== АКТИВНОСТЬ ===============
@bot.message_handler(commands=['activity'])
def cmd_activity(message):
    user_id = str(message.from_user.id)
    user_data = activity_data.get(user_id)
    if not user_data:
        bot.reply_to(message, "📊 У вас пока нет активности.")
        return
    count = user_data["all"]["messages"]
    bot.reply_to(message, f"📊 Ваша активность: {count} сообщений.")

@bot.message_handler(commands=["globalactivity"])
def cmd_globalactivity(message):
    if not activity_data:
        bot.reply_to(message, "📊 Пока нет данных об активности.")
        return

    totals = []
    for uid, data in activity_data.items():
        total_msgs = data.get("all", {}).get("messages", 0)
        name = data.get("username") or data.get("first_name") or f"ID:{uid}"
        totals.append((name, total_msgs))

    totals.sort(key=lambda x: x[1], reverse=True)
    top_list = totals[:5]

    text = "🏆 Топ-5 самых активных:\n\n"
    for i, (name, count) in enumerate(top_list, start=1):
        text += f"{i}. {name} — {count} сообщений\n"

    bot.send_message(message.chat.id, text)

poll_data = {"question": "", "options": [], "votes": {}}

@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
    _, poll_id, option_index = call.data.split("_")
    poll_id = int(poll_id)
    option_index = int(option_index)

    if poll_id not in polls:
        bot.answer_callback_query(call.id, "❌ Это голосование уже завершено.")
        return

    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    # Проверяем, голосовал ли пользователь ранее
    for voters in polls[poll_id]["votes"].values():
        if user_id in voters:
            bot.answer_callback_query(call.id, "❌ Вы уже проголосовали!")
            return

    # Регистрируем голос
    polls[poll_id]["votes"][option_index].append(user_id)

    # Обновляем текст кнопки с количеством голосов
    markup = types.InlineKeyboardMarkup()
    for i, option in enumerate(polls[poll_id]["options"]):
        vote_count = len(polls[poll_id]["votes"][i])
        markup.add(types.InlineKeyboardButton(f"{option} ({vote_count})", callback_data=f"vote_{poll_id}_{i}"))

    bot.edit_message_reply_markup(
        chat_id=polls[poll_id]["chat_id"],
        message_id=poll_id,
        reply_markup=markup
    )

    # Уведомляем пользователя
    bot.answer_callback_query(call.id, "✅ Ваш голос учтён!")

    # Отправляем уведомление владельцу бота
    bot.send_message(
        OWNER_ID,
        f"🗳 Пользователь {username} проголосовал за вариант: {polls[poll_id]['options'][option_index]}"
    )
    
@bot.message_handler(commands=['results'])
def show_results(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может просматривать результаты.")
        return

    if not poll_data["question"]:
        bot.reply_to(message, "❌ Сейчас нет активного голосования.")
        return

    # Формируем текст с результатами
    results_text = f"📊 Результаты голосования: {poll_data['question']}\n\n"
    for i, option in enumerate(poll_data["options"]):
        votes_count = len(poll_data["votes"][i])
        results_text += f"{option}: {votes_count} голос(ов)\n"

    bot.reply_to(message, results_text)
    
@bot.message_handler(commands=['resetpool'])
def reset_poll(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может сбросить голосование.")
        return

    poll_data.clear()
    poll_data.update({"question": "", "options": [], "votes": {}})
    bot.reply_to(message, "✅ Голосование сброшено.")

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    rules_text = (
        "📌 <b>Правила чата</b>:\n"
        "1) Без спама - мут 1 час\n"
        "2) Без Оскорблений/матов - мут 1 час\n"
        "3) Не обижать - мут 30 минут\n"
        "4) Уважение к участникам\n"
        "5) Без 18+ - мут 3 дня\n"
        "6) Следовать указаниям админов\n"
        "7) Не рекламировать - бан 1 день\n"
        "8) Без политики - мут 1 день\n"
        "9) Соблюдать тему чата\n"
    )
    bot.reply_to(message, rules_text, parse_mode="HTML")


# ===== КОМАНДА /messege (ТОЛЬКО ДЛЯ ТЕБЯ) =====
OWNER_ID = 5782683757   # твой Telegram ID
CHAT_ID = -1002241393389  # ID школьного чата

@bot.message_handler(commands=['messege'])
def send_message_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "⛔ Эта команда только для владельца.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ Используй: /messege ТЕКСТ")
        return

    text = parts[1]
    try:
        bot.send_message(
            chat_id=CHAT_ID,
            text=f"📢 Сообщение от @RBXTelega1:\n\n{text}",
        )
        bot.reply_to(message, "✅ Сообщение отправлено в чат.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

# =============== РАСПИСАНИЕ УРОКОВ ===============
schedule_dict = {
    "пн": "\n 1: 9:00 - 9:45\n 2: 10:05 - 10:50 \n 3: 11:10 - 11:55\n 4: 12:15 - 13:00\n 5: 13:20 - 14:05\n 6: 14:25 - 15:10",
    "вт": "\n 1: 9:00 - 9:45\n 2: 10:05 - 10:50 \n 3: 11:10 - 11:55\n 4: 12:15 - 13:00\n 5: 13:20 - 14:05\n 6: 14:25 - 15:10",
    "ср": "\n 1: 9:00 - 9:45\n 2: 10:05 - 10:50 \n 3: 11:10 - 11:55\n 4: 12:15 - 13:00\n 5: 13:20 - 14:05\n 6: 14:25 - 15:10",
    "чт": "\n Пока что нету",
    "пт": "\n Пока что нету",
    "сб": "Выходной",
    "вс": "Выходной",
    # Полные названия тоже поддержим
    "понедельник": "Пока что нету",
    "вторник": "Пока что нету",
    "среда": "Пока что нету",
    "четверг": "Пока что нету",
    "пятница": "Пока что нету",
    "суббота": "Выходной",
    "воскресенье": "Выходной",
}

@bot.message_handler(commands=['lessons'])
def cmd_lessons(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        # показать всё (по коротким дням)
        text = "📚 Расписание уроков:\n"
        for day in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]:
            text += f"{day}: {schedule_dict[day.lower()]}\n"
        bot.reply_to(message, text)
        return

    day_raw = parts[1].strip().lower()
    key = day_raw[:2] if day_raw[:2] in schedule_dict else day_raw
    val = schedule_dict.get(key)
    if val is None:
        bot.reply_to(message, "❗ Неизвестный день. Используй: Пн, Вт, Ср, Чт, Пт, Сб, Вс или полное имя дня.")
    else:
        pretty = day_raw.capitalize()
        bot.reply_to(message, f"📚 Расписание на {pretty}: {val}")

WARN_FILE = "warns.json"

def load_warns():
    if os.path.exists(WARN_FILE):
        try:
            with open(WARN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_warns(data):
    try:
        with open(WARN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении предупреждений: {e}")

warnings = load_warns()  # { user_id(str): [ts, ...] }

# ===== История мутов для эскалации =====
MUTE_HISTORY_FILE = "mute_history.json"

def load_mute_history():
    if os.path.exists(MUTE_HISTORY_FILE):
        try:
            with open(MUTE_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_mute_history(data):
    try:
        with open(MUTE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении mute_history: {e}")

mute_history = load_mute_history()  # { user_id(str): {"count": int, "last_reset": ts} }

# Эскалация: 1ч,2ч,4ч,8ч,24ч,48ч,1нед -> потом бан
ESCALATION_SECONDS = [3600, 2*3600, 4*3600, 8*3600, 24*3600, 48*3600, 7*24*3600]
ESCALATION_RESET_SECONDS = 7*24*3600

def _get_mute_count_and_maybe_reset(uid_str):
    entry = mute_history.get(uid_str, {})
    last_reset = int(entry.get("last_reset", 0))
    now = int(time.time())
    if last_reset == 0 or now - last_reset > ESCALATION_RESET_SECONDS:
        # reset
        mute_history[uid_str] = {"count": 0, "last_reset": now}
        save_mute_history(mute_history)
        return 0
    return int(entry.get("count", 0))

def _increment_mute_count(uid_str):
    now = int(time.time())
    entry = mute_history.get(uid_str, {"count": 0, "last_reset": now})
    # if last_reset too old, reset
    if now - int(entry.get("last_reset", now)) > ESCALATION_RESET_SECONDS:
        entry = {"count": 0, "last_reset": now}
    entry["count"] = int(entry.get("count", 0)) + 1
    entry["last_reset"] = int(entry.get("last_reset", now))
    mute_history[uid_str] = entry
    save_mute_history(mute_history)
    return int(entry["count"])

def apply_escalating_mute(chat_id, user_id, by_admin=None, reason=None, seconds_override=None):
    uid_str = str(user_id)
    # If override specified (admin manual mute or warn-trigger), use it
    if seconds_override:
        seconds = int(seconds_override)
        try:
            bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=int(time.time()) + seconds
            )
            # schedule unmute
            def _unmute():
                time.sleep(seconds)
                unmute_user(chat_id, user_id)
            threading.Thread(target=_unmute, daemon=True).start()
            return seconds
        except Exception as e:
            print(f"Ошибка при применении override мута: {e}")
            return None

    # otherwise escalation based on history
    count = _get_mute_count_and_maybe_reset(uid_str)
    # choose next index
    idx = min(count, len(ESCALATION_SECONDS)-1)
    seconds = ESCALATION_SECONDS[idx]
    # if count beyond escalation -> permanent ban
    try:
        if count >= len(ESCALATION_SECONDS):
            # permanent ban
            bot.ban_chat_member(chat_id, user_id)
            # record temp ban? add to temp_bans as permanent marker (until 0)
            temp_entry = {"chat_id": chat_id, "user_id": user_id, "until": 0}
            try:
                temp_bans.append(temp_entry)
                save_temp_bans(temp_bans)
            except Exception:
                pass
            return 0
        else:
            bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=int(time.time()) + seconds
            )
            # increment history
            _increment_mute_count(uid_str)
            # schedule unmute
            def _unmute2():
                time.sleep(seconds)
                unmute_user(chat_id, user_id)
            threading.Thread(target=_unmute2, daemon=True).start()
            return seconds
    except Exception as e:
        print(f"Ошибка при применении эскалируемого мута: {e}")
        return None

# ===== Предупреждения (авто и ручные) =====
def _prune_warns_for(uid_str):
    # keep only warnings from last 30 days
    now = int(time.time())
    month_seconds = 30*24*3600
    arr = warnings.get(uid_str, [])
    arr = [int(t) for t in arr if now - int(t) <= month_seconds]
    warnings[uid_str] = arr
    save_warns(warnings)
    return len(arr)

def add_warning_for(uid, by="auto", reason=None, chat_id=None):
    uid_str = str(uid)
    now = int(time.time())
    arr = warnings.get(uid_str, [])
    arr.append(now)
    warnings[uid_str] = arr
    save_warns(warnings)
    count = _prune_warns_for(uid_str)
    # notify user
    try:
        bot.send_message(uid, f"⚠️ Вы получили предупреждение. Причина: {reason or 'Нарушение правил'}. (Всего: {count})")
    except Exception:
        pass
    # if more than 3 warnings -> mute 30 minutes
    if count > 3 and chat_id:
        apply_escalating_mute(chat_id, uid, by_admin=None, reason="auto_warnes_exceeded", seconds_override=30*60)
    return count

def clear_warnings_for_uid(uid):
    uid_str = str(uid)
    if uid_str in warnings:
        warnings[uid_str] = []
        save_warns(warnings)

def get_warnings_count(uid):
    uid_str = str(uid)
    return _prune_warns_for(uid_str)


# =============== /balance ================
@bot.message_handler(commands=["balance", "coins"])
def cmd_balance(message):
    user_id = message.from_user.id
    balance = get_user_balance(user_id)  # Используем новую функцию
    bot.reply_to(message, f"💰 Ваш баланс: {balance} монет.")


def _casino_win_chance(bet: int) -> float:
    """Чем больше ставка, тем меньше шанс победы."""
    if bet <= 1000:
        return 0.45
    if bet <= 5000:
        return 0.38
    if bet <= 10000:
        return 0.32
    if bet <= 25000:
        return 0.25
    if bet <= 50000:
        return 0.19
    if bet <= 100000:
        return 0.14
    return 0.10


def _casino_retry_markup(bet: int):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔁 Еще раз", callback_data=f"casino_retry_{bet}"))
    return markup


def _play_casino_round(message, user_id: int, bet: int):
    if bet <= 0:
        bot.reply_to(message, "❌ Ставка должна быть больше нуля.")
        return

    min_bet = 100
    max_bet = 500000
    if bet < min_bet:
        bot.reply_to(message, f"❌ Минимальная ставка: {min_bet} монет.")
        return
    if bet > max_bet:
        bot.reply_to(message, f"❌ Максимальная ставка: {max_bet} монет.")
        return

    balance = get_user_balance(user_id)
    if balance < bet:
        bot.reply_to(message, f"❌ Недостаточно монет. Ваш баланс: {balance}.")
        return

    try:
        remove_coins(user_id, bet)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка списания ставки: {e}")
        return

    chance = _casino_win_chance(bet)
    markup = _casino_retry_markup(bet)
    if random.random() < chance:
        win_amount = bet * 2
        add_coins(user_id, win_amount, bypass_block=True)
        new_balance = get_user_balance(user_id)
        bot.reply_to(
            message,
            f"🎉 Вы выиграли!\n"
            f"Ставка: {bet}\n"
            f"Выигрыш: {win_amount}\n"
            f"Шанс победы: {int(chance * 100)}%\n"
            f"Новый баланс: {new_balance}",
            reply_markup=markup
        )
    else:
        new_balance = get_user_balance(user_id)
        bot.reply_to(
            message,
            f"💥 Вы проиграли ставку.\n"
            f"Ставка: {bet}\n"
            f"Шанс победы: {int(chance * 100)}%\n"
            f"Новый баланс: {new_balance}",
            reply_markup=markup
        )


@bot.message_handler(commands=["casino"])
def cmd_casino(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(
            message,
            "🎰 Используйте: /casino [ставка]\nПример: /casino 5000"
        )
        return

    try:
        bet = int(parts[1].strip())
    except Exception:
        bot.reply_to(message, "❌ Ставка должна быть целым числом.")
        return

    user_id = message.from_user.id
    _play_casino_round(message, user_id, bet)


@bot.callback_query_handler(func=lambda call: call.data.startswith("casino_retry_"))
def callback_casino_retry(call):
    user_id = call.from_user.id
    try:
        bet = int(call.data.split("_")[-1])
    except Exception:
        bot.answer_callback_query(call.id, "Некорректная ставка.")
        return

    bot.answer_callback_query(call.id, "Пробуем еще раз...")
    _play_casino_round(call.message, user_id, bet)


@bot.message_handler(commands=["casinoinfo"])
def cmd_casino_info(message):
    text = (
        "🎰 Правила казино\n\n"
        "Команда: /casino [ставка]\n"
        "При победе вы получаете x2 от ставки.\n"
        "При проигрыше ставка сгорает.\n\n"
        "📉 Шансы победы:\n"
        "100 - 1 000: 45%\n"
        "1 001 - 5 000: 38%\n"
        "5 001 - 10 000: 32%\n"
        "10 001 - 25 000: 25%\n"
        "25 001 - 50 000: 19%\n"
        "50 001 - 100 000: 14%\n"
        "100 001+: 10%\n\n"
        "Лимиты ставки: от 100 до 500000 монет."
    )
    bot.reply_to(message, text)


def find_user_by_username(username: str):
    """Ищет user_id по username (без @) в activity_data. Возвращает int id или None."""
    if not username:
        return None
    uname = username.lstrip("@")
    for uid_str, data in activity_data.items():
        try:
            if data and data.get("username") and data.get("username").lower() == uname.lower():
                return int(uid_str)
        except Exception:
            continue
    return None


@bot.message_handler(commands=['pay'])
def cmd_pay(message):
    """Перевести монеты другому пользователю.

    Поддерживается:
    - ответ на сообщение: /pay 100
    - упоминание: /pay @username 100
    - id: /pay 123456789 100
    """
    parts = message.text.split()
    sender_id = message.from_user.id

    # Если команда — ответ на сообщение: ожидаем /pay amount
    if message.reply_to_message:
        if len(parts) < 2:
            bot.reply_to(message, "✍️ Используйте: ответ на сообщение -> /pay [количество]")
            return
        try:
            amount = int(parts[1])
        except Exception:
            bot.reply_to(message, "❗ Неверная сумма. Используйте целое число.")
            return
        if amount <= 0:
            bot.reply_to(message, "❗ Сумма должна быть положительной.")
            return
        target_id = message.reply_to_message.from_user.id

    else:
        # ожидаем: /pay @username amount  или /pay user_id amount
        if len(parts) < 3:
            bot.reply_to(message, "✍️ Используйте: /pay @username (количество) или ответом на сообщение: /pay (количество)")
            return
        target_raw = parts[1]
        try:
            amount = int(parts[2])
        except Exception:
            bot.reply_to(message, "❗ Неверная сумма. Используйте целое число.")
            return
        if amount <= 0:
            bot.reply_to(message, "❗ Сумма должна быть положительной.")
            return

        # определяем target_id
        if target_raw.startswith("@"):
            target_id = find_user_by_username(target_raw)
            if target_id is None:
                bot.reply_to(message, "❌ Не удалось найти пользователя по нику. Попросите пользователя написать боту хотя бы одно сообщение.")
                return
        else:
            # возможно числовой id
            try:
                target_id = int(target_raw)
            except Exception:
                bot.reply_to(message, "❌ Неверный формат получателя. Используйте @username или user_id.")
                return

    # Защита от перевода себе
    if target_id == sender_id:
        bot.reply_to(message, "❗ Нельзя переводить монеты самому себе.")
        return

    sender_balance = get_user_balance(sender_id)
    if sender_balance < amount:
        bot.reply_to(message, f"❌ Недостаточно монет. Ваш баланс: {sender_balance}.")
        return

    try:
        remove_coins(sender_id, amount)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка списания: {e}")
        return

    # При переводе обходиm проверку приватного блока у получателя
    added = add_coins(target_id, amount, bypass_block=True)
    if not added:
        # если по каким-то причинам не удалось добавить — вернуть деньги
        add_coins(sender_id, amount, bypass_block=True)
        bot.reply_to(message, "⚠️ Не удалось зачислить монеты получателю. Сумма возвращена.")
        return

    # Уведомления
    bot.reply_to(message, f"✅ Вы перевели {amount} монет пользователю (ID:{target_id}).")
    try:
        bot.send_message(target_id, f"💸 Вам перевели {amount} монет от {message.from_user.first_name} (ID:{sender_id}).")
    except Exception:
        pass

@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    # support: reply -> /warn [reason], or /warn @username reason
    parts = message.text.split(maxsplit=2)
    target_id = None
    reason = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        reason = parts[1] if len(parts) > 1 else None
    else:
        if len(parts) < 3:
            bot.reply_to(message, "✍️ Используй: /warn @username [причина] или ответом на сообщение")
            return
        target_raw = parts[1]
        reason = parts[2]
        # try username or id
        try:
            target_id = int(target_raw)
        except Exception:
            target_id = find_user_by_username(target_raw)
            if target_id is None:
                bot.reply_to(message, "❌ Пользователь не найден. Используйте @username или ответьте на сообщение.")
                return

    count = add_warning_for(target_id, by=message.from_user.id, reason=reason, chat_id=message.chat.id)
    bot.reply_to(message, f"⚠️ Пользователь получил предупреждение. Всего предупреждений за 30 дней: {count}.")

@bot.message_handler(commands=['clearwarns'])
def cmd_clearwarns(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    parts = message.text.split(maxsplit=1)
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        if len(parts) < 2:
            bot.reply_to(message, "✍️ Используй: /clearwarns @username или ответом на сообщение")
            return
        target_raw = parts[1]
        try:
            target_id = int(target_raw)
        except Exception:
            target_id = find_user_by_username(target_raw)
            if target_id is None:
                bot.reply_to(message, "❌ Пользователь не найден.")
                return
    clear_warnings_for_uid(target_id)
    bot.reply_to(message, f"✅ Предупреждения очищены для пользователя (ID:{target_id}).")

@bot.message_handler(commands=["myrole"])
def my_role(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    roles = load_roles()
    key = f"{chat_id}:{user_id}"

    if key not in roles:
        bot.reply_to(message, "❌ У вас нет активной роли.")
        return

    data = roles[key]

    if data["expire"] == 0:
        bot.reply_to(message, f"🎭 Ваша роль: {data['role']}\n⏳ Срок: навсегда")
        return

    seconds = data["expire"] - int(time.time())
    if seconds < 0:
        seconds = 0

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    bot.reply_to(
        message,
        f"🎭 Ваша роль: {data['role']}\n"
        f"⏳ Осталось: {days}д {hours}ч {minutes}м"
    )

@bot.message_handler(commands=['warnslist'])
def cmd_warnslist(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    parts = message.text.split(maxsplit=1)
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        if len(parts) < 2:
            bot.reply_to(message, "✍️ Используй: /warnslist @username или ответом на сообщение")
            return
        target_raw = parts[1]
        try:
            target_id = int(target_raw)
        except Exception:
            target_id = find_user_by_username(target_raw)
            if target_id is None:
                bot.reply_to(message, "❌ Пользователь не найден.")
                return
    count = get_warnings_count(target_id)
    bot.reply_to(message, f"ℹ️ У пользователя (ID:{target_id}) сейчас {count} предупреждение(й) за последние 30 дней.")

# =============== ЖАЛОБЫ (с сохранением) ===============
COMPLAINTS_FILE = "complaints.txt"

@bot.message_handler(commands=['report'])
def cmd_report(message):
    # жалобы только в ЛС
    if message.chat.type != "private":
        bot.reply_to(message, "❗ Жалобы можно отправлять только в ЛС боту.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Используй: /report [текст жалобы]\n<b>как правльно оформить жалобу<b>\nесли у вас жалоба на сообщение, следуйте инструкции:\n1. зажмите это сообщение\n2. скопируйте ссылку на сообщение\nправильное фофрмление: /report [ссылка на сообщение] [причина]\n\n <b>жалоба на пользователя<b>\nесли вы хотите пожаловатся на пользователя, пишите так: \n/report @username [причина]\n\n обязательно после /report пишите хэштег:\n#user - жалоба на пользователя\n #message - жалоба на сообщение", parse_mode="Markdown")
        return

    complaint = parts[1]
    text = (
        f"🚨 <b>Жалоба</b>\n"
        f"От: @{message.from_user.username or 'без_ника'}\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"Текст: {complaint}"
    )

    # сохраняем в файл
    try:
        with open(COMPLAINTS_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Не удалось сохранить жалобу: {e}")
        return

    # отправляем админам
    try:
        bot.send_message(ADMIN_CHAT_ID, text)
        bot.reply_to(message, "✅ Жалоба отправлена администраторам и сохранена.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при отправке жалобы админам: {e}")

# =============== АПЕЛЛЯЦИИ ===============
APPEALS_FILE = "appeals.json"

def load_appeals():
    if os.path.exists(APPEALS_FILE):
        try:
            with open(APPEALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_appeals(arr):
    try:
        with open(APPEALS_FILE, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении апелляций: {e}")

@bot.message_handler(commands=['appeal'])
def cmd_appeal(message):
    # апелляции — только в ЛС боту
    if message.chat.type != "private":
        bot.reply_to(message, "❗ Апелляции принимаются только в личных сообщениях боту.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Используй: /appeal [текст апелляции]")
        return
    text = parts[1]
    entry = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "text": text,
        "time": int(time.time())
    }
    arr = load_appeals()
    arr.append(entry)
    save_appeals(arr)
    # уведомляем админа/владельца
    try:
        bot.send_message(ADMIN_CHAT_ID, f"📩 Апелляция от @{message.from_user.username or message.from_user.first_name} (ID:{message.from_user.id}):\n{text}")
    except Exception:
        pass
    bot.reply_to(message, "✅ Ваша апелляция отправлена. Администраторы свяжутся с вами.")

# =============== ДОМАШНЕЕ ЗАДАНИЕ (сохранение по дням) ===============
HOMEWORK_FILE = "homework.json"

def load_homework():
    if os.path.exists(HOMEWORK_FILE):
        try:
            with open(HOMEWORK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    # структура: { "понедельник": "текст...", ... }
    return {}

def save_homework(data: dict):
    try:
        with open(HOMEWORK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Не удалось сохранить homework.json:", e)

homework_data = load_homework()

days_full = {
    "понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3,
    "пятница": 4, "суббота": 5, "воскресенье": 6
}
days_short_to_full = {
    "пн": "понедельник", "вт": "вторник", "ср": "среда",
    "чт": "четверг", "пт": "пятница", "сб": "суббота", "вс": "воскресенье"
}

def normalize_day_name(s: str):
    """Принимает 'Пн'/'понедельник' и возвращает полное название дня ('понедельник') или None."""
    if not s:
        return None
    s = s.strip().lower()
    if s in days_full:
        return s
    short = s[:2]
    return days_short_to_full.get(short)

@bot.message_handler(commands=['homework'])
def cmd_homework(message):
    global homework_data

    args = message.text.split(maxsplit=2)

    if message.chat.type == "private":
        # Только конкретный админ может задавать ДЗ в ЛС
        if message.from_user.id != ADMIN_USER_ID:
            bot.reply_to(message, "❌ Только админ может задавать домашнее задание в личке.")
            return

        if len(args) < 3:
            bot.reply_to(message, "✍️ В ЛС используйте: /homework [день] [задание]\nНапр.: /homework понедельник параграф 12, упр. 5")
            return

        day_full = normalize_day_name(args[1])
        if not day_full:
            bot.reply_to(message, "⚠️ Неверный день. Пример: понедельник / вт / ср / четверг / ...")
            return

        task = args[2].strip()
        # На каждый день хранится одно задание: просто перезаписываем
        homework_data[day_full] = task
        save_homework(homework_data)
        bot.reply_to(message, f"✅ Домашнее задание на <b>{day_full}</b> обновлено:\n{task}", parse_mode="HTML")
        return

    # В группе — показ ДЗ
    if len(args) == 1:
        # без аргументов — показать ДЗ на сегодня
        today_idx = datetime.datetime.today().weekday()  # 0..6
        # ищем по индексу полное название
        day_full = [k for k, v in days_full.items() if v == today_idx][0]
    else:
        day_full = normalize_day_name(args[1])
        if not day_full:
            bot.reply_to(message, "⚠️ Неверный день. Пример: /homework вт  или  /homework четверг")
            return

    task = homework_data.get(day_full, "На этот день задания нет.")
    bot.reply_to(message, f"📚 Домашнее задание на <b>{day_full}</b>:\n{task}")

# =============== БАН / МУТ / РАЗМУТ (ТОЛЬКО АДМИНЫ) ===============
@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Используй команду <b>ответом</b> на сообщение пользователя. Пример: /ban 2h")
        return

    parts = message.text.split(maxsplit=1)
    seconds = parse_time_to_seconds(parts[1]) if len(parts) > 1 else 3600
    if seconds is None:
        bot.reply_to(message, "❗ Неверный формат времени. Пример: 30m, 2h, 1d")
        return

    target_id = message.reply_to_message.from_user.id
    if has_immunity(target_id):
        name = getattr(message.reply_to_message.from_user, 'first_name', str(target_id))
        bot.reply_to(message, f"🛡 {name} избежал бана иммунитетом!")
        return

    try:
        bot.ban_chat_member(message.chat.id, target_id, until_date=int(time.time()) + seconds)
        bot.reply_to(message, f"🚫 Пользователь забанен на {parts[1] if len(parts) > 1 else '1h'}.")
        # Если бан временный — сохраняем и планируем автоматический разбан
        if seconds and seconds > 0:
            try:
                until_ts = int(time.time()) + seconds
                # Добавляем запись в temp_bans и сохраняем
                entry = {"chat_id": message.chat.id, "user_id": target_id, "until": until_ts}
                try:
                    temp_bans.append(entry)
                except NameError:
                    temp_bans = [entry]
                try:
                    with open(TEMP_BANS_FILE, "w", encoding="utf-8") as f:
                        json.dump(temp_bans, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                schedule_unban_for(entry)
            except Exception as e:
                print(f"Ошибка при планировании временного бана: {e}")
    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось забанить: <code>{e}</code>")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Используй команду <b>ответом</b> на сообщение. Пример: /mute 30m", parse_mode="HTML")
        return

    parts = message.text.split(maxsplit=1)
    seconds = parse_time_to_seconds(parts[1]) if len(parts) > 1 else 3600
    if seconds is None:
        bot.reply_to(message, "❗ Неверный формат времени. Пример: 30m, 2h, 1d")
        return

    target_id = message.reply_to_message.from_user.id
    # Проверка иммунитета к муту (и бану) — если есть, отменяем операцию
    if has_immunity(target_id):
        name = getattr(message.reply_to_message.from_user, 'first_name', str(target_id))
        bot.reply_to(message, f"🛡 {name} избежал мута иммунитетом!")
        return

    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=int(time.time()) + seconds
        )
        # учитываем в истории мутов (для эскалации)
        try:
            _increment_mute_count(str(target_id))
        except Exception:
            pass
        bot.reply_to(message, f"🔇 Пользователь замьючен на {parts[1] if len(parts)>1 else '1h'}.")

        # Запускаем таймер для автоматического снятия мута
        def unmute_later():
            time.sleep(seconds)
            unmute_user(message.chat.id, target_id)
        threading.Thread(target=unmute_later, daemon=True).start()

    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось замутить: <code>{e}</code>")

@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message):
    payload = message.successful_payment.invoice_payload
    product = STAR_SHOP.get(payload)

    if not product:
        return

    user_id = message.from_user.id
    coins = product["coins"]

    add_coins(user_id, coins, bypass_block=True)

    bot.send_message(
        user_id,
        f"✅ Оплата прошла успешно!\n"
        f"💰 Вам начислено {coins} монет."
    )

    # Уведомление тебе (владельцу)
    bot.send_message(
        OWNER_ID,
        f"⭐ Оплата Stars\n"
        f"👤 {message.from_user.first_name} (@{message.from_user.username})\n"
        f"💰 {coins} монет\n"
        f"⭐ {product['stars']} звёзд"
    )

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        bot.send_message(
            message.chat.id,
            f"👋 Добро пожаловать, {new_member.first_name}! Ознакомьтесь с правилами чата: /rules"
        )

# ===== TELEGRAM STARS / CHECKOUT =====

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True
    )


@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Используй команду <b>ответом</b> на сообщение пользователя.")
        return

    target_id = message.reply_to_message.from_user.id
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            permissions=types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            ),
            until_date=int(time.time())
        )
        bot.reply_to(message, "🔊 Мут снят.")
    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось снять мут: <code>{e}</code>")

        # 🔹 Запуск автосохранения в отдельном потоке
autosave_thread = threading.Thread(target=autosave_activity, daemon=True)
autosave_thread.start()

@bot.message_handler(commands=['deletepoll'])
def delete_poll(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может завершать голосования.")
        return

    if not polls:
        bot.reply_to(message, "❌ Нет активных голосований.")
        return

    # Формируем список активных голосований
    text = "📋 Активные голосования:\n\n"
    for poll_id, poll_data in polls.items():
        text += f"ID: {poll_id}\nВопрос: {poll_data['question']}\n\n"

    bot.reply_to(message, text + "❗ Используйте: /deletepoll [ID], чтобы завершить голосование.")

@bot.message_handler(commands=['deletepoll'])
def delete_poll_by_id(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может завершать голосования.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ Используйте: /deletepoll [ID]")
        return

    try:
        poll_id = int(parts[1])
        if poll_id not in polls:
            bot.reply_to(message, "❌ Голосование с таким ID не найдено.")
            return

        # Формируем результаты голосования
        poll_data = polls.pop(poll_id)
        results_text = f"📊 Результаты голосования: {poll_data['question']}\n\n"
        for i, option in enumerate(poll_data["options"]):
            vote_count = len(poll_data["votes"][i])
            results_text += f"{option}: {vote_count} голос(ов)\n"

        # Уведомляем чат о завершении голосования
        bot.send_message(poll_data["chat_id"], f"❌ Голосование завершено.\n\n{results_text}")
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID.")

@bot.message_handler(commands=['daily'])
def cmd_daily(message):
    user_id = str(message.from_user.id)
    now = datetime.datetime.now()  # Текущая дата и время (offset-naive)
    last_daily = xp_data.get(user_id, {}).get("last_daily")

    if last_daily:
        try:
            last_daily_date = datetime.datetime.fromisoformat(last_daily)
            last_daily_date = last_daily_date.replace(tzinfo=None)
            now_naive = now.replace(tzinfo=None)
            next_available = last_daily_date + datetime.timedelta(days=1)
            if now_naive < next_available:
                remaining = (next_available - now_naive).total_seconds()
                hrs = int(remaining // 3600)
                mins = int((remaining % 3600) // 60)
                secs = int(remaining % 60)
                if hrs > 0:
                    timestr = f"{hrs}ч {mins}м"
                elif mins > 0:
                    timestr = f"{mins}м {secs}s"
                else:
                    timestr = f"{secs}s"
                bot.reply_to(message, f"❌ Вы уже получили ежедневную награду. До следующей: {timestr}.")
                return
        except Exception:
            # Если парсинг упал — позволим выдать награду
            pass

    reward = random.randint(30, 100)  # Рандомная награда от 30 до 100 монет
    add_coins(user_id, reward)
    # Убедимся, что запись в xp_data существует (исправление KeyError)
    if user_id not in xp_data:
        xp_data[user_id] = {"xp": 0, "level": 1, "last_daily": None, "username": message.from_user.username or message.from_user.first_name}
    xp_data[user_id]["last_daily"] = now.isoformat()
    save_xp()
    # Планируем уведомление через 24 часа, когда пользователь снова сможет взять дейли
    try:
        next_available = now + datetime.timedelta(days=1)
        schedule_notification_for_user(user_id, next_available)
    except Exception as e:
        print(f"Ошибка при планировании уведомления после выдачи daily: {e}")
    bot.reply_to(message, f"✅ Вы получили ежедневную награду: {reward} монет!")
    
# ======= Команда очистки дз =======
@bot.message_handler(commands=["clearhomework"])
def clear_homework(message):
    global homework_data

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(
            message,
            "❌ Укажи день, например:\n`/clearhomework пн` или `/clearhomework понедельник`",
            parse_mode="Markdown"
        )
        return

    day = normalize_day_name(args[1])
    if not day:
        bot.reply_to(message, "❌ Не известный день. Попробуй: пн, вт, ср, чт, пт, сб, вс.")
        return

    homework_data[day] = "Пока что нету…"
    save_homework(homework_data)

    bot.reply_to(message, f"🧹 Домашка на *{day}* очищена! Теперь: «Пока что нету…»", parse_mode="Markdown")

import random
import json
import os
import datetime

XP_FILE = "xp_data.json"

# загрузка/сохранение
def load_xp():
    if os.path.exists(XP_FILE):
        try:
            with open(XP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_xp():
    try:
        with open(XP_FILE, "w", encoding="utf-8") as f:
            json.dump(xp_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка при сохранении XP:", e)

xp_data = load_xp()

# ---- Уведомления о доступности /daily ----
def notify_daily_available(uid_str):
    try:
        uid = int(uid_str)
        bot.send_message(uid, "✅ Вы снова можете забрать ежедневную награду: /daily")
    except Exception as e:
        print(f"Ошибка при отправке уведомления daily для {uid_str}: {e}")

def schedule_notification_for_user(uid_str, when_dt):
    try:
        now = datetime.datetime.now()
        # когда_dt может быть строкой или datetime
        if isinstance(when_dt, str):
            when_dt = datetime.datetime.fromisoformat(when_dt)
        delay = (when_dt - now).total_seconds()
        if delay <= 0:
            threading.Thread(target=notify_daily_available, args=(uid_str,), daemon=True).start()
        else:
            t = threading.Timer(delay, notify_daily_available, args=(uid_str,))
            t.daemon = True
            t.start()
    except Exception as e:
        print(f"Ошибка при планировании уведомления daily для {uid_str}: {e}")

# При старте планируем уведомления для тех, у кого ещё не прошло 24 часа
try:
    now = datetime.datetime.now()
    for uid, data in xp_data.items():
        last = data.get("last_daily")
        if not last:
            continue
        try:
            last_dt = datetime.datetime.fromisoformat(last)
            next_av = last_dt + datetime.timedelta(days=1)
            if now < next_av:
                schedule_notification_for_user(uid, next_av)
        except Exception:
            continue
except Exception as e:
    print(f"Ошибка при инициализации планировщика daily: {e}")

# ===== Временные баны: хранение и автоснятие =====
TEMP_BANS_FILE = "temp_bans.json"

def load_temp_bans():
    if os.path.exists(TEMP_BANS_FILE):
        try:
            with open(TEMP_BANS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_temp_bans(bans):
    try:
        with open(TEMP_BANS_FILE, "w", encoding="utf-8") as f:
            json.dump(bans, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении temp_bans: {e}")

temp_bans = load_temp_bans()

def unban_and_invite(chat_id, user_id, entry=None):
    try:
        bot.unban_chat_member(chat_id, user_id)
    except Exception as e:
        print(f"Ошибка при разбане {user_id} в {chat_id}: {e}")
    # Попробуем отправить пользователю ссылку на приглашение
    try:
        link = None
        try:
            link = bot.export_chat_invite_link(chat_id)
        except Exception:
            link = None
        if link:
            try:
                bot.send_message(user_id, f"✅ Вас разбанили в чате. Ссылка для возвращения: {link}")
            except Exception:
                pass
        # Уведомление в чате
        try:
            name = entry.get("display") if entry and isinstance(entry, dict) else str(user_id)
            bot.send_message(chat_id, f"♻️ Пользователь {name} был разбанен и может вернуться.")
        except Exception:
            pass
    finally:
        # удаляем из списка и сохраняем
        try:
            global temp_bans
            temp_bans = [b for b in temp_bans if not (b.get("chat_id") == chat_id and b.get("user_id") == user_id)]
            save_temp_bans(temp_bans)
        except Exception:
            pass

def schedule_unban_for(entry):
    try:
        chat_id = int(entry.get("chat_id"))
        user_id = int(entry.get("user_id"))
        until_ts = int(entry.get("until"))
        delay = until_ts - int(time.time())
        if delay <= 0:
            threading.Thread(target=unban_and_invite, args=(chat_id, user_id, entry), daemon=True).start()
        else:
            t = threading.Timer(delay, unban_and_invite, args=(chat_id, user_id, entry))
            t.daemon = True
            t.start()
    except Exception as e:
        print(f"Ошибка при планировании разбанa: {e}")

# При старте планируем все существующие временные баны
try:
    now_ts = int(time.time())
    for e in list(temp_bans):
        try:
            if int(e.get("until", 0)) > now_ts:
                schedule_unban_for(e)
            else:
                # уже истёк — разбаним сразу
                schedule_unban_for(e)
        except Exception:
            continue
except Exception as e:
    print(f"Ошибка при инициализации temp_bans: {e}")

# начисление XP за сообщение
def add_xp(user_id, username, amount=5):
    # Если пользователь в блоке личного спама — не начисляем XP
    try:
        uid = str(user_id)
        blocked_until = private_spam_blocks.get(uid, 0)
        if blocked_until and time.time() < blocked_until:
            return False, xp_data.get(uid, {}).get("level", 1), xp_data.get(uid, {}).get("xp", 0)
    except Exception:
        pass

    if str(user_id) not in xp_data:
        xp_data[str(user_id)] = {"xp": 0, "level": 1, "last_daily": None, "username": username}
    xp_data[str(user_id)]["xp"] += amount
    xp_data[str(user_id)]["username"] = username
    # проверка уровня
    current_level = xp_data[str(user_id)]["level"]
    needed_xp = current_level * 100
    level_up = False
    if xp_data[str(user_id)]["xp"] >= needed_xp:
        xp_data[str(user_id)]["level"] += 1
        level_up = True
        bot.send_message(user_id, f"🎉 Поздравляем! Вы достигли уровня {xp_data[str(user_id)]['level']}!")
    save_xp()
    return level_up, xp_data[str(user_id)]["level"], xp_data[str(user_id)]["xp"]

# команда /level
@bot.message_handler(commands=['level'])
def cmd_level(message):
    uid = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    if uid not in xp_data:
        bot.reply_to(message, "У вас ещё нет XP. Напишите что-нибудь в чате, чтобы заработать XP.")
        return
    data = xp_data[uid]
    bot.reply_to(message, f"👤 {username}\nУровень: {data['level']}\nXP: {data['xp']}")

ROLE_PRICES = {
    "⭐ Модератор": {
        1: 10000,
        3: 25000,
        7: 50000,
        30: 70000,
        9999: 150000
    },
    "👑 Администратор": {
        1: 50000,
        3: 75000,
        7: 100000,
        30: 200000,
        9999: 400000
    },
    "👑 Владелец": {
        9999: 800000
    },
    "⭐ Мл. админ": {
        1: 1000,
        3: 2500,
        7: 6500,
        30: 15000,
        9999: 30000
    }
}

# Список товаров магазина
# Команда /shop — отображение магазина с кнопками
@bot.message_handler(commands=["shop"])
def cmd_shop(message):
    markup = types.InlineKeyboardMarkup(row_width=1)

    for role in ROLE_PRICES.keys():
        markup.add(
            types.InlineKeyboardButton(
                text=role,
                callback_data=f"role_{role}"
            )
        )

    balance = get_user_balance(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"🏪 Магазин \n\n💰 Баланс: {balance} монет\n\nВыберите товар:",
        reply_markup=markup
    )

# ========== Покупка монет за звёзды (pending system) ==========
PENDING_FILE = "pending_purchases.json"
pending_purchases = {}

def load_pending():
    global pending_purchases
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, "r", encoding="utf-8") as f:
                pending_purchases = json.load(f)
        except Exception:
            pending_purchases = {}
    else:
        pending_purchases = {}

def save_pending():
    try:
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(pending_purchases, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Ошибка при сохранении pending_purchases: {e}")

load_pending()

# Опции покупки: ключ -> coins, required stars, label
BUY_PACKAGES = {
    "p1": {"coins": 1000, "stars": 2, "label": "1000 монет - 5 звёзд"},
    "p2": {"coins": 5000, "stars": 10, "label": "5000 монет - 10 звёзд"},
    "p3": {"coins": 10000, "stars": 15, "label": "10000 монет - 15 звёзд"},
    "p4": {"coins": 50000, "stars": 25, "label": "50000 монет - 25 звёзд"},
    "p5": {"coins": 100000, "stars": 50, "label": "100000 монет - 50 звёзд"},
}

@bot.message_handler(commands=['buycoins'])
def cmd_buycoins(message):
    # команда доступна только в личке
    if message.chat.type != "private":
        bot.reply_to(message, "✉️ Напишите мне в личку команду /buycoins")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, pkg in BUY_PACKAGES.items():
        markup.add(types.InlineKeyboardButton(pkg['label'], callback_data=f"buypkg_{key}"))

    bot.reply_to(message, "🪙 Выберите пакет монет для покупки за звёзды:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith('buypkg_'))
def handle_buypkg(call):
    key = call.data.split('_', 1)[1]
    pkg = BUY_PACKAGES.get(key)
    if not pkg:
        bot.answer_callback_query(call.id, "❌ Пакет не найден.")
        return

    # создаём заявку
    purchase_id = str(int(time.time() * 1000))
    pending_purchases[purchase_id] = {
        "user_id": str(call.from_user.id),
        "username": call.from_user.username or call.from_user.first_name,
        "coins": pkg['coins'],
        "stars": pkg['stars'],
        "created": datetime.datetime.utcnow().isoformat()
    }
    save_pending()

    # Инструкция: отправьте звёзды владельцу бота и перешлите уведомление или дождитесь подтверждения
    instruction = (
        f"✅ Заявка #{purchase_id} создана.\n"
        f"Пакет: {pkg['coins']} монет за {pkg['stars']} звёзд.\n\n"
        f"1) Отправьте {pkg['stars']} звёзд владельцу бота (ID: {OWNER_ID}).\n"
        "2) После отправки перешлите сюда уведомление о получении звёзд (forward),\n"
        "   либо нажмите кнопку 'Уведомить владельца' — он подтвердит вручную.\n\n"
        "После подтверждения вам автоматически зачислятся монеты."
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Уведомить владельца", callback_data=f"notifyowner_{purchase_id}"))
    try:
        bot.send_message(call.from_user.id, instruction, reply_markup=kb)
        bot.answer_callback_query(call.id, "✅ Заявка создана. Инструкция отправлена в ЛС.")
    except Exception:
        bot.answer_callback_query(call.id, "✅ Заявка создана. Пожалуйста, проверьте ЛС у бота.")


@bot.callback_query_handler(func=lambda c: c.data.startswith('notifyowner_'))
def handle_notifyowner(call):
    pid = call.data.split('_', 1)[1]
    info = pending_purchases.get(pid)
    if not info:
        bot.answer_callback_query(call.id, "❌ Заявка не найдена.")
        return

    # Уведомляем владельца бота
    user_display = f"@{info.get('username')}" if info.get('username') else f"ID:{info.get('user_id')}"
    text = (
        f"📥 Заявка на покупку #{pid}\n"
        f"Пользователь: {user_display} (ID:{info.get('user_id')})\n"
        f"Пакет: {info.get('coins')} монет за {info.get('stars')} звёзд\n\n"
        f"Пожалуйста, подтвердите получение звёзд командой: /confirmpurchase {pid}"
    )
    try:
        bot.send_message(OWNER_ID, text)
        bot.answer_callback_query(call.id, "✅ Владелец уведомлён. Ожидайте подтверждения.")
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠ Не удалось уведомить владельца. Попробуйте позже.")


@bot.message_handler(commands=['confirmpurchase'])
def cmd_confirmpurchase(message):
    # Только владелец подтверждает получение звёзд
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец может подтверждать покупки.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Используйте: /confirmpurchase [ID_заявки]")
        return
    pid = parts[1].strip()
    info = pending_purchases.get(pid)
    if not info:
        bot.reply_to(message, "❌ Заявка не найдена.")
        return

    try:
        target_id = int(info['user_id'])
        add_coins(target_id, int(info['coins']), bypass_block=True)
        # удаляем заявку
        pending_purchases.pop(pid, None)
        save_pending()

        bot.reply_to(message, f"✅ Подтверждение принято. Зачислено {info['coins']} монет пользователю ID:{target_id}.")
        try:
            bot.send_message(target_id, f"✅ Ваша покупка #{pid} подтверждена. Вам зачислено {info['coins']} монет.")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при подтверждении: {e}")


@bot.message_handler(commands=['pendingpurchases'])
def cmd_pendingpurchases(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец может просматривать список заявок.")
        return
    if not pending_purchases:
        bot.reply_to(message, "ℹ️ Нет активных заявок.")
        return
    text = "📋 Активные заявки:\n\n"
    for pid, info in pending_purchases.items():
        text += f"ID:{pid} — {info.get('coins')} монет за {info.get('stars')} звёзд — пользователь: {info.get('username') or info.get('user_id')}\n"
    bot.reply_to(message, text)

polls = {}  # Словарь для хранения активных голосований


# ======= Авто-подтверждение по пересланному уведомлению о звёздах ======
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_forward_for_stars(m):
    # Пытаемся распарсить число звёзд из пересланного сообщения или текста
    try:
        # Соберём возможные источники текста
        sources = []
        if getattr(m, 'text', None):
            sources.append(m.text)
        if getattr(m, 'caption', None):
            sources.append(m.caption)
        if getattr(m, 'forward_sender_name', None):
            sources.append(m.forward_sender_name)

        big = "\n".join([s for s in sources if s])
        if not big:
            return  # ничего разобрать

        # ищем количество звёзд (регэксы для русских и английских слов и символа ⭐)
        mnum = re.search(r"(\d+)\s*(?:зв|звёзд|звезд|stars|star|⭐)", big, re.IGNORECASE)
        if not mnum:
            return
        stars_sent = int(mnum.group(1))

        # найти подходящую заявку для этого пользователя и количества звёзд
        uid = str(m.from_user.id)
        candidates = []
        for pid, info in pending_purchases.items():
            if info.get('user_id') == uid and int(info.get('stars', 0)) == stars_sent:
                # parse created to sort
                created = info.get('created')
                candidates.append((created or '', pid, info))

        if not candidates:
            bot.reply_to(m, "⚠ Не найдена заявка на такое число звёзд. Если вы ещё не создали заявку — отправьте /buycoins.")
            return

        # выберем самую старую заявку
        candidates.sort(key=lambda x: len(x[0]), reverse=True)
        chosen = candidates[0][1]
        info = pending_purchases.get(chosen)

        # зачисляем монеты
        try:
            target_id = int(info['user_id'])
            add_coins(target_id, int(info['coins']), bypass_block=True)
            pending_purchases.pop(chosen, None)
            save_pending()

            bot.reply_to(m, f"✅ Оплата подтверждена. Вам зачислено {info['coins']} монет (заявка #{chosen}).")
            try:
                bot.send_message(OWNER_ID, f"ℹ️ Автоподтверждена заявка #{chosen} — {info['coins']} монет за {info['stars']} звёзд. Пользователь: {info.get('username')} (ID:{info.get('user_id')})")
            except Exception:
                pass
        except Exception as e:
            bot.reply_to(m, f"❌ Ошибка при зачислении: {e}")
    except Exception:
        # не прерываем работу — просто игнорируем
        return

@bot.message_handler(commands=['poll'])
def create_poll(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может создавать голосования.")
        return

    parts = message.text.split("\n")
    if len(parts) < 3:
        bot.reply_to(message, "❗ Используйте: /poll [вопрос]\n[вариант 1]\n[вариант 2]\n...")
        return

    question = parts[0][6:]  # Убираем "/poll "
    options = parts[1:]

    # Создаём кнопки для голосования
    markup = types.InlineKeyboardMarkup()
    for i, option in enumerate(options):
        markup.add(types.InlineKeyboardButton(f"{option} (0)", callback_data=f"vote_{i}"))

    # Отправляем сообщение с голосованием
    poll_message = bot.send_message(message.chat.id, f"📊 {question}", reply_markup=markup)

    # Сохраняем данные о голосовании
    polls[poll_message.message_id] = {
        "question": question,
        "options": options,
        "votes": {i: [] for i in range(len(options))},  # Список голосов для каждого варианта
        "chat_id": message.chat.id
    }
    
@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
    _, poll_id, option_index = call.data.split("_")
    poll_id = int(poll_id)
    option_index = int(option_index)

    if poll_id not in polls:
        bot.answer_callback_query(call.id, "❌ Это голосование уже завершено.")
        return

    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    # Проверяем, голосовал ли пользователь ранее
    for voters in polls[poll_id]["votes"].values():
        if user_id in voters:
            bot.answer_callback_query(call.id, "❌ Вы уже проголосовали!")
            return

    # Регистрируем голос
    polls[poll_id]["votes"][option_index].append(user_id)

    # Обновляем текст кнопки с количеством голосов
    markup = types.InlineKeyboardMarkup()
    for i, option in enumerate(polls[poll_id]["options"]):
        vote_count = len(polls[poll_id]["votes"][i])
        markup.add(types.InlineKeyboardButton(f"{option} ({vote_count})", callback_data=f"vote_{poll_id}_{i}"))

    bot.edit_message_reply_markup(
        chat_id=polls[poll_id]["chat_id"],
        message_id=poll_id,
        reply_markup=markup
    )

    # Уведомляем пользователя
    bot.answer_callback_query(call.id, "✅ Ваш голос учтён!")

    # Отправляем уведомление владельцу бота
    bot.send_message(
        OWNER_ID,
        f"🗳 Пользователь {username} проголосовал за вариант: {polls[poll_id]['options'][option_index]}"
    )

# Обработка покупки через callback
def grant_role(chat_id: int, user_id: int, role: str) -> bool:
    """Выдаёт роль пользователю в чате. Возвращает True если успешно."""
    def _role_title(r: str) -> str:
        # ??????? ??????/?????? ???????, ????????? ?????????/????????/?????/???????/?????/??????
        cleaned = re.sub(r"[^\w\u0400-\u04FF .-]+", "", r).strip()
        title = cleaned or r
        return title[:16]  # ????? Telegram ?? custom title

    try:
        if role == "⭐ Модератор":
            bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_delete_messages=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
                can_manage_chat=False
            )
        elif role == "👑 Администратор":
            bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        elif role == "⭐ Мл. админ":
            bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_delete_messages=True,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=True,
                can_manage_chat=False
            )
        elif role == "👑 Владелец":
            bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_restrict_members=True,
                can_promote_members=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        # ??????????? ????????? title ? ?????? ???????
        try:
            bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
            can_promote = getattr(bot_member, 'can_promote_members', False)
            if not can_promote:
                try:
                    bot.send_message(OWNER_ID, '?? ???? ?? ??????? ???? (????????? ???????????????) ??? ????????? title.')
                except Exception:
                    pass
            else:
                bot.set_chat_administrator_custom_title(
                    chat_id=chat_id,
                    user_id=user_id,
                    custom_title=_role_title(role)
                )
        except Exception as e:
            try:
                bot.send_message(OWNER_ID, f'?? ?? ??????? ?????????? title: {e}')
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"❌ Ошибка при выдаче роли {role}: {e}")
        return False

# ??????????? ??????? ROLE_PRICES ??? ?????? ????????????
try:
    ROLE_PRICES
except NameError:
    ROLE_PRICES = {}

@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def handle_role_select(call):
    role = call.data.replace("role_", "")

    if role not in ROLE_PRICES:
        bot.answer_callback_query(call.id, "❌ Ошибка роли")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

    for days, price in ROLE_PRICES[role].items():
        if days == 9999:
            text = f"Навсегда — {price} монет"
        else:
            text = f"{days} дней — {price} монет"

        markup.add(
            types.InlineKeyboardButton(
                text=text,
                callback_data=f"buy_{role}_{days}"
            )
        )

    bot.edit_message_text(
        f"🏪 {role}\n\nВыберите срок:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy(call):
    data = call.data[4:]

    # 🔒 Защита: новый формат ОБЯЗАН быть role_days
    if "_" not in data:
        bot.answer_callback_query(call.id, "❌ Устаревшая кнопка. Откройте /shop заново.")
        return

    item_name, days = data.rsplit("_", 1)

    try:
        days = int(days)
    except:
        bot.answer_callback_query(call.id, "❌ Ошибка срока")
        return

    # 🔒 Защита: роль обязана существовать в новой системе
    if item_name not in ROLE_PRICES:
        bot.answer_callback_query(call.id, "❌ Устаревшая кнопка. Откройте /shop заново.")
        return

    user_id = call.from_user.id
    chat_id = call.message.chat.id

    price = ROLE_PRICES[item_name].get(days)

    if not price:
        bot.answer_callback_query(call.id, "❌ Ошибка цены")
        return

    balance = get_user_balance(user_id)

    if balance < price:
        bot.answer_callback_query(call.id, f"❌ Недостаточно монет. Баланс: {balance}")
        return

    if call.message.chat.type == "private":
        bot.answer_callback_query(call.id, "❌ Роли можно покупать только в группах")
        return

    # 🔒 Защита от двойного клика
    lock_key = f"{chat_id}:{user_id}:lock"
    roles = load_roles()

    if lock_key in roles:
        bot.answer_callback_query(call.id, "⏳ Подождите, операция выполняется...")
        return

    roles[lock_key] = True
    save_roles(roles)

    # Выдача роли
    if not grant_role(chat_id, user_id, item_name):
        del roles[lock_key]
        save_roles(roles)
        bot.answer_callback_query(call.id, "⚠️ Ошибка выдачи роли")
        return

    remove_coins(user_id, price)

    # ⏳ Сохраняем срок
    key = f"{chat_id}:{user_id}"

    if days == 9999:
        expire = 0
    else:
        expire = int(time.time()) + days * 86400

    roles[key] = {
        "chat_id": chat_id,
        "user_id": user_id,
        "role": item_name,
        "expire": expire
    }

    # снимаем лок
    del roles[lock_key]
    save_roles(roles)

    if days == 9999:
        time_text = "навсегда"
    else:
        time_text = f"{days} дн."

    bot.edit_message_text(
        f"✅ Роль куплена!\n\n"
        f"🎭 {item_name}\n"
        f"⏳ {time_text}\n"
        f"💰 {price} монет",
        chat_id,
        call.message.message_id
    )

    # ===== ОБЫЧНЫЕ ТОВАРЫ =====
    item_price = ROLE_PRICES.get(item_name, {}).get("price")

    if item_price is None:
        bot.answer_callback_query(call.id, "❌ Товар не найден.")
        return

    if balance < item_price:
        bot.answer_callback_query(call.id, f"❌ Недостаточно монет. Баланс: {balance}")
        return

    remove_coins(user_id, item_price)
    bot.answer_callback_query(call.id, f"✅ Вы купили {item_name} за {item_price} монет!")

def get_user_balance(user_id):
    """Получить баланс пользователя по его ID."""
    uid = str(user_id)
    return coins_data.get(uid, {}).get("coins", 0)

def remove_coins(user_id, amount):
    """Списать монеты у пользователя."""
    uid = str(user_id)
    if uid in coins_data:
        if coins_data[uid]["coins"] >= amount:
            coins_data[uid]["coins"] -= amount
            save_coins()
        else:
            raise ValueError("Недостаточно монет для списания.")
        
def add_coins(user_id, amount, bypass_block=False):
    """Добавить монеты пользователю.

    Если `bypass_block`=True, игнорируем приватный блок (используется для переводов).
    """
    uid = str(user_id)
    # Если пользователь в блоке личного спама — не начисляем монеты (если не bypass)
    try:
        if not bypass_block:
            blocked_until = private_spam_blocks.get(uid, 0)
            if blocked_until and time.time() < blocked_until:
                return False
    except Exception:
        pass

    if uid not in coins_data:
        coins_data[uid] = {"coins": 0}
    coins_data[uid]["coins"] += amount
    save_coins()
    return True

def has_immunity(user_id):
    """Проверяет, есть ли у пользователя иммунитет к бану."""
    uid = str(user_id)
    immune_users = load_immune_users()
    cnt = immune_users.get(uid, 0)
    if cnt > 0:
        cnt -= 1
        if cnt > 0:
            immune_users[uid] = cnt
        else:
            # удалить ключ если больше нет иммунитетов
            immune_users.pop(uid, None)
        save_immune_users(immune_users)
        return True
    return False

roles = load_roles()

save_roles(roles)

@bot.message_handler(commands=['privateblocks'])
def cmd_privateblocks(message):
    # Только админ/владелец
    if message.from_user.id not in (OWNER_ID, ADMIN_USER_ID):
        bot.reply_to(message, "❌ У вас нет прав для этой команды.")
        return

    now = time.time()
    lines = []
    for uid, until_ts in private_spam_blocks.items():
        if until_ts > now:
            rem = int(until_ts - now)
            mins = rem // 60
            lines.append(f"ID:{uid} — осталось {mins} мин")
    if not lines:
        bot.reply_to(message, "ℹ️ Нет активных блокировок личных начислений.")
    else:
        bot.reply_to(message, "📋 Активные блокировки:\n" + "\n".join(lines))

@bot.message_handler(commands=['unblockprivate'])
def cmd_unblockprivate(message):
    # Только админ/владелец
    if message.from_user.id not in (OWNER_ID, ADMIN_USER_ID):
        bot.reply_to(message, "❌ У вас нет прав для этой команды.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Используйте: /unblockprivate [user_id]")
        return
    target = parts[1].strip()
    if target in private_spam_blocks:
        private_spam_blocks.pop(target, None)
        save_private_spam()
        bot.reply_to(message, f"✅ Блокировка для ID {target} снята.")
    else:
        bot.reply_to(message, "⚠️ Такая блокировка не найдена.")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("🚀 Запуск бота...")
    
    # Укажите ID вашей группы и темы
    GROUP_CHAT_ID = -1002241393389  # Замените на ваш chat_id
    TOPIC_ID = 1803  # Замените на ваш topic_id

    # Запуск ежедневного сообщения
    schedule_daily_message(GROUP_CHAT_ID, TOPIC_ID)
    threading.Thread(target=role_watcher, daemon=True).start()
    # Запуск polling
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
            break
        except KeyboardInterrupt:
            print("⏹ Бот остановлен вручную.")
            break
        except Exception:
            logging.exception("Infinity polling exception — перезапуск через 5 секунд")
            time.sleep(5)
