import os
import subprocess
import shutil
import re
from typing import Optional, Dict, List, Tuple, Any

class AdbManager:
    """Manages ADB discovery, USB & Wireless (Wi-Fi) connections, and device interactions."""

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or self._find_adb()

    def _find_adb(self) -> str:
        """Locates adb executable across common paths or PATH."""
        which_adb = shutil.which("adb")
        if which_adb and os.path.exists(which_adb):
            return which_adb

        user_profile = os.environ.get("USERPROFILE", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "platform-tools", "adb.exe"),
            r"C:\platform-tools\adb.exe",
            r"C:\Program Files\Android\platform-tools\adb.exe",
            r"C:\Android\platform-tools\adb.exe",
        ]

        for cand in candidates:
            if os.path.isfile(cand):
                return cand

        return "adb"

    def is_available(self) -> bool:
        """Checks if ADB binary is reachable and working."""
        try:
            res = subprocess.run([self.adb_path, "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def get_devices(self) -> List[Dict[str, Any]]:
        """Returns list of connected devices (both USB and Wi-Fi) with status and model details."""
        if not self.adb_path:
            return []
        try:
            res = subprocess.run([self.adb_path, "devices", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
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
                    model = "Dispozitiv Android"
                    model_match = re.search(r"model:([^\s]+)", info)
                    if model_match:
                        model = model_match.group(1).replace("_", " ")
                    device_name = ""
                    device_match = re.search(r"device:([^\s]+)", info)
                    if device_match:
                        device_name = device_match.group(1)

                    is_wireless = (":" in serial) or ("_adb-tls" in serial)

                    devices.append({
                        "serial": serial,
                        "state": state,  # 'device', 'unauthorized', 'offline'
                        "model": model,
                        "device": device_name,
                        "is_wireless": is_wireless,
                        "connection_type": "Wi-Fi (Wireless)" if is_wireless else "Cablu USB",
                        "raw_info": info
                    })
            return devices
        except Exception:
            return []

    def discover_wireless_services(self) -> Dict[str, Any]:
        """Uses `adb mdns services` to auto-discover phones with Wireless Debugging open on the same Wi-Fi."""
        ok, out = self.run_adb(["mdns", "services"], timeout=6)
        pairing_services = []
        connect_services = []

        if ok and out:
            for line in out.splitlines():
                line = line.strip()
                if not line or line.startswith("List of"):
                    continue
                # Format: <service_name>  _adb-tls-pairing._tcp.  192.168.1.50:39123
                m = re.search(r"([^\s]+)\s+(_adb-tls-(?:pairing|connect)\._tcp\.?)\s+(\d+\.\d+\.\d+\.\d+:\d+)", line)
                if m:
                    name, stype, addr = m.group(1), m.group(2), m.group(3)
                    ip_only = addr.split(":")[0]
                    port_only = addr.split(":")[1]
                    entry = {"name": name, "address": addr, "ip": ip_only, "port": port_only}
                    if "pairing" in stype:
                        pairing_services.append(entry)
                    else:
                        connect_services.append(entry)

        return {
            "pairing_services": pairing_services,
            "connect_services": connect_services
        }

    def pair_wireless(self, pairing_addr: str, pairing_code: str, connect_addr: Optional[str] = None) -> Dict[str, Any]:
        """Pairs with an Android 11+ device over Wi-Fi using `adb pair <ip:port> <code>`, then auto-connects."""
        pairing_addr = (pairing_addr or "").strip()
        pairing_code = re.sub(r"\s+", "", (pairing_code or ""))

        if not re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", pairing_addr):
            return {
                "success": False,
                "message": "Format invalid pentru IP:Port de asociere. Exemplu corect: 192.168.1.105:39123"
            }
        if not re.match(r"^\d{6}$", pairing_code):
            return {
                "success": False,
                "message": "Codul de asociere trebuie să conțină exact 6 cifre (ex: 482910)."
            }

        ok, out = self.run_adb(["pair", pairing_addr, pairing_code], timeout=15)
        combined = (out or "").strip()
        paired_ok = ok and ("Successfully paired" in combined or "paired to" in combined.lower())

        if not paired_ok:
            return {
                "success": False,
                "message": f"Asocierea a eșuat: {combined or 'Verifică dacă fereastra cu codul de 6 cifre este încă deschisă pe telefon și dacă PC-ul este în aceeași rețea Wi-Fi.'}"
            }

        # After pairing, try to connect automatically!
        ip_part = pairing_addr.split(":")[0]
        target_connect = (connect_addr or "").strip()

        # If user only gave the connect port (e.g. "41555"), prepend IP
        if target_connect and target_connect.isdigit():
            target_connect = f"{ip_part}:{target_connect}"

        # If no connect_addr provided, check mdns services for the same IP
        if not target_connect:
            mdns = self.discover_wireless_services()
            for svc in mdns.get("connect_services", []):
                if svc["ip"] == ip_part:
                    target_connect = svc["address"]
                    break

        connect_msg = ""
        connected_now = False
        if target_connect and re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", target_connect):
            c_res = self.connect_wireless(target_connect)
            connected_now = c_res.get("success", False)
            connect_msg = f" {c_res.get('message', '')}"
        else:
            # Check if adb auto-connected via mDNS tls serial
            devices = self.get_devices()
            if any(d["state"] == "device" and d.get("is_wireless") for d in devices):
                connected_now = True
                connect_msg = " Telefonul s-a conectat automat prin mDNS Wi-Fi!"
            else:
                connect_msg = " Acum introdu Portul de Conectare afișat pe pagina 'Depanare wireless' a telefonului (Pasul 2) pentru a finaliza conexiunea."

        return {
            "success": True,
            "paired": True,
            "connected": connected_now,
            "ip": ip_part,
            "message": f"✅ Asociere reușită cu {pairing_addr}!{connect_msg}"
        }

    def connect_wireless(self, connect_addr: str) -> Dict[str, Any]:
        """Connects to an already paired Android device over Wi-Fi (`adb connect <ip:port>`)."""
        connect_addr = (connect_addr or "").strip()
        if not re.match(r"^\d+\.\d+\.\d+\.\d+(:\d+)?$", connect_addr):
            return {
                "success": False,
                "message": "Format invalid pentru IP:Port. Exemplu corect: 192.168.1.105:41555"
            }

        ok, out = self.run_adb(["connect", connect_addr], timeout=12)
        combined = (out or "").strip()
        success = ("connected to" in combined.lower()) and ("cannot connect" not in combined.lower()) and ("failed" not in combined.lower())

        if success:
            return {
                "success": True,
                "address": connect_addr,
                "message": f"📶 Conectat cu succes prin Wi-Fi la {connect_addr}!"
            }
        return {
            "success": False,
            "message": f"Nu s-a putut conecta la {connect_addr}: {combined}. Verifică dacă 'Depanare wireless' este activată pe telefon și dacă portul este cel corect."
        }

    def disconnect_wireless(self, addr: Optional[str] = None) -> Dict[str, Any]:
        """Disconnects wireless ADB connections."""
        args = ["disconnect"]
        if addr:
            args.append(addr.strip())
        ok, out = self.run_adb(args, timeout=8)
        return {
            "success": ok,
            "message": "Dispozitivele Wi-Fi au fost deconectate." if ok else f"Eroare: {out}"
        }

    def run_shell(self, cmd: str, serial: Optional[str] = None, timeout: int = 25) -> Tuple[bool, str]:
        """Runs an adb shell command on the target device."""
        if not self.adb_path:
            return False, "ADB nu a fost găsit."

        adb_cmd = [self.adb_path]
        if serial:
            adb_cmd.extend(["-s", serial])
        adb_cmd.extend(["shell", cmd])

        try:
            res = subprocess.run(adb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            if res.returncode == 0:
                return True, res.stdout
            else:
                return False, res.stderr or res.stdout
        except subprocess.TimeoutExpired:
            return False, f"Comanda a expirat după {timeout} secunde."
        except Exception as e:
            return False, str(e)

    def run_adb(self, args: List[str], serial: Optional[str] = None, timeout: int = 25) -> Tuple[bool, str]:
        """Runs a raw adb command."""
        if not self.adb_path:
            return False, "ADB nu a fost găsit."

        adb_cmd = [self.adb_path]
        if serial:
            adb_cmd.extend(["-s", serial])
        adb_cmd.extend(args)

        try:
            res = subprocess.run(adb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            return res.returncode == 0, res.stdout if res.returncode == 0 else (res.stderr or res.stdout)
        except Exception as e:
            return False, str(e)
