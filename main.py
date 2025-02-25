from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import filters
import sqlite3
import os
import random

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для обмена скидочными картами. "
        "Отправь мне одну фотографию скидочной карты и присвой ей имя."
    )

# Обработка фотографии
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Сохраняем фотографию
    photo_file = await update.message.photo[-1].get_file()  # Берем фото с наивысшим разрешением
    photo_path = f"photos/{user_id}_{random.randint(0,999)}.jpg"

    os.makedirs("photos", exist_ok=True)
    await photo_file.download_to_drive(photo_path)

    # Сохраняем информацию в базе данных
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cards (user_id, photo)
        VALUES (?, ?)
    ''', (user_id, photo_path))
    conn.commit()
    conn.close()

    await update.message.reply_text("Фотография сохранена. Теперь отправьте имя для этой карты.")

# Обработка имени
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    name = update.message.text

    # Обновляем запись в базе данных
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cards
        SET name = ?
        WHERE user_id = ? AND name IS NULL
    ''', (name, user_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Имя '{name}' успешно присвоено вашей карте.")

# Команда /list
async def list_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM cards')
    cards = cursor.fetchall()
    conn.close()

    if not cards:
        await update.message.reply_text("Пока нет доступных карт.")
    else:
        # Создаем кнопки для каждой карты
        keyboard = [
            [InlineKeyboardButton(card[1], callback_data=f"card_{card[0]}")] for card in cards
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите карту:", reply_markup=reply_markup)

# Обработка выбора карты
async def handle_card_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card_id = int(query.data.split("_")[1])  # Извлекаем ID карты из callback_data

    # Получаем информацию о карте из базы данных
    conn = sqlite3.connect('discount_cards.db')
    cursor = conn.cursor()
    cursor.execute('SELECT photo FROM cards WHERE id = ?', (card_id,))
    card = cursor.fetchone()
    conn.close()

    if not card:
        await query.edit_message_text("Карта не найдена.")
    else:
        # Отправляем фотографию
        await query.message.reply_photo(open(card[0], 'rb'))

def main():
    application = Application.builder().token("7502824728:AAGhbNavfGdWydiQn_DqIgTigYhHLQyd8T8").build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_cards))

    # Регистрация обработчиков сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))

    # Регистрация обработчика callback-запросов (выбор карты)
    application.add_handler(CallbackQueryHandler(handle_card_selection))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()