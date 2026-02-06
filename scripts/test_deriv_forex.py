import asyncio
import websockets
import json
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

async def test_deriv_forex():
    app_id = os.getenv("DERIV_APP_ID") or "121681"
    token = os.getenv("DERIV_API_TOKEN")
    uri = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    symbols = ["frxEURGBP", "frxGBPUSD", "frxXAUUSD", "OTC_NDX"]
    print(f"Testing Deriv (Authorized: {bool(token)}) for symbols: {symbols}")
    
    try:
        async with websockets.connect(uri) as ws:
            if token:
                auth_req = {"authorize": token}
                await ws.send(json.dumps(auth_req))
                auth_resp = await ws.recv()
                print(f"Auth Response: {auth_resp[:100]}...")
            
            for symbol in symbols:
                request = {
                    "ticks_history": symbol,
                    "count": 500,
                    "end": "latest",
                    "style": "candles",
                    "granularity": 60 # 1 minute
                }
                await ws.send(json.dumps(request))
                resp = await ws.recv()
                data = json.loads(resp)
                
                if 'candles' in data:
                    print(f"SUCCESS: Retrieved {len(data['candles'])} candles for {symbol}")
                elif 'error' in data:
                    print(f"FAILURE for {symbol}: {data['error'].get('message')}")
                else:
                    print(f"UNKNOWN response for {symbol}: {data}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_deriv_forex())
