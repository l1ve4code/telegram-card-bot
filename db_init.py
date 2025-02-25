import sqlite3

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
