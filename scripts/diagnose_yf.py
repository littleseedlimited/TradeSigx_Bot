import yfinance as yf
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

def test_yf():
    symbol = "BTC-USD"
    print(f"Testing yfinance for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="7d", interval="15m")
        if not df.empty:
            print(f"SUCCESS: Retrieved {len(df)} rows for {symbol}")
            print(df.tail())
        else:
            print(f"FAILURE: Received empty dataframe for {symbol}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_yf()
