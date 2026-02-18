import requests
import sys

def check_local_server():
    print("🔍 CHECKING TRADESIGX LOCAL CONNECTIVITY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    port = 5000
    url = f"http://127.0.0.1:{port}"
    
    print(f"1. Testing local port {port}...")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ SUCCESS: Local API is ACTIVE on {url}")
        else:
            print(f"⚠️ WARNING: Local API returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ FAILURE: Local API is OFFLINE. Port {port} is not responding.")
        print("\n💡 ACTION: Please ensure you have run 'python main.py' first.")
        return
    
    print("\n2. Checking Tunnel Configuration...")
    try:
        from config import Config
        print(f"📡 Current Config BASE_URL: {Config.BASE_URL}")
        if "ngrok-free.dev" in Config.BASE_URL:
            print("💡 TIP: If using ngrok, ensure you run: 'ngrok http 5000'")
        elif "serveo.net" in Config.BASE_URL:
            print("💡 TIP: If using Serveo, run: 'python scripts/start_tunnel.py'")
    except Exception as e:
        print(f"⚠️ Error reading config: {e}")

if __name__ == "__main__":
    check_local_server()
