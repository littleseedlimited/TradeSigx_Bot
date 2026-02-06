import asyncio
import pandas as pd
import logging
import os
from data.collector import DataCollector
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

async def test_all_data():
    collector = DataCollector()
    
    test_assets = [
        ("EURUSD=X", "forex"),
        ("BTC/USDT", "crypto"),
        ("R_75", "synthetic")
    ]
    
    print("STARTING GLOBAL DATA DIAGNOSTIC v4.1")
    print("------------------------------------")
    
    for symbol, asset_type in test_assets:
        print(f"Testing {symbol} ({asset_type})...")
        try:
            df = await collector.fetch_data(symbol, asset_type)
            if df is not None and not df.empty:
                print(f"SUCCESS: {symbol} returned {len(df)} rows.")
            else:
                print(f"FAILURE: {symbol} returned EMPTY dataframe.")
        except Exception as e:
            print(f"ERROR: {symbol} failed with: {e}")
    
    print("------------------------------------")
    print("Diagnostic Complete.")

if __name__ == "__main__":
    asyncio.run(test_all_data())
