from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import filters
import sqlite3
import os
import time
import textwrap
from os import environ
from datetime import datetime, timedelta

def create_database():
    conn = sqlite3.connect('discount_cards.db')
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
    conn.commit()
    conn.close()

create_database()

def update_user_stats(user_id):
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    ''', (user_id,))
    cursor.execute('''
        UPDATE users SET last_use = CURRENT_TIMESTAMP WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_user_stats(update.message.from_user.id)
    welcome_text = textwrap.dedent("""
    🌟 *Добро пожаловать в бота для обмена скидочными картами!* 🌟
    
    📸 *Как это работает?*
    1. Отправьте мне *одну фотографию* вашей скидочной карты.
    2. Присвойте карте *уникальное имя*, чтобы другие могли её найти.
    3. Используйте команду `/list`, чтобы просмотреть все доступные карты.
    4. Выберите карту из списка, и я отправлю вам её фотографию.
    
    💡 *Преимущества:*
    - 🛍️ Обменивайтесь скидками с друзьями и коллегами.
    - 📂 Удобное хранение всех карт в одном месте.
    - 🔍 Быстрый поиск нужной карты.
    
    📌 *Доступные команды:*
    - `/start` - показать это сообщение.
    - `/list` - показать список всех карт.
    
    🚀 *Начните прямо сейчас!* Отправьте мне фотографию вашей скидочной карты.
    """).strip()
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
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
    name = update.message.text.strip()
    name_lower = name.lower()

    conn = sqlite3.connect('discount_cards.db')
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

async def list_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_user_stats(update.message.from_user.id)
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name FROM cards
        WHERE id IN (
            SELECT MAX(id) FROM cards GROUP BY LOWER(name)
        )
    ''')
    cards = cursor.fetchall()
    conn.close()

    if not cards:
        await update.message.reply_text("📭 Пока нет доступных карт.")
    else:
        keyboard = [
            [InlineKeyboardButton(card[1], callback_data=f"card_{card[0]}")] for card in cards
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 Выберите карту:", reply_markup=reply_markup)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔒 Для доступа к статистике укажите пароль.")
        return

    user_password = context.args[0]
    admin_password = environ.get("ADMIN_PASSWORD")

    if user_password != admin_password:
        await update.message.reply_text("❌ Неверный пароль.")
        return

    conn = sqlite3.connect('discount_cards.db')
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

    stats_text = textwrap.dedent(f"""
    📊 *Статистика использования бота:*
    
    👤 *Всего пользователей:* {total_users}
    📂 *Пользователей с картами:* {users_with_cards}
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
        stats_text += f"\n  {i}. {name} (выбрана {count} раз)\n"

    stats_text += textwrap.dedent(f"""
    📅 *Карт загружено за последние 7 дней:* {cards_last_7_days}
    📦 *Среднее количество карт на активного пользователя:* {avg_cards_per_active_user:.2f}
    """).strip()

    await update.message.reply_text(stats_text, parse_mode="Markdown")

    conn.close()

async def handle_card_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card_id = int(query.data.split("_")[1])

    conn = sqlite3.connect('discount_cards.db')
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

def main():
    bot_token = environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("Необходимо указать BOT_TOKEN в переменных окружения.")

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_cards))
    application.add_handler(CommandHandler("stats", stats))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))

    application.add_handler(CallbackQueryHandler(handle_card_selection))

    application.run_polling()

if __name__ == '__main__':
    main()