import requests
import pandas as pd
import time
import json

def test_direct_yf(symbol):
    print(f"Testing DIRECT Yahoo API for {symbol}...")
    
    # interval: 1m, 5m, 15m, 1h, 1d
    # range: 1d, 5d, 7d, 30d, 1y
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=15)
        duration = time.time() - start_time
        print(f"Time taken: {duration:.2f}s | Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('chart', {}).get('result', [])
            if result:
                quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
                timestamps = result[0].get('timestamp', [])
                df = pd.DataFrame(quotes)
                df['timestamp'] = pd.to_datetime(timestamps, unit='s')
                df.set_index('timestamp', inplace=True)
                print(f"SUCCESS: Retrieved {len(df)} rows")
                # print(df.tail(2))
                return df
            else:
                print("FAILURE: No result in JSON")
        else:
            print(f"FAILURE: HTTP {response.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")
    return pd.DataFrame()

if __name__ == "__main__":
    test_direct_yf("EURUSD=X")
    test_direct_yf("^NDX")
