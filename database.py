import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import hashlib

DB_PATH = "vpn_bot.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            remna_uuid TEXT,
            subscription_end TEXT,
            is_trial_used INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            referrer_id INTEGER,
            balance_days INTEGER DEFAULT 0,
            created_at TEXT,
            referral_code TEXT UNIQUE
        )
    ''')
    
    # Таблица платежей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount INTEGER,
            months INTEGER,
            payment_system TEXT,
            external_id TEXT UNIQUE,
            status TEXT,
            created_at TEXT,
            paid_at TEXT
        )
    ''')
    
    # Таблица промокодов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            bonus_days INTEGER,
            usage_limit INTEGER,
            used_count INTEGER DEFAULT 0,
            expires_at TEXT,
            created_by INTEGER
        )
    ''')
    
    # Таблица для статистики админов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_id INTEGER,
            details TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


# === USER FUNCTIONS ===

def get_user(telegram_id: int) -> Optional[Dict]:
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(telegram_id: int, username: str, full_name: str, referrer_id: int = None) -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    
    # Генерируем уникальный referral_code
    import hashlib
    referral_code = hashlib.md5(f"{telegram_id}{datetime.now()}".encode()).hexdigest()[:8]
    
    # Генерируем UUID для панели Remnawave
    import uuid
    remna_uuid = str(uuid.uuid4())
    
    cursor.execute('''
        INSERT INTO users (telegram_id, username, full_name, remna_uuid, created_at, referral_code, referrer_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (telegram_id, username, full_name, remna_uuid, datetime.now().isoformat(), referral_code, referrer_id))
    
    conn.commit()
    conn.close()
    
    # Если есть реферер, начисляем бонус
    if referrer_id:
        update_subscription(referrer_id, REFERRAL_BONUS_DAYS)
    
    return get_user(telegram_id)

def update_subscription(telegram_id: int, days_to_add: int) -> datetime:
    """Добавляет дни к подписке и возвращает новую дату окончания"""
    conn = get_db()
    user = get_user(telegram_id)
    
    current_end = datetime.fromisoformat(user["subscription_end"]) if user.get("subscription_end") else datetime.now()
    new_end = max(current_end, datetime.now()) + timedelta(days=days_to_add)
    
    conn.execute(
        "UPDATE users SET subscription_end = ? WHERE telegram_id = ?",
        (new_end.isoformat(), telegram_id)
    )
    conn.commit()
    conn.close()
    return new_end

def set_trial_used(telegram_id: int):
    conn = get_db()
    conn.execute(
        "UPDATE users SET is_trial_used = 1 WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    conn.close()

def set_remna_uuid(telegram_id: int, remna_uuid: str):
    conn = get_db()
    conn.execute(
        "UPDATE users SET remna_uuid = ? WHERE telegram_id = ?",
        (remna_uuid, telegram_id)
    )
    conn.commit()
    conn.close()

def get_all_users() -> List[Dict]:
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(u) for u in users]

def ban_user(telegram_id: int):
    conn = get_db()
    conn.execute("UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

def unban_user(telegram_id: int):
    conn = get_db()
    conn.execute("UPDATE users SET is_banned = 0 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

def get_active_users_count() -> int:
    conn = get_db()
    now = datetime.now().isoformat()
    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE subscription_end > ? AND is_banned = 0",
        (now,)
    ).fetchone()[0]
    conn.close()
    return count

def get_total_users_count() -> int:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

def get_total_revenue() -> int:
    conn = get_db()
    total = conn.execute(
        "SELECT SUM(amount) FROM payments WHERE status = 'paid'"
    ).fetchone()[0] or 0
    conn.close()
    return total


# === PAYMENT FUNCTIONS ===

def add_payment(telegram_id: int, amount: int, months: int, payment_system: str, external_id: str):
    conn = get_db()
    conn.execute('''
        INSERT INTO payments (telegram_id, amount, months, payment_system, external_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    ''', (telegram_id, amount, months, payment_system, external_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def mark_payment_paid(external_id: str, paid_at: str = None) -> bool:
    conn = get_db()
    payment = conn.execute(
        "SELECT * FROM payments WHERE external_id = ?", (external_id,)
    ).fetchone()
    
    if payment and payment["status"] != "paid":
        conn.execute(
            "UPDATE payments SET status = 'paid', paid_at = ? WHERE external_id = ?",
            (paid_at or datetime.now().isoformat(), external_id)
        )
        # Начисляем дни пользователю
        update_subscription(payment["telegram_id"], payment["months"] * 30)
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


# === PROMOCODE FUNCTIONS ===

def add_promocode(code: str, bonus_days: int, usage_limit: int, expires_days: int, created_by: int):
    conn = get_db()
    expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
    conn.execute('''
        INSERT INTO promocodes (code, bonus_days, usage_limit, expires_at, created_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (code, bonus_days, usage_limit, expires_at, created_by))
    conn.commit()
    conn.close()

def use_promocode(code: str, telegram_id: int) -> Optional[int]:
    conn = get_db()
    promo = conn.execute(
        "SELECT * FROM promocodes WHERE code = ? AND usage_limit > used_count AND expires_at > ?",
        (code, datetime.now().isoformat())
    ).fetchone()
    
    if not promo:
        conn.close()
        return None
    
    conn.execute(
        "UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?",
        (code,)
    )
    conn.commit()
    conn.close()
    
    # Начисляем бонусные дни
    update_subscription(telegram_id, promo["bonus_days"])
    return promo["bonus_days"]


# === ADMIN LOGS ===

def add_admin_log(admin_id: int, action: str, target_id: int = None, details: str = None):
    conn = get_db()
    conn.execute('''
        INSERT INTO admin_logs (admin_id, action, target_id, details, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, action, target_id, details, datetime.now().isoformat()))
    conn.commit()
    conn.close()
