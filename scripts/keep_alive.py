import subprocess
import time
import sys
import os

def keep_bot_alive():
    """Bulletproof persistence for TradeSigx BOT"""
    print("STARTING TradeSigx Uptime Guardian Active")
    while True:
        try:
            # Clear residual python processes to prevent port conflicts
            # Using /T to kill the process tree and /F for force
            # We don't kill our own process (the keeper)
            print(f"[{time.ctime()}] Booting System Stack...")
            
            # Use sys.executable to ensure we use the same python version
            subprocess.run([sys.executable, "main.py"], check=True)
        except KeyboardInterrupt:
            print("\nManually stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"SYSTEM ALERT: Internal timeout or crash detected. {e}")
            print("Cleaning environment and re-initializing in 10 seconds...")
            # Minimal cleaning to avoid killing ourselves
            os.system("taskkill /F /IM python.exe /FI \"PID ne " + str(os.getpid()) + "\"")
            time.sleep(10)

if __name__ == "__main__":
    keep_bot_alive()
