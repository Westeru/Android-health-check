import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import socket
import webbrowser
import threading
import time
import uvicorn

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8899) -> int:
    port = start_port
    while is_port_in_use(port):
        port += 1
    return port

def open_browser(url: str):
    time.sleep(1.2)
    print(f"\n[+] Deschidere interfață în browser: {url}\n")
    webbrowser.open(url)

def main():
    port = find_available_port(8899)
    url = f"http://127.0.0.1:{port}"

    print("=" * 68)
    print("  ANDROID HEALTH DOCTOR - Diagnostic & Optimizare Universală ADB")
    print("=" * 68)
    print(f"[*] Serverul pornește la adresa: {url}")
    print("[*] Conectează orice telefon Android prin cablu USB sau Wireless Wi-Fi.")
    print("=" * 68)

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run("server:app", host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    main()
