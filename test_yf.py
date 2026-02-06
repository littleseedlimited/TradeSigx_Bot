import yfinance as yf
import pandas as pd
import sys

symbol = "GBPUSD=X"
print(f"Testing {symbol}...")
try:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1d", interval="15m")
    if df.empty:
        print("FAIL: DataFrame is empty.")
    else:
        print(f"SUCCESS: Received {len(df)} rows.")
        print(df.tail(1))
except Exception as e:
    print(f"ERROR: {e}")
