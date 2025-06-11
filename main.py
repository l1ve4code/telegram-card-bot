from telegram import LabeledPrice, Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters, \
    CallbackQueryHandler
import sqlite3
import os
import time
from os import environ
from datetime import datetime, timedelta
import textwrap

DATABASE_PATH = os.path.join("data", "discount_cards.db")

def create_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_use TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_use TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_stats (
            card_id INTEGER PRIMARY KEY,
            selection_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS premium_users (
            user_id INTEGER PRIMARY KEY,
            premium_until TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_views (
            user_id INTEGER,
            month_year TEXT,
            views_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, month_year)
        )
    ''')
    conn.commit()
    conn.close()

create_database()

def has_premium_access(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT premium_until FROM premium_users WHERE user_id = ? AND premium_until >= CURRENT_TIMESTAMP
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def was_premium_access(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT premium_until FROM premium_users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def update_user_stats(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    ''', (user_id,))
    cursor.execute('''
        UPDATE users SET last_use = CURRENT_TIMESTAMP WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def add_premium(user_id, premium_until):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
            INSERT OR REPLACE INTO premium_users (user_id, premium_until) VALUES (?, ?)
        ''', (user_id, premium_until))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    premium_until = datetime.now() + timedelta(days=30)

    update_user_stats(user_id)
    if not was_premium_access(user_id):
        add_premium(user_id, premium_until)

    welcome_text = textwrap.dedent("""
    🌟 *Добро пожаловать в клуб обмена персональными скидками!* 🌟
    
    📸 *Как это работает?*
    - ☘️*Получить* карту магазина - используйте команду */list* и я отправлю вам её фотографию
    - ☘️*Загрузить* карту магазина - используйте команду */load* и ваша карта будет загружена для использования
    
    💡 *Наши преимущества:*
    - 🛍 Обменивайтесь скидками с друзьями и коллегами
    - 🌚 Экономьте на покупках
    - ⚡️ Повышайте уровень лояльности ваших карт
    - 🔍 Моментальный поиск нужной карты
    
    📌 *Доступные команды:*
    - */start* - показать это сообщение
    - */list* - список доступных карт
    - */load* - загрузить карту
    """).strip()
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = textwrap.dedent("""
    📸 *Как это работает?*
    - ☘️*Получить* карту магазина - используйте команду */list* и я отправлю вам её фотографию
    - ☘️*Загрузить* карту магазина - используйте команду */load* и ваша карта будет загружена для использования

    📌 *Доступные команды:*
    - */start* - показать это сообщение
    - */list* - список доступных карт
    - */load* - загрузить карту
    """).strip()
    await update.message.reply_text(info_text, parse_mode="Markdown")

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    title = "Покупка премиум-доступа"
    description = "Доступ к премиум-функциям бота на 1 месяц"
    payload = "premium_subscription"
    provider_token = ""
    currency = "XTR"
    prices = [LabeledPrice("Премиум-доступ", 150)]

    await context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        provider_token,
        currency,
        prices,
    )

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload == "premium_subscription":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Ошибка платежа")

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    premium_until = datetime.now() + timedelta(days=30)
    add_premium(user_id, premium_until)
    await update.message.reply_text("🎉 Спасибо за оплату! Ваш премиум-доступ активирован на 1 месяц.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not has_premium_access(user_id):
        await update.message.reply_text("❌ Для загрузки карт необходим премиум-доступ. Используйте команду /buy.")
        return

    update_user_stats(user_id)

    timestamp = int(time.time())
    photo_path = f"photos/{user_id}_{timestamp}.jpg"

    photo_file = await update.message.photo[-1].get_file()
    os.makedirs("photos", exist_ok=True)
    await photo_file.download_to_drive(photo_path)

    context.user_data['photo_path'] = photo_path

    await update.message.reply_text("📸 Фотография сохранена. Теперь отправьте имя для этой карты.")

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not has_premium_access(user_id):
        await update.message.reply_text("❌ Для загрузки карт необходим премиум-доступ. Используйте команду /buy.")
        return

    name = update.message.text.strip()
    name_lower = name.lower()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM cards WHERE LOWER(name) = ?', (name_lower,))
    existing_card = cursor.fetchone()

    if existing_card:
        card_id = existing_card[0]
        cursor.execute('''
            UPDATE cards
            SET user_id = ?, photo = ?
            WHERE id = ?
        ''', (user_id, context.user_data['photo_path'], card_id))
        await update.message.reply_text(f"✅ Карта '{name}' обновлена.")
    else:
        cursor.execute('''
            INSERT INTO cards (user_id, name, photo)
            VALUES (?, ?, ?)
        ''', (user_id, name, context.user_data['photo_path']))
        await update.message.reply_text(f"✅ Имя '{name}' успешно присвоено вашей карте.")

    conn.commit()
    conn.close()

async def list_cards(update_or_query, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    if isinstance(update_or_query, CallbackQuery):
        user_id = update_or_query.from_user.id
        send_method = update_or_query.edit_message_text
    else:
        user_id = update_or_query.from_user.id
        send_method = update_or_query.reply_text

    if not can_view_more_cards(user_id):
        remaining_views = 5 - get_user_monthly_views(user_id)
        await send_method(
            f"❌ Вы достигли лимита просмотров карт на этот месяц ({5 - remaining_views}/5).\n"
            "Для неограниченного доступа к картам используйте команду /buy"
        )
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name FROM cards
        WHERE id IN (SELECT MAX(id) FROM cards GROUP BY LOWER(name))
        LIMIT 10 OFFSET ?
    ''', (page * 10,))
    cards = cursor.fetchall()
    conn.close()

    if not cards:
        await send_method("📭 Больше карт нет.")
        return

    keyboard = [
        [InlineKeyboardButton(card[1], callback_data=f"card_{card[0]}")] for card in cards
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("← Назад", callback_data=f"list_{page - 1}"))
    if len(cards) == 10:
        nav_buttons.append(InlineKeyboardButton("Вперед →", callback_data=f"list_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    remaining_views = 5 - get_user_monthly_views(user_id)
    views_info = f"\n\n👁 Осталось просмотров в этом месяце: {remaining_views}/5" if not has_premium_access(user_id) else ""

    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_method(
        f"📋 Страница {page + 1}. Выберите карту:{views_info}",
        reply_markup=reply_markup
    )

async def handle_list_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("list_"):
        page = int(query.data.split("_")[1])
        await list_cards(query, context, page)
    else:
        await handle_card_selection(update, context)

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"🆔 Ваш user_id: {user_id}")

async def grant_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ Используйте команду так: /grant_premium <user_id> <пароль>")
        return

    user_id = context.args[0]
    password = context.args[1]
    admin_password = environ.get("ADMIN_PASSWORD")

    if password != admin_password:
        await update.message.reply_text("❌ Неверный пароль.")
        return

    premium_until = datetime.now() + timedelta(days=30)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO premium_users (user_id, premium_until) VALUES (?, ?)
    ''', (user_id, premium_until))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🎉 Пользователю с user_id {user_id} выдан премиум-доступ на 1 месяц.")

async def delete_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ Формат: /delete <имя_карты> <пароль>")
        return

    *card_name_words, password = context.args
    card_name = " ".join(card_name_words).strip()
    admin_password = environ.get("ADMIN_PASSWORD")

    if password != admin_password:
        await update.message.reply_text("❌ Неверный пароль.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM cards WHERE LOWER(name) = LOWER(?)', (card_name,))
    card = cursor.fetchone()

    if not card:
        await update.message.reply_text(f"❌ Карта '{card_name}' не найдена.")
        conn.close()
        return

    cursor.execute('DELETE FROM cards WHERE LOWER(name) = LOWER(?)', (card_name,))
    conn.commit()

    cursor.execute('DELETE FROM card_stats WHERE card_id = ?', (card[0],))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Карта '{card_name}' удалена.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔒 Для доступа к статистике укажите пароль.")
        return

    user_password = context.args[0]
    admin_password = environ.get("ADMIN_PASSWORD")

    if user_password != admin_password:
        await update.message.reply_text("❌ Неверный пароль.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM cards')
    users_with_cards = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM cards')
    total_cards = cursor.fetchone()[0]

    avg_cards_per_user = total_cards / users_with_cards if users_with_cards > 0 else 0

    retention_period = 7
    retention_date = datetime.now() - timedelta(days=retention_period)
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id) FROM users
        WHERE last_use >= ?
    ''', (retention_date,))
    retained_users = cursor.fetchone()[0]
    retention_rate = (retained_users / total_users) * 100 if total_users > 0 else 0

    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users WHERE last_use >= DATE("now", "-7 days")')
    active_users_last_7_days = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE first_use >= DATE("now", "-7 days")')
    new_users_last_7_days = cursor.fetchone()[0]

    conversion_rate = (users_with_cards / total_users) * 100 if total_users > 0 else 0

    cursor.execute('SELECT AVG(JULIANDAY(last_use) - JULIANDAY(first_use)) FROM users')
    avg_usage_duration = cursor.fetchone()[0] or 0

    cursor.execute('''
        SELECT c.name, COALESCE(cs.selection_count, 0) as selection_count 
        FROM cards c
        LEFT JOIN card_stats cs ON c.id = cs.card_id
        ORDER BY selection_count DESC
        LIMIT 5
    ''')
    top_cards = cursor.fetchall()

    cursor.execute('SELECT COUNT(*) FROM cards WHERE created_at >= DATE("now", "-7 days")')
    cards_last_7_days = cursor.fetchone()[0]

    cursor.execute('''
        SELECT AVG(card_count) 
        FROM (
            SELECT user_id, COUNT(*) as card_count 
            FROM cards 
            GROUP BY user_id
        )
    ''')
    avg_cards_per_active_user = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM premium_users')
    premium_users = cursor.fetchone()[0]

    premium_conversion = (premium_users / total_users) * 100 if total_users > 0 else 0

    cursor.execute('SELECT COUNT(*) FROM premium_users WHERE premium_until >= CURRENT_TIMESTAMP')
    active_premium_users = cursor.fetchone()[0]

    stats_text = textwrap.dedent(f"""
        📊 *Статистика использования бота:*

        👤 *Всего пользователей:* {total_users}
        📂 *Пользователей с картами:* {users_with_cards}
        💎 Пользователей с премиумом: {premium_users}
        🚀 Конверсия в премиум: {premium_conversion:.2f}%
        💎 Активных премиум-подписок: {active_premium_users}
        
        📦 *Всего карт:* {total_cards}
        📈 *Среднее количество карт на пользователя:* {avg_cards_per_user:.2f}
        📅 *Retention rate (за последние 7 дней):* {retention_rate:.2f}%

        🚀 *Активные пользователи (за последние 7 дней):* {active_users_last_7_days}
        🆕 *Новые пользователи (за последние 7 дней):* {new_users_last_7_days}
        🔄 *Конверсия в загрузку карт:* {conversion_rate:.2f}%
        ⏳ *Среднее время между первым и последним использованием:* {avg_usage_duration:.2f} дней

        🏆 *Топ-5 популярных карт:*
    """).strip()

    for i, (name, count) in enumerate(top_cards, start=1):
        stats_text += f"\n  {i}. {name} (выбрана {count} раз)"

    stats_text += textwrap.dedent(f"""
        📅 *Карт загружено за последние 7 дней:* {cards_last_7_days}
        📦 *Среднее количество карт на активного пользователя:* {avg_cards_per_active_user:.2f}
    """).strip()

    await update.message.reply_text(stats_text, parse_mode="Markdown")

    conn.close()

async def handle_card_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not can_view_more_cards(user_id):
        await query.edit_message_text(
            f"❌ Вы достигли лимита просмотров карт на этот месяц.\n"
            "Для неограниченного доступа к картам используйте команду /buy"
        )
        return

    card_id = int(query.data.split("_")[1])
    increment_user_views(user_id)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO card_stats (card_id) VALUES (?)
    ''', (card_id,))
    cursor.execute('''
        UPDATE card_stats SET selection_count = selection_count + 1 WHERE card_id = ?
    ''', (card_id,))
    conn.commit()

    cursor.execute('SELECT photo FROM cards WHERE id = ?', (card_id,))
    card = cursor.fetchone()
    conn.close()

    if not card:
        await query.edit_message_text("❌ Карта не найдена.")
    else:
        await query.message.reply_photo(open(card[0], 'rb'))

async def load_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
        
    load_instructions = textwrap.dedent("""
    📸 *Как загрузить карту:*
    
    1️⃣ Отправьте фотографию карты
    2️⃣ После загрузки фото, отправьте название карты
    
    💡 *Советы:*
    - Убедитесь, что фото четкое и хорошо читаемое
    - Название должно быть понятным и уникальным
    - Можно использовать существующее название для обновления карты
    """).strip()
    
    await update.message.reply_text(load_instructions, parse_mode="Markdown")

def get_current_month_year():
    return datetime.now().strftime("%Y-%m")

def get_user_monthly_views(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    current_month = get_current_month_year()
    
    cursor.execute('''
        SELECT views_count FROM card_views 
        WHERE user_id = ? AND month_year = ?
    ''', (user_id, current_month))
    result = cursor.fetchone()
    
    if result is None:
        cursor.execute('''
            INSERT INTO card_views (user_id, month_year, views_count)
            VALUES (?, ?, 0)
        ''', (user_id, current_month))
        conn.commit()
        views = 0
    else:
        views = result[0]
    
    conn.close()
    return views

def increment_user_views(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    current_month = get_current_month_year()
    
    cursor.execute('''
        INSERT INTO card_views (user_id, month_year, views_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, month_year) 
        DO UPDATE SET views_count = views_count + 1
    ''', (user_id, current_month))
    
    conn.commit()
    conn.close()

def can_view_more_cards(user_id):
    if has_premium_access(user_id):
        return True
    return get_user_monthly_views(user_id) < 5

def main():
    bot_token = environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("Необходимо указать BOT_TOKEN в переменных окружения.")

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("list", lambda u, c: list_cards(u.message, c, page=0)))
    application.add_handler(CommandHandler("load", load_command))
    application.add_handler(CommandHandler("buy", start_payment))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("myid", my_id))
    application.add_handler(CommandHandler("grant_premium", grant_premium))
    application.add_handler(CommandHandler("delete", delete_card))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))

    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    application.add_handler(CallbackQueryHandler(handle_list_pagination))

    application.run_polling()

if __name__ == '__main__':
    main()