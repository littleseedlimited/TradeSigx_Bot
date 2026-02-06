import yfinance as yf
import pandas as pd
import logging
import requests

logging.basicConfig(level=logging.INFO)

# Mimic the bot's session
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
})

def test_symbol(symbol):
    print(f"Testing yfinance for {symbol}...")
    try:
        ticker = yf.Ticker(symbol, session=yf_session)
        df = ticker.history(period="5d", interval="15m")
        if not df.empty:
            print(f"SUCCESS: Retrieved {len(df)} rows for {symbol}")
            print(df.tail(2))
        else:
            print(f"FAILURE: Received empty dataframe for {symbol}")
            # Try without session
            print(f"Retrying {symbol} without session...")
            ticker_no_sess = yf.Ticker(symbol)
            df_no_sess = ticker_no_sess.history(period="5d", interval="15m")
            if not df_no_sess.empty:
                print(f"SUCCESS (No Session): Retrieved {len(df_no_sess)} rows")
            else:
                print(f"FAILURE (No Session): Still empty")
    except Exception as e:
        print(f"ERROR for {symbol}: {e}")

if __name__ == "__main__":
    for sym in ["EURGBP=X", "EURJPY=X", "^IXIC", "^NDX"]:
        test_symbol(sym)
        import time
        time.sleep(2) # Small delay between tests
        print("-" * 30)
