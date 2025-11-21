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
                return json.load(f)
        except Exception as e:
            print(f"⚠ Ошибка при загрузке данных об иммунитете: {e}")
    return {}

# Сохранение данных об иммунитете
def save_immune_users(data):
    try:
        with open(IMMUNE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠ Ошибка при сохранении данных об иммунитете: {e}")

# ====== Активность ачаст ======

activity_data = defaultdict(lambda: {"username": None, "first_name": None, "last_name": None,
                                     "all": {"messages": 0}, "by_chat": {}, "leader_since": None})

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
       Если данных мало — пробуем подтянуть через get_chat_member."""
    d = activity_data.get(user_id, {})
    first = d.get("first_name")
    last  = d.get("last_name")
    uname = d.get("username")

    name = None
    if first or last:
        name = f"{first or ''} {last or ''}".strip()
    if not name and uname:
        name = f"@{uname}"

    # если до сих пор пусто — пробуем подтянуть из чата
    if not name and chat_id is not None:
        try:
            member = bot.get_chat_member(chat_id, user_id)
            u = member.user
            first = first or (u.first_name or None)
            last  = last  or (getattr(u, "last_name", None))
            uname = uname or (u.username or None)

            if first or last:
                name = f"{first or ''} {last or ''}".strip()
            if not name and uname:
                name = f"@{uname}"

            # кэшируем обратно
            dd = activity_data[user_id]
            if first: dd["first_name"] = first
            if last:  dd["last_name"]  = last
            if uname: dd["username"]   = uname
        except Exception:
            pass

    return name or f"ID:{user_id}"

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

    # 12 часов на первом месте — выдаём права модерации (пример)
    try:
        if (now_dt - then_dt).total_seconds() >= 12 * 3600:
            bot.promote_chat_member(
                chat_id=chat_id,
                user_id=int(top_uid),
                can_manage_chat=False,
                can_delete_messages=True,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=True
            )
            bot.send_message(chat_id, f"👑 {_display_name(top_uid, chat_id)} держится на первом месте 12 часов и теперь админ!")
            # обновляем метку в ISO-формате
            top_stats["leader_since"] = now_dt.isoformat()
            save_activity()
    except Exception as e:
        print(f"Ошибка при выдаче прав: {e}")

@bot.message_handler(func=lambda m: bool(getattr(m, "text", None)) and not m.text.startswith("/"))
def handle_message(message):
    # Увеличиваем активность пользователя
    _activity_add(message.from_user, message.chat.id)

    # Начисляем монеты за сообщение
    try:
        add_coins(message.from_user.id, 1)  # Начисляем 1 монету за сообщение
    except Exception as e:
        print(f"Ошибка при начислении монет: {e}")

    # Геймификация: начисляем XP за сообщение
    try:
        level_up, new_level, total_xp = add_xp(
            message.from_user.id,
            message.from_user.username or message.from_user.first_name,
            amount=5
        )
        if level_up:
            bot.reply_to(
                message,
                f"🎉 {message.from_user.first_name} повысил уровень до {new_level}! (Всего XP: {total_xp})"
            )
    except Exception as e:
        print(f"Ошибка при начислении XP: {e}")

from telebot import types
import sys, os

# 🔑 Твой Telegram ID
OWNER_ID = 5782683757  

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

from datetime import timezone
import json
import os
# ===== Файл для хранения активности =====
ACTIVITY_FILE = "activity.json"

# ===== Загрузка данных при старте =====
if os.path.exists(ACTIVITY_FILE):
    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            activity_data = json.load(f)
    except Exception:
        activity_data = {}
else:
    activity_data = {}

# =============== ВСПОМОГАТЕЛЬНОЕ ===============
def is_admin(chat_id, user_id) -> bool:
    """Проверка, что пользователь админ чата."""
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "creator")
    except Exception:
        return False

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
    "Сука", "сука", "Блять", "блять", "Пизда", "пизда", "Хуй", "хуй", "Ебать", "ебать", "Еблан", "еблан", "Пидор", "пидор", "Пидрила", "пидрила", "Мудак", "мудак","Долбоёб", "долбоёб", "Пиздец", "пиздец", "Гандон", "гандон", "Залупа", "залупа","Пиздюк", "пиздюк", "Пидорас", "пидорас", "Ебаный", "ебаный", "Ебать", "ебать", "Еблан", "еблан", "Пиздабол", "пиздабол", "Мудак", "мудак","Долбоёб", "долбоёб", "Пиздец", "пиздец", "Гандон", "гандон", "Залупа", "залупа","Хуесос","хуесос","Пидорас","пидорас","Ебать","ебать","Ебаный","ебаный","Блядь","блядь","Бля","бля","Пизда","пизда","Хуй","хуй","Пиздюк","пиздюк","Пидор","пидор","Пидрила","пидрила","Мудак","мудак","Долбоёб","долбоёб","Пиздец","пиздец","Гандон","гандон","Залупа","залупа"
    # добавь свои слова через запятую
]

# ===================== АВТОМОДЕРАЦИЯ ======================
@bot.message_handler(func=lambda m: bool(getattr(m, "text", None)) and not m.text.startswith("/"))
def anti_spam_handler(message):
    user_id = message.from_user.id
    now = time.time()

    # --- Инициализация списка сообщений ---
    if user_id not in user_messages:
        user_messages[user_id] = []

    # --- Антиспам ---
    user_messages[user_id].append(now)
    # оставляем только последние 10 секунд
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t <= 5]

    if len(user_messages[user_id]) >= 5:
        try:
            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=int(now) + 3600  # мут на 1 час
            )
            bot.reply_to(message, f"⚠️ {message.from_user.first_name}, слишком много сообщений! Мут на 1 час.")
            user_messages[user_id] = []
        except Exception:
            pass

    # --- Проверка на мат ---
    text_lower = message.text.lower()
    if any(bw in text_lower for bw in banned_words):
        try:
            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=int(now) + 3600  # мут на 1 час
            )
            bot.reply_to(message, f"⛔ {message.from_user.first_name}, запрещённые слова! Мут на 1 час.")
        except Exception:
            pass
    # --- Сохраняем данные между перезапусками ---
    with open('user_messages.json', 'w') as f:
        json.dump({str(uid): ts for uid, ts in user_messages.items()}, f)

            # ====== Отслеживание сообщений ======
        @bot.message_handler(func=lambda m: bool(getattr(m, "text", None)) and not m.text.startswith("/"))
        def handle_message(message):
                _activity_add(message.from_user)
                # Если есть авто-модерация, её можно оставить здесь

                    # === Геймификация: начисляем XP за обычное сообщение (не команду) ===
    try:
        level_up, new_level, total_xp = add_xp(message.from_user.id, message.from_user.username or message.from_user.first_name, amount=5)
        if level_up:
            bot.reply_to(
                message,
                f"🎉 {message.from_user.first_name} повысил уровень до {new_level}! (Всего XP: {total_xp})"
            )
    except Exception as e:
        print("XP error:", e)

def add_xp_with_rewards(user_id, username, amount=5):
    level_up, new_level, total_xp = add_xp(user_id, username, amount)
    if level_up:
        reward = new_level * 10  # Награда за уровень
        add_coins(user_id, reward)
        bot.send_message(user_id, f"🎉 Поздравляем! Вы достигли уровня {new_level} и получили {reward} монет!")
    return level_up, new_level, total_xp

def send_days_to_summer(chat_id, topic_id):
    """Отправляет сообщение о днях до лета в указанную тему."""
    today = datetime.date.today()
    next_summer = datetime.date(today.year, 6, 1)
    if today > next_summer:
        next_summer = datetime.date(today.year + 1, 6, 1)
    days_left = (next_summer - today).days

    bot.send_message(
        chat_id=chat_id,
        text=f"🌞 До лета осталось {days_left} дней! Ожидаем...",
        message_thread_id=topic_id  # Отправка в тему
    )
    
def schedule_daily_message(chat_id, topic_id):
    """Запускает задачу для отправки сообщения каждый день в 10:00."""
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
        totals.append((name, total_msgs))

    totals.sort(key=lambda x: x[1], reverse=True)
    top_list = totals[:5]

    text = "🏆 Топ-5 самых активных:\n\n"
    for i, (name, count) in enumerate(top_list, start=1):
        text += f"{i}. {name} — {count} сообщений\n"

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
        "/rules – правила",
        "/lessons [день] – расписание уроков (Пн/Вт/.. или полное имя)",
        "/homework [день] – показать ДЗ (в группе). В ЛС админ задаёт ДЗ: /homework [день] [текст]",
        "/activity – показать свою активность",
        "/activity [ответ] – показать активность другого пользователя",
        "/globalactivity – показать топ-5 активности",
        "/level - показывает ваш уровень",
        "/daily - ежедневная награда",
        "/shop - Открыть магазин",
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
    ]

    text = "\n".join(cmds)
    try:
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    except Exception:
        # fallback — короткий ответ, если отправка HTML упала
        bot.reply_to(message, "\n".join(cmds))

poll_data = {"question": "", "options": [], "votes": {}}

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
    
@bot.message_handler(commands=['resetgolosovanie'])
def reset_poll(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота может сбросить голосование.")
        return

    poll_data.clear()
    poll_data.update({"question": "", "options": [], "votes": {}})
    bot.reply_to(message, "✅ Голосование сброшено.")

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    bot.reply_to(message,
        "📌 <b>Правила чата</b>:\n"
        "1) Не спамить\n"
        "2) Без оскорблений/мата\n"
        "3) Не обижать\n"
        "4) Уважение к участникам\n"
        "5) Без 18+"
    )


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
            text=f"📢 Сообщение от RBXTelega:\n\n{text}",
        )
        bot.reply_to(message, "✅ Сообщение отправлено в чат.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

# =============== РАСПИСАНИЕ УРОКОВ ===============
schedule_dict = {
    "пн": "\n 1: 9:00 - 9:45\n 2: 10:05 - 10:50 \n2 "
    "вт" "",
    "ср": "",
    "чт": "",
    "пт": "",
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

warnings = {}  # { "@username": int }

# =============== /balance ================
@bot.message_handler(commands=["balance", "coins"])
def cmd_balance(message):
    user_id = message.from_user.id
    balance = get_user_balance(user_id)  # Используем новую функцию
    bot.reply_to(message, f"💰 Ваш баланс: {balance} монет.")

@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "✍️ Используй: /warn @username [причина]")
        return
    username, reason = parts[1], parts[2]
    warnings[username] = warnings.get(username, 0) + 1
    bot.reply_to(message, f"⚠️ {username} получил предупреждение #{warnings[username]}. Причина: {reason}")

@bot.message_handler(commands=['clearwarns'])
def cmd_clearwarns(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Используй: /clearwarns @username")
        return
    username = parts[1]
    warnings[username] = 0
    bot.reply_to(message, f"✅ Предупреждения для {username} очищены.")

@bot.message_handler(commands=['warnslist'])
def cmd_warnslist(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Используй: /warnslist @username")
        return
    username = parts[1]
    count = warnings.get(username, 0)
    bot.reply_to(message, f"ℹ️ У {username} сейчас {count} предупреждение(й).")

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
        bot.reply_to(message, "✍️ Используй: /report [текст жалобы]\n<b>как правльно оформить жалобу<b>\nесли у вас жалоба на сообщение, следуйте инструкции:\n1. зажмите это сообщение\n2. скопируйте ссылку на сообщение\nправильное фофрмление: /report [ссылка на сообщение] [причина]\n\n <b>жалоба на пользователя<b>\nесли вы хотите пожаловатся на пользователя, пишите так: \n/report @username [причина]\n\n обязательно после /report пишите хэштег:\n#user - жалоба на пользователя\n #message - жалоба на сообщение")
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
        bot.reply_to(message, f"✅ Домашнее задание на <b>{day_full}</b> обновлено:\n{task}")
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

    target_id = message.reply_to_message.from_user.id
    if has_immunity(target_id):
        bot.reply_to(message, "🛡 {first_name} избежал бана иммунитетом!")
        return

    parts = message.text.split(maxsplit=1)
    seconds = parse_time_to_seconds(parts[1]) if len(parts) > 1 else 3600
    if seconds is None:
        bot.reply_to(message, "❗ Неверный формат времени. Пример: 30m, 2h, 1d")
        return

    try:
        bot.ban_chat_member(message.chat.id, target_id, until_date=int(time.time()) + seconds)
        bot.reply_to(message, f"🚫 Пользователь забанен на {parts[1] if len(parts) > 1 else '1h'}.")
    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось забанить: <code>{e}</code>")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только админы могут использовать эту команду!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Используй команду <b>ответом</b> на сообщение. Пример: /mute 30m")
        return

    parts = message.text.split(maxsplit=1)
    seconds = parse_time_to_seconds(parts[1]) if len(parts) > 1 else 3600
    if seconds is None:
        bot.reply_to(message, "❗ Неверный формат времени. Пример: 30m, 2h, 1d")
        return

    target_id = message.reply_to_message.from_user.id
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=int(time.time()) + seconds
        )
        bot.reply_to(message, f"🔇 Пользователь замьючен на {parts[1] if len(parts)>1 else '1h'}.")

        # Запускаем таймер для автоматического снятия мута
        def unmute_later():
            time.sleep(seconds)
            unmute_user(message.chat.id, target_id)
        threading.Thread(target=unmute_later, daemon=True).start()

    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось замутить: <code>{e}</code>")
        
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        bot.send_message(
            message.chat.id,
            f"👋 Добро пожаловать, {new_member.first_name}! Ознакомьтесь с правилами чата: /rules"
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
        last_daily_date = datetime.datetime.fromisoformat(last_daily)
        # Приведение обеих дат к offset-naive для корректного сравнения
        last_daily_date = last_daily_date.replace(tzinfo=None)
        now_naive = now.replace(tzinfo=None)
        if (now_naive - last_daily_date).days < 1:
            bot.reply_to(message, "❌ Вы уже получили ежедневную награду. Попробуйте завтра.")
            return

    reward = random.randint(30, 100)  # Рандомная награда от 30 до 100 монет
    add_coins(user_id, reward)
    xp_data[user_id]["last_daily"] = now.isoformat()
    save_xp()
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

# начисление XP за сообщение
def add_xp(user_id, username, amount=5):
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

# Список товаров магазина
SHOP_ITEMS = {
    "⭐ Модератор": 5000,
    "👑 Администратор": 10000,
    "👑 Владелец": 100000,
    "⭐ Мл. админ": 10000,
    "🛡 Иммунитет к бану (1)": 1000
}

# Команда /shop — отображение магазина с кнопками
@bot.message_handler(commands=["shop"])
def cmd_shop(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for item, price in SHOP_ITEMS.items():
        btn = types.InlineKeyboardButton(
            text=f"{item} - {price} монет",
            callback_data=f"buy_{item}"
        )
        markup.add(btn)
    
    user_balance = get_user_balance(message.from_user.id)
    bot.reply_to(
        message,
        f"🏪 Магазин\nВаш баланс: {user_balance} монет\n\nВыберите товар для покупки:",
        reply_markup=markup
    )

polls = {}  # Словарь для хранения активных голосований

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
        markup.add(types.InlineKeyboardButton(f"{option} (0)", callback_data=f"vote_{message.message_id}_{i}"))

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
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy(call):
    item_name = call.data[4:]  # Убираем "buy_" из callback_data
    item_price = SHOP_ITEMS.get(item_name)

    if item_price is None:
        bot.answer_callback_query(call.id, "❌ Товар не найден.")
        return

    user_id = call.from_user.id
    balance = get_user_balance(user_id)  # Используем новую функцию

    if balance < item_price:
        bot.answer_callback_query(call.id, f"❌ Недостаточно монет. Ваш баланс: {balance} монет.")
        return

    # Если покупается должность
    if item_name in ["⭐ Модератор", "👑 Администратор", "👑 Владелец", "⭐ Мл. админ"]:
        bot.answer_callback_query(call.id, "❌ Должности можно покупать только в группах.")
        return

    # Если покупается иммунитет к бану
    if item_name == "🛡 Иммунитет к бану (1)":
        immune_users = load_immune_users()
        immune_users[user_id] = immune_users.get(user_id, 0) + 1
        save_immune_users(immune_users)
        remove_coins(user_id, item_price)
        bot.answer_callback_query(call.id, f"✅ Вы купили иммунитет к бану. Осталось {immune_users[user_id]} иммунитетов.")
        return

    # Обычная покупка
    remove_coins(user_id, item_price)
    bot.answer_callback_query(call.id, f"✅ Вы успешно купили {item_name} за {item_price} монет!")

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
        
def add_coins(user_id, amount):
    """Добавить монеты пользователю."""
    uid = str(user_id)
    if uid not in coins_data:
        coins_data[uid] = {"coins": 0}
    coins_data[uid]["coins"] += amount
    save_coins()

def has_immunity(user_id):
    """Проверяет, есть ли у пользователя иммунитет к бану."""
    immune_users = load_immune_users()
    if str(user_id) in immune_users and immune_users[str(user_id)] > 0:
        immune_users[str(user_id)] -= 1
        if immune_users[str(user_id)] == 0:
            del immune_users[str(user_id)]  # Удаляем запись, если иммунитет закончился
        save_immune_users(immune_users)
        return True
    return False


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("🚀 Запуск бота...")
    
    # Укажите ID вашей группы и темы
    GROUP_CHAT_ID = -1002241393389  # Замените на ваш chat_id
    TOPIC_ID = 1803  # Замените на ваш topic_id

    # Запуск ежедневного сообщения
    schedule_daily_message(GROUP_CHAT_ID, TOPIC_ID)

    # Бесконечный цикл для polling
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
