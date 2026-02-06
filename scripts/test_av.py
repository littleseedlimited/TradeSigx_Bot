import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_av():
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    print(f"Testing Alpha Vantage with key: {api_key[:5]}...")
    
    # Test Forex
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=EUR&to_symbol=GBP&interval=15min&apikey={api_key}"
    resp = requests.get(url)
    data = resp.json()
    
    if "Time Series FX (15min)" in data:
        print("SUCCESS: Forex data retrieved from Alpha Vantage")
    elif "Note" in data:
        print(f"FAILURE: Rate limited - {data['Note']}")
    else:
        print(f"FAILURE: {data.get('Error Message', 'Unknown error')}")
        print(data)

if __name__ == "__main__":
    test_av()
