import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def list_deriv():
    app_id = os.getenv("DERIV_APP_ID") or "121681"
    uri = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    try:
        async with websockets.connect(uri) as ws:
            request = {"active_symbols": "brief", "product_type": "basic"}
            await ws.send(json.dumps(request))
            resp = await ws.recv()
            data = json.loads(resp)
            
            if 'active_symbols' in data:
                print(f"Total symbols found: {len(data['active_symbols'])}")
                # Filter for Forex and Indices
                forex = [s for s in data['active_symbols'] if s.get('market') == 'forex']
                indices = [s for s in data['active_symbols'] if s.get('market') == 'indices']
                commodities = [s for s in data['active_symbols'] if s.get('market') == 'commodities']
                
                print(f"Forex: {len(forex)}")
                print(f"Indices: {len(indices)}")
                print(f"Commodities: {len(commodities)}")
                
                print("\nAll Indices:")
                for s in indices:
                    print(f"- {s['symbol']} ({s['display_name']})")
                
                print("\nAll Commodities:")
                for s in commodities:
                    print(f"- {s['symbol']} ({s['display_name']})")
            else:
                print("FAILURE: No active_symbols in response")
                print(data)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(list_deriv())
