"""
Database Migration Script for TradeSigx v5.0
Adds new columns to existing users table and creates new tables
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'tradesigx.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing columns in users table
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"Existing columns: {existing_columns}")
    
    # New columns to add to users table
    new_columns = [
        ("full_name", "TEXT"),
        ("email", "TEXT"),
        ("phone", "TEXT"),
        ("country", "TEXT"),
        ("is_registered", "INTEGER DEFAULT 0"),
        ("registration_step", "TEXT DEFAULT 'start'"),
        ("terms_accepted", "INTEGER DEFAULT 0"),
        ("subscription_plan", "TEXT DEFAULT 'free'"),
        ("plan_expires_at", "DATETIME"),
        ("signals_used_today", "INTEGER DEFAULT 0"),
        ("last_signal_date", "TEXT"),
        ("kyc_status", "TEXT DEFAULT 'not_submitted'"),
        ("kyc_id_document", "TEXT"),
        ("kyc_selfie", "TEXT"),
        ("kyc_submitted_at", "DATETIME"),
        ("kyc_reviewed_at", "DATETIME"),
        ("kyc_rejection_reason", "TEXT"),
        ("is_admin", "INTEGER DEFAULT 0"),
        ("is_super_admin", "INTEGER DEFAULT 0"),
        ("is_banned", "INTEGER DEFAULT 0"),
        ("ban_reason", "TEXT"),
    ]
    
    # Add missing columns
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"[OK] Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Column {col_name}: {e}")
    
    # Mark existing users as registered (they were using the bot before)
    cursor.execute("UPDATE users SET is_registered = 1 WHERE is_registered IS NULL OR is_registered = 0")
    print("[OK] Marked existing users as registered")
    
    # Create subscription_plans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            display_name TEXT,
            price_usd REAL,
            signals_per_day INTEGER,
            features TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    print("[OK] Created subscription_plans table")
    
    # Seed plans if empty
    cursor.execute("SELECT COUNT(*) FROM subscription_plans")
    if cursor.fetchone()[0] == 0:
        plans = [
            ("free", "Free", 0, 3, '{"delay": "15min", "radar": false, "support": "community"}', 1),
            ("basic", "Basic", 9.99, 15, '{"delay": "realtime", "radar": false, "support": "email"}', 1),
            ("pro", "Pro", 29.99, -1, '{"delay": "realtime", "radar": true, "support": "priority"}', 1),
            ("vip", "VIP", 99.99, -1, '{"delay": "realtime", "radar": true, "support": "dedicated", "early_access": true}', 1),
        ]
        cursor.executemany("INSERT INTO subscription_plans (name, display_name, price_usd, signals_per_day, features, is_active) VALUES (?, ?, ?, ?, ?, ?)", plans)
        print("[OK] Seeded subscription plans")
    
    # Create payment_transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            currency TEXT DEFAULT 'USD',
            payment_method TEXT,
            transaction_ref TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            plan_purchased TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            extra_data TEXT
        )
    """)
    print("[OK] Created payment_transactions table")
    
    conn.commit()
    conn.close()
    print("\n[DONE] Migration complete!")

if __name__ == "__main__":
    migrate()

if __name__ == "__main__":
    migrate()
