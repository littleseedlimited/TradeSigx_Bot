import yfinance as yf
import pandas as pd
import time
import requests

yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
})

def test_bulk():
    symbols = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "^NDX", "GC=F"]
    print(f"Testing yf.download for: {symbols}")
    
    start_time = time.time()
    try:
        data = yf.download(
            tickers=symbols,
            period="5d",
            interval="15m",
            group_by='ticker',
            session=yf_session,
            timeout=20
        )
        duration = time.time() - start_time
        print(f"Time taken: {duration:.2f}s")
        
        if not data.empty:
            print(f"SUCCESS: Retrieved data for {len(data.columns.levels[0]) if isinstance(data.columns, pd.MultiIndex) else 1} assets")
            # print(data.head())
        else:
            print("FAILURE: Multi-asset download returned empty")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_bulk()
