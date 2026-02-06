import subprocess
import re
import sys
import time

def start_tunnel(subdomain="tradesigx"):
    print(f"Starting tunnel for subdomain: {subdomain}")
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R", f"{subdomain}:80:localhost:8000", "serveo.net"]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    url = None
    for line in iter(process.stdout.readline, ""):
        print(line, end="")
        match = re.search(r"https://[a-zA-Z0-9.-]+\.serveousercontent\.com", line)
        if match:
            url = match.group(0)
            break
        match_alt = re.search(r"https://[a-zA-Z0-9.-]+\.serveo\.net", line)
        if match_alt:
            url = match_alt.group(0)
            break
            
    if url:
        print(f"\nTunnel established: {url}")
        update_config(url)
        return process, url
    return process, None

def update_config(url):
    config_path = "config.py"
    with open(config_path, "r") as f:
        content = f.read()
    
    new_content = re.sub(r'BASE_URL = ".*"', f'BASE_URL = "{url}"', content)
    
    with open(config_path, "w") as f:
        f.write(new_content)
    print(f"Updated config.py with {url}")

if __name__ == "__main__":
    subdomain = sys.argv[1] if len(sys.argv) > 1 else "tradesigx"
    # Try a few common names if tradesigx is taken
    names = [subdomain, f"{subdomain}-bot", f"{subdomain}-dashboard", f"ts-bot-{int(time.time())}"]
    
    for name in names:
        process, url = start_tunnel(name)
        if url:
            try:
                # Keep script running to maintain tunnel
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                break
        time.sleep(2)
