import os
import sys
import socket
import concurrent.futures
import subprocess
import shutil
import re
import urllib.request
import zipfile
from typing import Optional, Dict, List, Tuple, Any

class AdbManager:
    """Manages ADB discovery (including bundled EXE, auto-download & Android TV LAN scan), USB & Wireless connections."""

    PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or self._find_or_provision_adb()

    def _find_or_provision_adb(self) -> str:
        """Locates adb executable in PyInstaller bundle, local folder, PATH, SDK, or auto-downloads official Google Platform Tools."""
        base_dirs = []
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base_dirs.append(getattr(sys, "_MEIPASS"))
            base_dirs.append(os.path.dirname(sys.executable))
        base_dirs.append(os.path.dirname(os.path.abspath(__file__)))

        for bdir in base_dirs:
            bundled = os.path.join(bdir, "platform-tools", "adb.exe")
            if os.path.isfile(bundled):
                return bundled
            bundled_root = os.path.join(bdir, "adb.exe")
            if os.path.isfile(bundled_root):
                return bundled_root

        which_adb = shutil.which("adb")
        if which_adb and os.path.exists(which_adb):
            return which_adb

        user_profile = os.environ.get("USERPROFILE", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app_data, "AndroidHealthDoctor", "platform-tools", "adb.exe"),
            os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "platform-tools", "adb.exe"),
            r"C:\platform-tools\adb.exe",
            r"C:\Program Files\Android\platform-tools\adb.exe",
            r"C:\Android\platform-tools\adb.exe",
        ]

        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand

        auto_path = self.auto_download_adb()
        if auto_path and os.path.isfile(auto_path):
            return auto_path

        return "adb"

    def auto_download_adb(self) -> Optional[str]:
        """Automatically downloads and extracts official Google Android Platform Tools if ADB is missing on the PC."""
        try:
            local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            target_dir = os.path.join(local_app_data, "AndroidHealthDoctor")
            os.makedirs(target_dir, exist_ok=True)
            adb_exe = os.path.join(target_dir, "platform-tools", "adb.exe")
            if os.path.isfile(adb_exe):
                return adb_exe

            zip_path = os.path.join(target_dir, "platform-tools.zip")
            print("[*] ADB not found on system. Downloading official Google Android Platform Tools (~6 MB)...")
            urllib.request.urlretrieve(self.PLATFORM_TOOLS_URL, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
            try:
                os.remove(zip_path)
            except Exception:
                pass

            if os.path.isfile(adb_exe):
                print(f"[+] Official Android Platform Tools installed at: {adb_exe}")
                self.adb_path = adb_exe
                return adb_exe
        except Exception as e:
            print(f"[!] Auto-download of ADB failed: {e}")
        return None

    def _creation_flags(self) -> int:
        if sys.platform == "win32":
            return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return 0

    def is_available(self) -> bool:
        try:
            res = subprocess.run(
                [self.adb_path, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                creationflags=self._creation_flags()
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_devices(self, lang: str = "en") -> List[Dict[str, Any]]:
        """Returns list of connected devices (USB, Wi-Fi, Android TV) with status and model details."""
        if not self.adb_path:
            return []
        ro = (lang == "ro")
        try:
            res = subprocess.run(
                [self.adb_path, "devices", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                creationflags=self._creation_flags()
            )
            lines = res.stdout.strip().splitlines()
            devices = []
            for line in lines[1:]:
                line = line.strip()
                if not line or line.startswith("*"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    info = " ".join(parts[2:])
                    model = "Dispozitiv Android / TV" if ro else "Android Device / TV"
                    model_match = re.search(r"model:([^\s]+)", info)
                    if model_match:
                        model = model_match.group(1).replace("_", " ")
                    device_name = ""
                    device_match = re.search(r"device:([^\s]+)", info)
                    if device_match:
                        device_name = device_match.group(1)

                    is_wireless = (":" in serial) or ("_adb-tls" in serial)
                    conn_label = "Wi-Fi / LAN (Wireless)" if is_wireless else ("Cablu USB" if ro else "USB Cable")

                    devices.append({
                        "serial": serial,
                        "state": state,  # 'device', 'unauthorized', 'offline'
                        "model": model,
                        "device": device_name,
                        "is_wireless": is_wireless,
                        "connection_type": conn_label,
                        "raw_info": info
                    })
            return devices
        except Exception:
            return []

    def _scan_lan_port_5555(self) -> List[Dict[str, str]]:
        """Scans the local Wi-Fi/LAN subnet for Android TVs / devices listening on standard ADB TCP port 5555."""
        found_tvs = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            parts = local_ip.split(".")
            if len(parts) != 4:
                return []
            prefix = ".".join(parts[:3])

            def probe(host_id: int) -> Optional[str]:
                ip = f"{prefix}.{host_id}"
                if ip == local_ip:
                    return None
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.32)
                    if sock.connect_ex((ip, 5555)) == 0:
                        return ip
                return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
                for ip in ex.map(probe, range(1, 255)):
                    if ip:
                        found_tvs.append({
                            "name": "Android TV / ADB (:5555)",
                            "address": f"{ip}:5555",
                            "ip": ip,
                            "port": "5555"
                        })
        except Exception:
            pass
        return found_tvs

    def discover_wireless_services(self) -> Dict[str, Any]:
        """Auto-discovers phones via mDNS AND Android TVs (Philips, Sony, TCL, Xiaomi, etc.) on LAN TCP port 5555."""
        ok, out = self.run_adb(["mdns", "services"], timeout=6)
        pairing_services = []
        connect_services = []
        seen_addrs = set()

        if ok and out:
            for line in out.splitlines():
                line = line.strip()
                if not line or line.startswith("List of"):
                    continue
                m = re.search(r"([^\s]+)\s+(_adb-tls-(?:pairing|connect)\._tcp\.?)\s+(\d+\.\d+\.\d+\.\d+:\d+)", line)
                if m:
                    name, stype, addr = m.group(1), m.group(2), m.group(3)
                    ip_only = addr.split(":")[0]
                    port_only = addr.split(":")[1]
                    entry = {"name": name, "address": addr, "ip": ip_only, "port": port_only}
                    if "pairing" in stype:
                        pairing_services.append(entry)
                    else:
                        if addr not in seen_addrs:
                            seen_addrs.add(addr)
                            connect_services.append(entry)

        # Also scan LAN port 5555 for Android TVs (where 'USB debugging' opens port 5555 directly without mDNS)
        for tv_entry in self._scan_lan_port_5555():
            if tv_entry["address"] not in seen_addrs:
                seen_addrs.add(tv_entry["address"])
                connect_services.append(tv_entry)

        return {
            "pairing_services": pairing_services,
            "connect_services": connect_services
        }

    def pair_wireless(self, pairing_addr: str, pairing_code: str, connect_addr: Optional[str] = None, lang: str = "en") -> Dict[str, Any]:
        """Pairs with an Android 11+ device over Wi-Fi using `adb pair <ip:port> <code>`, then auto-connects."""
        ro = (lang == "ro")
        pairing_addr = (pairing_addr or "").strip()
        pairing_code = re.sub(r"\s+", "", (pairing_code or ""))

        if not re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", pairing_addr):
            return {
                "success": False,
                "message": (
                    "Format invalid pentru IP:Port de asociere. Exemplu corect: 192.168.1.105:39123"
                    if ro else "Invalid Pairing IP:Port format. Example: 192.168.1.105:39123"
                )
            }
        if not re.match(r"^\d{6}$", pairing_code):
            return {
                "success": False,
                "message": (
                    "Codul de asociere trebuie să conțină exact 6 cifre (ex: 482910)."
                    if ro else "Pairing code must be exactly 6 digits (e.g. 482910)."
                )
            }

        ok, out = self.run_adb(["pair", pairing_addr, pairing_code], timeout=15)
        combined = (out or "").strip()
        paired_ok = ok and ("Successfully paired" in combined or "paired to" in combined.lower())

        if not paired_ok:
            return {
                "success": False,
                "message": (
                    f"Asocierea a eșuat: {combined or 'Verifică dacă fereastra cu codul de 6 cifre este încă deschisă pe telefon și dacă PC-ul este în aceeași rețea Wi-Fi.'}"
                    if ro else f"Pairing failed: {combined or 'Make sure the 6-digit pairing dialog is still open on the phone and both devices are on the same Wi-Fi.'}"
                )
            }

        ip_part = pairing_addr.split(":")[0]
        target_connect = (connect_addr or "").strip()

        if target_connect and target_connect.isdigit():
            target_connect = f"{ip_part}:{target_connect}"

        if not target_connect:
            mdns = self.discover_wireless_services()
            for svc in mdns.get("connect_services", []):
                if svc["ip"] == ip_part:
                    target_connect = svc["address"]
                    break

        connect_msg = ""
        connected_now = False
        if target_connect and re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", target_connect):
            c_res = self.connect_wireless(target_connect, lang=lang)
            connected_now = c_res.get("success", False)
            connect_msg = f" {c_res.get('message', '')}"
        else:
            devices = self.get_devices(lang=lang)
            if any(d["state"] == "device" and d.get("is_wireless") for d in devices):
                connected_now = True
                connect_msg = " Telefonul s-a conectat automat prin mDNS Wi-Fi!" if ro else " Phone auto-connected via mDNS Wi-Fi!"
            else:
                connect_msg = (
                    " Acum introdu Portul de Conectare afișat pe pagina 'Depanare wireless' a telefonului (Pasul 2)."
                    if ro else " Now enter the Connection IP:Port shown on the phone's Wireless Debugging screen (Step 2)."
                )

        return {
            "success": True,
            "paired": True,
            "connected": connected_now,
            "ip": ip_part,
            "message": f"✅ {'Asociere reușită cu' if ro else 'Successfully paired with'} {pairing_addr}!{connect_msg}"
        }

    def connect_wireless(self, connect_addr: str, lang: str = "en") -> Dict[str, Any]:
        """Connects to an Android phone or Android TV over Wi-Fi/LAN (`adb connect <ip:port>`)."""
        ro = (lang == "ro")
        connect_addr = (connect_addr or "").strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", connect_addr):
            connect_addr = f"{connect_addr}:5555"

        if not re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", connect_addr):
            return {
                "success": False,
                "message": (
                    "Format invalid pentru IP sau IP:Port. Exemplu: 192.168.86.48:5555"
                    if ro else "Invalid IP or IP:Port format. Example: 192.168.86.48:5555"
                )
            }

        ok, out = self.run_adb(["connect", connect_addr], timeout=12)
        combined = (out or "").strip()
        lower_out = combined.lower()

        # On Android TV (port 5555), the first connect returns "failed to authenticate to <ip>:5555"
        # while popping up the "Allow USB debugging?" dialog on the TV screen!
        if "failed to authenticate" in lower_out:
            return {
                "success": True,
                "needs_auth": True,
                "address": connect_addr,
                "message": (
                    f"📺 Conectat la {connect_addr}! Privește acum ecranul televizorului / telefonului, bifează 'Permite întotdeauna de pe acest computer' și apasă pe 'Permiteți' (Allow) din telecomandă!"
                    if ro else
                    f"📺 Connected to {connect_addr}! Now look at your TV / phone screen, check 'Always allow from this computer', and press 'Allow' with your remote!"
                )
            }

        success = ("connected to" in lower_out) and ("cannot connect" not in lower_out) and ("failed" not in lower_out)

        if success:
            return {
                "success": True,
                "address": connect_addr,
                "message": f"📶 {'Conectat cu succes prin Wi-Fi/LAN la' if ro else 'Successfully connected via Wi-Fi/LAN to'} {connect_addr}!"
            }
        return {
            "success": False,
            "message": (
                f"Nu s-a putut conecta la {connect_addr}: {combined}. Verifică dacă 'Depanare USB' (pe TV) sau 'Depanare wireless' (pe telefon) este activată."
                if ro else f"Could not connect to {connect_addr}: {combined}. Verify that 'USB debugging' (on Android TV) or 'Wireless debugging' (on phone) is enabled."
            )
        }

    def disconnect_wireless(self, addr: Optional[str] = None, lang: str = "en") -> Dict[str, Any]:
        """Disconnects wireless ADB connections."""
        ro = (lang == "ro")
        args = ["disconnect"]
        if addr:
            args.append(addr.strip())
        ok, out = self.run_adb(args, timeout=8)
        return {
            "success": ok,
            "message": (
                ("Dispozitivele Wi-Fi au fost deconectate." if ro else "Wireless ADB devices disconnected.")
                if ok else f"Error: {out}"
            )
        }

    def run_shell(self, cmd: str, serial: Optional[str] = None, timeout: int = 25) -> Tuple[bool, str]:
        if not self.adb_path:
            return False, "ADB not found."

        adb_cmd = [self.adb_path]
        if serial:
            adb_cmd.extend(["-s", serial])
        adb_cmd.extend(["shell", cmd])

        try:
            res = subprocess.run(
                adb_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                creationflags=self._creation_flags()
            )
            if res.returncode == 0:
                return True, res.stdout
            else:
                return False, res.stderr or res.stdout
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s."
        except Exception as e:
            return False, str(e)

    def run_adb(self, args: List[str], serial: Optional[str] = None, timeout: int = 25) -> Tuple[bool, str]:
        if not self.adb_path:
            return False, "ADB not found."

        adb_cmd = [self.adb_path]
        if serial:
            adb_cmd.extend(["-s", serial])
        adb_cmd.extend(args)

        try:
            res = subprocess.run(
                adb_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                creationflags=self._creation_flags()
            )
            return res.returncode == 0, res.stdout if res.returncode == 0 else (res.stderr or res.stdout)
        except Exception as e:
            return False, str(e)
