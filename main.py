from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import filters
import sqlite3
import os
import time

def create_database():
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            photo TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
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
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    timestamp = int(time.time())
    photo_path = f"photos/{user_id}_{timestamp}.jpg"

    photo_file = await update.message.photo[-1].get_file()
    os.makedirs("photos", exist_ok=True)
    await photo_file.download_to_drive(photo_path)

    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cards (user_id, photo)
        VALUES (?, ?)
    ''', (user_id, photo_path))
    conn.commit()
    conn.close()

    await update.message.reply_text("📸 Фотография сохранена. Теперь отправьте имя для этой карты.")

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    name = update.message.text

    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cards
        SET name = ?
        WHERE user_id = ? AND name IS NULL
    ''', (name, user_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Имя '{name}' успешно присвоено вашей карте.")

async def list_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM cards')
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

async def handle_card_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card_id = int(query.data.split("_")[1])

    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('SELECT photo FROM cards WHERE id = ?', (card_id,))
    card = cursor.fetchone()
    conn.close()

    if not card:
        await query.edit_message_text("❌ Карта не найдена.")
    else:
        await query.message.reply_photo(open(card[0], 'rb'))

def main():
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_cards))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))

    application.add_handler(CallbackQueryHandler(handle_card_selection))

    application.run_polling()

if __name__ == '__main__':
    main()