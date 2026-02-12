import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple

DB_FILE = "database/data/users.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
   
    # Создаём таблицы, если нет
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            reg_date TEXT,
            got_free INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payment_id TEXT UNIQUE,
            tarif TEXT,
            days INTEGER,
            created_at TEXT,
            status TEXT DEFAULT 'pending',
            metadata TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            uuid TEXT UNIQUE,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            review_text TEXT,
            created_at TEXT
        )
    ''')
   
    # Миграция: добавляем metadata, если столбца нет
    try:
        c.execute("ALTER TABLE payments ADD COLUMN metadata TEXT")
        print("Добавлен столбец metadata в таблицу payments")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            pass # столбец уже есть
        else:
            raise e
   
    conn.commit()
    conn.close()

def add_user_if_new(user_id: int, username: str) -> bool:
    """Добавляет пользователя если новый. Возвращает True если новый"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO users (user_id, username, reg_date) VALUES (?, ?, ?)",
                  (user_id, username, reg_date))
        conn.commit()
        conn.close()
        return True  # новый
    conn.close()
    return False

def user_got_free(user_id: int) -> bool:
    """Проверяет получал ли пользователь бесплатные дни"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT got_free FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def mark_got_free(user_id: int):
    """Отмечает что пользователь получил бесплатные дни"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET got_free = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user_subscriptions(user_id: int) -> List[Tuple[str, str]]:
    """Получает активные подписки пользователя"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT uuid, created_at FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,))
    subs = c.fetchall()
    conn.close()
    return subs

def add_subscription(user_id: int, uuid: str) -> bool:
    """Добавляет новую подписку в БД"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"ВСТАВКА НОВОЙ ПОДПИСКИ: user={user_id}, uuid={uuid}, created_at={created_at}")
        
        c.execute("""
            INSERT INTO subscriptions (user_id, uuid, created_at, status)
            VALUES (?, ?, ?, 'active')
        """, (user_id, uuid, created_at))
        conn.commit()
        
        # Проверка вставки
        c.execute("SELECT status FROM subscriptions WHERE uuid = ?", (uuid,))
        status_after = c.fetchone()[0]
        print(f"СТАТУС СРАЗУ ПОСЛЕ ВСТАВКИ: {status_after}")
        
        conn.close()
        return True
        
    except Exception as db_err:
        print(f"Ошибка записи новой подписки в БД для user={user_id}: {db_err}")
        return False

def add_payment(user_id: int, payment_id: str, tarif: str, days: int, metadata: str = None):
    """Добавляет платеж в БД"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO payments (user_id, payment_id, tarif, days, created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        payment_id,
        tarif,
        days,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        metadata
    ))
    conn.commit()
    conn.close()

def update_subscription_status(uuid: str, status: str):
    """Обновляет статус подписки"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE subscriptions SET status = ? WHERE uuid = ?", (status, uuid))
    conn.commit()
    conn.close()

def add_review(user_id: int, username: str, review_text: str):
    """Добавляет отзыв в БД"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO reviews (user_id, username, review_text, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, review_text, created_at))
    conn.commit()
    
    # Получаем номер отзыва (ID последней записи)
    review_id = c.lastrowid
    conn.close()
    return review_id

def get_review_by_id(review_id: int):
    """Получает отзыв по ID"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_latest_subscription(user_id: int) -> Optional[str]:
    """Получает последнюю активную подписку пользователя"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT uuid FROM subscriptions 
        WHERE user_id = ? AND status = 'active' 
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_active_users() -> List[int]:
    """Получает всех пользователей с активными подписками"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM subscriptions WHERE status = 'active'")
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()
    return user_ids

def get_user_stats():
    """Получает статистику пользователей"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Топ пользователи по активности
    c.execute("""
        SELECT u.user_id, u.username, COUNT(s.id) as sub_count
        FROM users u
        LEFT JOIN subscriptions s ON u.user_id = s.user_id
        GROUP BY u.user_id
        ORDER BY sub_count DESC
        LIMIT 10
    """)
    top_users = c.fetchall()
    
    conn.close()
    return {"top_users": top_users}

def get_payment_stats():
    """Получает статистику платежей"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Статистика по тарифам
    c.execute("""
        SELECT tarif, COUNT(*) as count, SUM(days) as total_days
        FROM payments 
        WHERE status = 'completed'
        GROUP BY tarif
        ORDER BY count DESC
    """)
    tarif_stats = c.fetchall()
    
    conn.close()
    return {"tarif_stats": tarif_stats}

def search_user(query: str):
    """Поиск пользователя по ID или username"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if query.isdigit():
        c.execute("SELECT * FROM users WHERE user_id = ?", (int(query),))
    else:
        c.execute("SELECT * FROM users WHERE username LIKE ?", (f"%{query}%",))
    
    result = c.fetchone()
    conn.close()
    return result

def get_pending_yookassa_payments():
     """Возвращает все платежи ЮKassa со статусом pending"""
     conn = sqlite3.connect(DB_FILE)
     c = conn.cursor()
     c.execute("""
         SELECT payment_id
         FROM payments
         WHERE status = 'pending'
     """) 

     rows = c.fetchall()
     conn.close()

     return [{"payment_id": row[0]} for row in rows]


def mark_payment_as_completed(payment_id: str):
     """Помечает платёж как обработанный"""
     conn = sqlite3.connect(DB_FILE)
     c = conn.cursor()

     c.execute("""
         UPDATE payments
         SET status = 'completed'
         WHERE payment_id = ?
     """, (payment_id,))

     conn.commit()
     conn.close()

