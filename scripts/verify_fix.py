import asyncio
import os
import pandas as pd
from dotenv import load_dotenv
import logging

# Mock the logger
logging.basicConfig(level=logging.INFO)

# Import the DataCollector from the actual codebase
import sys
sys.path.append(os.getcwd())
from data.collector import DataCollector

async def verify():
    load_dotenv()
    
    symbols_to_test = ["^NDX", "EURUSD=X", "GBPUSD=X", "GC=F", "R_100"]
    
    print("Starting Final Verification...")
    print("-" * 30)
    
    for symbol in symbols_to_test:
        print(f"Testing: {symbol}")
        try:
            df = await DataCollector.fetch_data(symbol)
            if not df.empty:
                print(f"SUCCESS: {symbol} | Rows: {len(df)}")
                print(f"Latest Price: {df['close'].iloc[-1]}")
            else:
                print(f"FAILURE: {symbol} | Data Empty")
        except Exception as e:
            print(f"ERROR: {symbol} | {e}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(verify())
