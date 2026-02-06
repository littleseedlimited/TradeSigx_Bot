import sqlite3
import os

db_path = 'tradesigx.db'

if not os.path.exists(db_path):
    print("Database file not found. Skipping migration.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check users table
cursor.execute("PRAGMA table_info(users)")
existing_columns = [col[1] for col in cursor.fetchall()]

missing_columns = [
    ("default_lot", "FLOAT DEFAULT 0.01"),
    ("risk_per_trade", "FLOAT DEFAULT 1.0"),
    ("max_daily_loss", "FLOAT DEFAULT 5.0"),
    ("wallet_balance", "FLOAT DEFAULT 1000.0"),
    ("wallet_currency", "TEXT DEFAULT 'USD'"),
    ("wallet_address", "TEXT"),
    ("timezone", "TEXT DEFAULT 'UTC'"),
    ("joined_at", "DATETIME"),
    ("is_premium", "BOOLEAN DEFAULT 0"),
    ("notifications_enabled", "BOOLEAN DEFAULT 1"),
    ("bulk_scan_config", "TEXT DEFAULT 'BTCUSD,ETHUSD,Gold,GBPUSD,USOIL'"),
    ("autotrade_enabled", "BOOLEAN DEFAULT 0"),
    ("autotrade_min_confidence", "FLOAT DEFAULT 75.0"),
    ("autotrade_max_trades", "INTEGER DEFAULT 5"),
    ("autotrade_assets", "TEXT DEFAULT 'BTC/USDT,ETH/USDT,GC=F'")
]

for col_name, col_type in missing_columns:
    if col_name not in existing_columns:
        print(f"Adding column {col_name} to users table...")
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            print(f"Error adding {col_name}: {e}")

# Check other tables if they exist
tables = ["broker_accounts", "signal_history", "trade_executions"]
for table in tables:
    try:
        cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone()[0] == 0:
            print(f"Table {table} does not exist. It will be created by SQLAlchemy.")
    except Exception as e:
        print(f"Error checking table {table}: {e}")

conn.commit()
conn.close()
print("Migration completed.")
