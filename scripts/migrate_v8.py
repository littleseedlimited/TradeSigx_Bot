import sqlite3
import os

db_path = 'tradesigx.db'
if os.path.exists('/data'):
    db_path = '/data/tradesigx.db'

print(f"Migrating database at {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing columns
cursor.execute("PRAGMA table_info(users)")
columns = [row[1] for row in cursor.fetchall()]

# Columns to add if missing
missing_columns = [
    ("default_lot", "FLOAT DEFAULT 0.01"),
    ("risk_per_trade", "FLOAT DEFAULT 1.0"),
    ("max_daily_loss", "FLOAT DEFAULT 5.0"),
    ("wallet_balance", "FLOAT DEFAULT 0.0"),
    ("wallet_currency", "VARCHAR DEFAULT 'USD'"),
    ("wallet_address", "VARCHAR"),
    ("timezone", "VARCHAR DEFAULT 'UTC'"),
    ("notifications_enabled", "BOOLEAN DEFAULT 1"), # SQLite Boolean is 0/1
    ("bulk_scan_config", "VARCHAR DEFAULT 'BTC/USDT,ETH/USDT,GC=F,EURUSD=X,GBPUSD=X'"),
    ("external_wallets", "TEXT"),
    ("autotrade_enabled", "BOOLEAN DEFAULT 0"),
    ("autotrade_min_confidence", "FLOAT DEFAULT 75.0"),
    ("autotrade_max_trades", "INTEGER DEFAULT 5"),
    ("autotrade_assets", "VARCHAR DEFAULT 'BTC/USDT,ETH/USDT,GC=F'"),
    ("full_name", "VARCHAR"),
    ("email", "VARCHAR"),
    ("phone", "VARCHAR"),
    ("country", "VARCHAR"),
    ("kyc_status", "VARCHAR DEFAULT 'not_submitted'"),
    ("kyc_id_document", "VARCHAR"),
    ("kyc_selfie", "VARCHAR"),
    ("kyc_submitted_at", "DATETIME"),
    ("kyc_reviewed_at", "DATETIME"),
    ("kyc_rejection_reason", "VARCHAR"),
    ("is_admin", "BOOLEAN DEFAULT 0"),
    ("is_super_admin", "BOOLEAN DEFAULT 0"),
    ("is_banned", "BOOLEAN DEFAULT 0"),
    ("ban_reason", "VARCHAR"),
    ("is_registered", "BOOLEAN DEFAULT 0"),
    ("registration_step", "VARCHAR DEFAULT 'start'"),
    ("terms_accepted", "BOOLEAN DEFAULT 0"),
    ("joined_at", "DATETIME"),
    ("subscription_plan", "VARCHAR DEFAULT 'free'"),
    ("plan_expires_at", "DATETIME"),
    ("signals_used_today", "INTEGER DEFAULT 0"),
    ("last_signal_date", "VARCHAR")
]

for col_name, col_type in missing_columns:
    if col_name not in columns:
        print(f"Adding column: {col_name}")
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            print(f"Error adding {col_name}: {e}")

conn.commit()
conn.close()
print("Migration completed Successfully!")
