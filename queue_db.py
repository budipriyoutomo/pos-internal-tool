import sqlite3
from datetime import datetime

import os
 
import sys

def get_base_path():
    # 🔥 kalau jalan dari EXE
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

    # 🔧 kalau jalan dari source
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
DB_NAME = os.path.join(BASE_DIR, "queue.db")

# ==============================
# 🔧 INIT DB
# ==============================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 🔥 QUEUE TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        retry_count INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    # 🔥 SYNC STATE (last_sync)
    c.execute("""
    CREATE TABLE IF NOT EXISTS sync_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()

def recreate_db():
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"🗑️ Database lama dihapus: {DB_NAME}")
        except Exception as e:
            print(f"⚠️ Gagal menghapus database lama: {e}")
    init_db()
    print("🆕 Database baru berhasil dibuat")


# ==============================
# 📥 INSERT QUEUE
# ==============================
def insert_queue(payload: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "INSERT INTO queue (payload, created_at) VALUES (?, ?)",
        (payload, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()


# ==============================
# 📤 GET PENDING
# ==============================
def get_pending(limit=10):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT id, payload, retry_count 
        FROM queue
        WHERE status='pending'
        ORDER BY id ASC
        LIMIT ?
    """, (limit,))

    rows = c.fetchall()
    conn.close()
    return rows


# ==============================
# ✅ MARK SENT
# ==============================
def mark_sent(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("DELETE FROM queue WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ==============================
# 🔁 RETRY
# ==============================
def increase_retry(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        UPDATE queue
        SET retry_count = retry_count + 1
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()


# ==============================
# 🔑 LAST SYNC
# ==============================
def get_last_sync():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT value FROM sync_state WHERE key='last_sync'")
    row = c.fetchone()

    conn.close()
    return row[0] if row else None


def update_last_sync(value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO sync_state (key, value)
        VALUES ('last_sync', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (value,))

    conn.commit()
    conn.close()