import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), 'hotels.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'client',
        full_name TEXT,
        phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    for col in [
        ("role", "TEXT NOT NULL DEFAULT 'client'"),
        ("full_name", "TEXT"),
        ("phone", "TEXT"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col[0]} {col[1]}")
        except:
            pass

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
            ("admin", hash_password("1234"), "admin", "Administrator")
        )
    else:
        cursor.execute("UPDATE users SET role='admin' WHERE username='admin'")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hotels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        region TEXT NOT NULL,
        price INTEGER NOT NULL,
        stars INTEGER NOT NULL,
        wifi INTEGER DEFAULT 0,
        breakfast INTEGER DEFAULT 0,
        parking INTEGER DEFAULT 0,
        description TEXT,
        rooms_total INTEGER DEFAULT 10
    )
    """)

    for col in [
        ("description", "TEXT"),
        ("rooms_total", "INTEGER DEFAULT 10"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE hotels ADD COLUMN {col[0]} {col[1]}")
        except:
            pass

    cursor.execute("SELECT COUNT(*) FROM hotels")
    if cursor.fetchone()[0] == 0:
        sample = [
            ("Hilton Tashkent", "Toshkent", 400, 4, 1, 1, 0),
            ("Hyatt Regency", "Toshkent", 600, 5, 1, 1, 1),
            ("Intercontinental", "Toshkent", 500, 5, 1, 1, 0),
            ("Samarkand Plaza", "Samarkand", 250, 3, 1, 0, 1),
            ("Silk Road Hotel", "Buxoro", 180, 3, 1, 1, 0),
        ]
        cursor.executemany(
            "INSERT INTO hotels (name, region, price, stars, wifi, breakfast, parking) VALUES (?,?,?,?,?,?,?)",
            sample
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hotel_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        check_in DATE NOT NULL,
        check_out DATE NOT NULL,
        guests INTEGER DEFAULT 1,
        total_price INTEGER,
        status TEXT DEFAULT 'pending',
        note TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (hotel_id) REFERENCES hotels(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

def check_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(username, password, full_name, phone):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role, full_name, phone) VALUES (?, ?, ?, ?, ?)",
            (username, hash_password(password), 'client', full_name, phone)
        )
        conn.commit()
        conn.close()
        return True, "Muvaffaqiyatli ro'yxatdan o'tdingiz!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bu foydalanuvchi nomi allaqachon band!"
