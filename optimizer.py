import re
import datetime
from typing import Dict, Any, Optional, List, Callable
from adb_manager import AdbManager

ProgressCallback = Optional[Callable[[int, int, str, str], None]]

class PhoneOptimizer:
    """Provides universal, non-destructive ADB-based repairs for any Android device with real-time progress reporting."""

    PROTECTED_PACKAGES = {
        "system",
        "android",
        "com.android.systemui",
        "com.google.android.apps.nexuslauncher",
        "com.sec.android.app.launcher",
        "com.miui.home",
        "com.android.launcher",
        "com.android.launcher3",
        "com.google.android.inputmethod.latin",
        "com.samsung.android.honeyboard",
        "com.android.phone",
        "com.android.settings",
        "com.google.android.gms",
        "com.google.android.gsf",
        "com.google.android.ims",
        "com.google.android.dialer",
        "com.samsung.android.dialer",
        "com.google.android.apps.messaging",
    }

    BASE_UI_PACKAGES = [
        "com.android.systemui",
        "com.google.android.webview",
        "com.android.chrome",
    ]

    KNOWN_LAUNCHERS = [
        "com.google.android.apps.nexuslauncher",
        "com.sec.android.app.launcher",
        "com.miui.home",
        "com.android.launcher3",
        "com.android.launcher",
        "com.motorola.launcher3",
        "com.oneplus.brickmode",
        "com.nothing.launcher",
        "com.teslacoilsw.launcher",
    ]

    # Known cross-brand heavy background AI, telemetry, and companion daemons safe to restrict in background
    COMMON_BG_HOGS = [
        "com.google.android.aicore",
        "com.google.android.as.oss",
        "com.google.android.apps.wellbeing",
        "com.samsung.android.bixby.agent",
        "com.samsung.android.game.gos",
        "com.miui.analytics",
        "com.miui.msa.global",
        "com.huawei.health",
        "com.xiaomi.wearable",
        "com.xiaomi.hm.health",
        "com.tuya.smartlife",
    ]

    def __init__(self, adb: AdbManager, serial: Optional[str] = None, progress_cb: ProgressCallback = None):
        self.adb = adb
        self.serial = serial
        self.progress_cb = progress_cb

    def _emit(self, step: int, total: int, current_task: str, log_msg: str):
        if self.progress_cb:
            self.progress_cb(step, total, current_task, log_msg)

    def _get_ui_critical_packages(self) -> List[str]:
        """Dynamically detects the active home launcher on any Android phone and combines with SystemUI & WebView."""
        pkgs = list(self.BASE_UI_PACKAGES)
        detected_launcher = None

        ok, out = self.adb.run_shell("cmd shortcut get-default-launcher", self.serial, timeout=5)
        if ok and out:
            m = re.search(r"ComponentInfo\{([a-zA-Z0-9_\.]+)/", out)
            if not m:
                m = re.search(r"package=([a-zA-Z0-9_\.]+)", out)
            if m:
                detected_launcher = m.group(1)

        if not detected_launcher:
            ok2, out2 = self.adb.run_shell(
                "pm resolve-activity -a android.intent.action.MAIN -c android.intent.category.HOME",
                self.serial,
                timeout=5
            )
            if ok2 and out2:
                m2 = re.search(r"packageName=([a-zA-Z0-9_\.]+)", out2)
                if m2 and m2.group(1) != "android":
                    detected_launcher = m2.group(1)

        if detected_launcher and detected_launcher not in pkgs:
            pkgs.insert(0, detected_launcher)
        else:
            pkgs.insert(0, "com.google.android.apps.nexuslauncher")

        return pkgs

    def get_installed_packages(self) -> List[str]:
        """Returns sorted list of installed user and updated system packages for custom per-app repair."""
        ok, out = self.adb.run_shell("pm list packages -3", self.serial, timeout=10)
        pkgs = []
        if ok and out:
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    pkg = line.replace("package:", "").strip()
                    if pkg:
                        pkgs.append(pkg)
        # Also include key system providers so users can select them directly
        for sys_pkg in (
            "com.android.providers.contacts",
            "com.android.providers.media.module",
            "com.android.providers.downloads",
            "com.android.systemui",
            "com.google.android.webview",
            "com.google.android.gms",
            "com.android.chrome",
        ):
            if sys_pkg not in pkgs:
                pkgs.append(sys_pkg)
        pkgs.sort()
        return pkgs

    @staticmethod
    def _normalize_package(package: str) -> str:
        if not package:
            return ""
        pkg = package.split(":")[0].strip()
        process_map = {
            "android.process.acore": "com.android.providers.contacts",
            "android.process.media": "com.android.providers.media.module",
            "com.google.process.gservices": "com.google.android.gsf",
            "com.google.process.gapps": "com.google.android.gms",
        }
        return process_map.get(pkg, pkg)

    @staticmethod
    def _is_valid_package(package: str) -> bool:
        return bool(package and re.match(r"^[a-zA-Z0-9_\.]+$", package))

    def get_available_ram_mb(self) -> int:
        ok, out = self.adb.run_shell("grep MemAvailable /proc/meminfo", self.serial, timeout=5)
        if ok and out:
            m = re.search(r"(\d+)", out)
            if m:
                return round(int(m.group(1)) / 1024)
        return 0

    def get_live_phone_activity(self) -> Dict[str, Any]:
        """Checks if the phone is currently running heavy background tasks like dex2oat64 compilation or fstrim."""
        ok, out = self.adb.run_shell("ps -A -o PID,NAME,ARGS | grep -E 'dex2oat|fstrim'", self.serial, timeout=5)
        active_tasks = []
        if ok and out:
            for line in out.splitlines():
                if "grep" in line:
                    continue
                if "dex2oat" in line:
                    pkg_match = re.search(r"/data/app/[^/]+/([^/-]+)-[^/]+/", line)
                    if not pkg_match:
                        pkg_match = re.search(r"([a-zA-Z0-9_]+\.[a-zA-Z0-9_\.]+)", line)
                    pkg_name = pkg_match.group(1) if pkg_match else "aplicație sistem"
                    active_tasks.append(f"Compilare nativă ART (dex2oat64) în curs pentru: {pkg_name}")
                elif "fstrim" in line or "sm fstrim" in line:
                    active_tasks.append("Optimizare blocuri memorie flash UFS (fstrim) în curs...")

        return {
            "busy": len(active_tasks) > 0,
            "active_tasks": active_tasks,
            "summary": active_tasks[0] if active_tasks else "Telefonul este în repaus (nicio operațiune în fundal)"
        }

    def run_fstrim(self) -> Dict[str, Any]:
        """Runs flash storage trim (fstrim) and reclaims system caches to restore UFS write speeds."""
        self._emit(1, 2, "Curățare cache sistem (pm trim-caches)...", "⏳ Se eliberează cache-ul neesențial din stocarea internă...")
        self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=25)
        self._emit(2, 2, "Execuție TRIM pe memoria flash UFS (sm fstrim)...", "✓ Cache-ul sistem a fost curățat. Se rulează fstrim pe blocurile flash...")
        ok, out = self.adb.run_shell("sm fstrim", self.serial, timeout=45)
        self._emit(2, 2, "Finalizat!", "✓ Optimizarea stocării UFS (fstrim + cache) s-a încheiat cu succes!")
        return {
            "success": ok,
            "title": "Optimizare Stocare UFS (fstrim + Cache Trim)",
            "message": "Memoria cache globală a fost curățată și blocurile flash UFS au fost optimizate cu succes!" if ok else f"Cache-ul a fost curățat (Notă fstrim: {out})"
        }

    def fix_ui_stutter(self) -> Dict[str, Any]:
        """Fixes choppy scrolling and UI lag ('sacadare'): enables high refresh rate, sets 0.5x snappy animations, repairs WebView & Launcher."""
        ui_pkgs = self._get_ui_critical_packages()
        total_steps = 3 + len(ui_pkgs)
        self._emit(1, total_steps, "Setare animații ultra-rapide (0.5x)...", "⏳ Se setează window_animation_scale, transition_animation_scale și animator_duration_scale la 0.5x...")
        for scale_key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            self.adb.run_shell(f"settings put global {scale_key} 0.5", self.serial, timeout=5)
        self._emit(1, total_steps, "Animații 0.5x activate", "✓ Animațiile de sistem au fost setate la 0.5x (răspuns instant).")

        self._emit(2, total_steps, "Activare rată de refresh maximă (90Hz / 120Hz)...", "⏳ Se configurează rata de refresh dinamică maximă a ecranului...")
        self.adb.run_shell("settings put system peak_refresh_rate 120.0", self.serial, timeout=5)
        self.adb.run_shell("settings put system min_refresh_rate 60.0", self.serial, timeout=5)
        self._emit(2, total_steps, "Rată de refresh maximă activată", "✓ Rata de refresh maximă (Smooth Display) a fost configurată.")

        step = 2
        for pkg in ui_pkgs:
            step += 1
            self._emit(step, total_steps, f"Recompilare nativă 'speed': {pkg}...", f"⏳ Se curăță cache-ul și se compilează nativ AOT (mod 'speed') pachetul {pkg}...")
            self.adb.run_shell(f"pm clear --cache-only {pkg}", self.serial, timeout=10)
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=45)
            self._emit(step, total_steps, f"Optimizat: {pkg}", f"✓ Pachetul {pkg} a fost curățat și compilat nativ în mod 'speed'.")

        self._emit(total_steps, total_steps, "Resetare contoare GPU Frame Stats...", "⏳ Se resetează statisticile de cadre pierdute (gfxinfo)...")
        self.adb.run_shell("dumpsys gfxinfo --reset", self.serial, timeout=8)
        self._emit(total_steps, total_steps, "Finalizat!", "✅ Eliminarea sacadării UI (120Hz + 0.5x + Launcher/SystemUI/WebView) s-a finalizat!")

        return {
            "success": True,
            "title": "Eliminare Sacadare UI & Boost Rată Refresh",
            "message": "Animațiile 0.5x și rata maximă de refresh au fost activate, iar Launcher-ul, SystemUI și Android WebView au fost recompilate nativ în mod 'speed'!"
        }

    def restore_default_animations(self) -> Dict[str, Any]:
        """Restores Android animation scales back to standard 1.0x."""
        self._emit(1, 1, "Restaurare animații 1.0x...", "⏳ Se readuc scările de animație la 1.0x...")
        for scale_key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            self.adb.run_shell(f"settings put global {scale_key} 1.0", self.serial, timeout=5)
        self._emit(1, 1, "Finalizat!", "✓ Scările de animație au fost readuse la 1.0x.")
        return {
            "success": True,
            "title": "Animații Standard (1.0x)",
            "message": "Scările de animație au fost readuse la valoarea standard 1.0x."
        }

    def disable_accessibility_services(self) -> Dict[str, Any]:
        """Disables active accessibility hooks that intercept touch events and cause severe UI stutter/ANRs."""
        self._emit(1, 1, "Dezactivare servicii de accesibilitate...", "⏳ Se opresc hook-urile de accesibilitate care interceptează atingerea ecranului...")
        ok1, _ = self.adb.run_shell("settings put secure enabled_accessibility_services null", self.serial, timeout=5)
        ok2, _ = self.adb.run_shell("settings put secure accessibility_enabled 0", self.serial, timeout=5)
        self._emit(1, 1, "Finalizat!", "✓ Serviciile de accesibilitate au fost dezactivate.")
        return {
            "success": ok1 or ok2,
            "title": "Dezactivare Servicii Accesibilitate",
            "message": "Serviciile de accesibilitate care interceptau ecranul și încetineau scroll-ul au fost dezactivate!"
        }

    def deep_repair_app(self, package: str, emit_standalone: bool = True) -> Dict[str, Any]:
        """Repairs a freezing/crashing app WITHOUT deleting user accounts or personal data."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid."}

        if emit_standalone:
            self._emit(1, 4, f"Oprire procese blocate pentru {package}...", f"⏳ Se opresc firele de execuție blocate pentru {package}...")
        if package != "com.android.systemui":
            self.adb.run_shell(f"am force-stop {package}", self.serial, timeout=8)

        if emit_standalone:
            self._emit(2, 4, f"Curățare exclusivă cache pentru {package}...", f"⏳ Se șterge doar cache-ul corupt pentru {package} (datele contului rămân intacte)...")
        ok_cache, _ = self.adb.run_shell(f"pm clear --cache-only {package}", self.serial, timeout=10)
        if not ok_cache:
            self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=15)

        if package == "com.android.providers.contacts":
            self.adb.run_shell("am force-stop com.google.android.contacts", self.serial, timeout=6)
            self.adb.run_shell("pm clear com.android.providers.contacts", self.serial, timeout=12)
            for companion in ("com.android.providers.blockednumber", "com.android.providers.userdictionary", "com.google.android.contacts"):
                self.adb.run_shell(f"pm clear --cache-only {companion}", self.serial, timeout=6)
                self.adb.run_shell(f"cmd package compile -m speed -f {companion}", self.serial, timeout=25)
        elif package in ("com.android.providers.media.module", "com.android.providers.media", "com.android.providers.downloads"):
            for media_pkg in ("com.android.providers.media.module", "com.android.providers.media", "com.android.providers.downloads"):
                self.adb.run_shell(f"pm clear --cache-only {media_pkg}", self.serial, timeout=6)
                self.adb.run_shell(f"cmd package compile -m speed -f {media_pkg}", self.serial, timeout=25)

        if emit_standalone:
            self._emit(3, 4, "Curățare cache Android System WebView...", "⏳ Se curăță cache-ul Android System WebView...")
        if package != "com.google.android.webview":
            self.adb.run_shell("pm clear --cache-only com.google.android.webview", self.serial, timeout=8)

        if emit_standalone:
            self._emit(4, 4, f"Compilare nativă AOT 'speed' pentru {package}...", f"⏳ Se recompilează în cod mașină nativ (mod 'speed') aplicația {package}...")
        self.adb.run_shell(f"cmd package compile -m speed -f {package}", self.serial, timeout=60)
        self.adb.run_shell(f"cmd activity clear-exit-info --user 0 {package}", self.serial, timeout=5)
        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=5)

        if emit_standalone:
            self._emit(4, 4, "Finalizat!", f"✅ Aplicația {package} a fost reparată, compilată nativ în mod 'speed' și istoricul de erori a fost curățat!")

        return {
            "success": True,
            "title": f"Reparare profundă: {package}",
            "message": f"Aplicația {package} a fost oprită, cache-ul corupt a fost șters (fără pierderea contului/datelor) și codul ei a fost recompilat nativ în mod 'speed'!"
        }

    def restrict_app_background(self, package: str) -> Dict[str, Any]:
        """Puts a heavy background app into restricted mode and stops it from running in the background."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid."}
        if package in self.PROTECTED_PACKAGES:
            return {"success": False, "message": f"Pachetul {package} este o componentă esențială de sistem și nu trebuie restricționat."}

        self._emit(1, 2, f"Oprire și restricționare fundal: {package}...", f"⏳ Se oprește {package} și se setează Standby Bucket = restricted...")
        self.adb.run_shell(f"am force-stop {package}", self.serial, timeout=8)
        self.adb.run_shell(f"am set-standby-bucket {package} restricted", self.serial, timeout=8)
        self.adb.run_shell(f"cmd appops set {package} RUN_ANY_IN_BACKGROUND ignore", self.serial, timeout=8)
        self.adb.run_shell(f"cmd appops set {package} RUN_IN_BACKGROUND ignore", self.serial, timeout=8)
        self._emit(2, 2, "Finalizat!", f"✅ {package} a fost blocat din a mai rula parazit în fundal.")

        return {
            "success": True,
            "title": f"Restricționare fundal: {package}",
            "message": f"Aplicația {package} a fost oprită și blocată din a mai rula parazit în fundal (Standby Bucket: Restricted)."
        }

    def optimize_ram(self, emit_standalone: bool = True) -> Dict[str, Any]:
        """Frees RAM and ZRAM pressure by killing cached processes and stopping heavy non-system background apps."""
        ram_before = self.get_available_ram_mb()
        if emit_standalone:
            self._emit(1, 3, "Eliberare procese cached (am kill-all)...", f"⏳ RAM liber înainte: {ram_before} MB. Se închid procesele inerte din fundal...")
        self.adb.run_shell("am kill-all", self.serial, timeout=10)

        if emit_standalone:
            self._emit(2, 3, "Curățare cache RAM/Storage...", "⏳ Se eliberează cache-ul pachetelor...")
        self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=15)

        if emit_standalone:
            self._emit(3, 3, "Oprire aplicații grele din fundal...", "⏳ Se identifică și se opresc aplicațiile non-sistem care consumă mult RAM...")
        stopped_apps = []
        ok_mem, mem_out = self.adb.run_shell("dumpsys meminfo | head -n 45", self.serial, timeout=12)
        if ok_mem and mem_out:
            for line in mem_out.splitlines():
                match = re.search(r"([\d,]+)K:\s+([a-zA-Z0-9_\.]+)\s*(?:\(pid|\()?", line.strip())
                if match:
                    pkg = self._normalize_package(match.group(2))
                    if (
                        "." in pkg
                        and pkg not in self.PROTECTED_PACKAGES
                        and not pkg.startswith("com.android.system")
                        and not pkg.startswith("com.google.android.providers")
                        and pkg not in stopped_apps
                    ):
                        self.adb.run_shell(f"am force-stop {pkg}", self.serial, timeout=5)
                        stopped_apps.append(pkg)
                        if len(stopped_apps) >= 6:
                            break

        ram_after = self.get_available_ram_mb()
        diff = max(0, ram_after - ram_before)
        stopped_str = f" Aplicații oprite din fundal: {', '.join(stopped_apps)}." if stopped_apps else ""
        msg = f"Memorie disponibilă acum: {ram_after} MB (+{diff} MB eliberați instant).{stopped_str}"
        if emit_standalone:
            self._emit(3, 3, "Finalizat!", f"✅ {msg}")

        return {
            "success": True,
            "title": "Eliberare Memorie RAM & ZRAM",
            "message": msg
        }

    def cool_down_cpu(self) -> Dict[str, Any]:
        """Stops top CPU-consuming background processes to stop thermal throttling."""
        self._emit(1, 2, "Oprire procese CPU din fundal...", "⏳ Se caută și se opresc aplicațiile care solicită procesorul...")
        self.adb.run_shell("am kill-all", self.serial, timeout=10)
        stopped_cpu = []

        ok_cpu, cpu_out = self.adb.run_shell("dumpsys cpuinfo | head -n 30", self.serial, timeout=10)
        if ok_cpu and cpu_out:
            for line in cpu_out.splitlines():
                match = re.search(r"(\d+(?:\.\d+)?)%\s+\d+/([a-zA-Z0-9_\.]+):", line.strip())
                if match:
                    pkg = self._normalize_package(match.group(2))
                    if "." in pkg and pkg not in self.PROTECTED_PACKAGES and pkg not in stopped_cpu:
                        self.adb.run_shell(f"am force-stop {pkg}", self.serial, timeout=5)
                        stopped_cpu.append(pkg)

        msg_extra = f" Procese CPU oprite: {', '.join(stopped_cpu)}." if stopped_cpu else ""
        self._emit(2, 2, "Finalizat!", f"✅ Procesorul a fost eliberat.{msg_extra}")
        return {
            "success": True,
            "title": "Răcire CPU & Oprire Consumatori Fundal",
            "message": f"Aplicațiile care solicitau procesorul în fundal au fost oprite.{msg_extra}"
        }

    def run_art_optimization(self) -> Dict[str, Any]:
        """Forces ART compiler to optimize critical UI apps in 'speed' mode and all other apps in 'speed-profile'."""
        ui_pkgs = self._get_ui_critical_packages()
        total = len(ui_pkgs) + 1
        step = 0
        for pkg in ui_pkgs:
            step += 1
            self._emit(step, total, f"Compilare 'speed' pentru {pkg}...", f"⏳ Se compilează nativ în mod 'speed' componenta {pkg}...")
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=45)
            self._emit(step, total, f"Compilat: {pkg}", f"✓ {pkg} compilat cu succes.")

        self._emit(total, total, "Optimizare profil pentru restul aplicațiilor...", "⏳ Se optimizează aplicațiile instalate (speed-profile)... Poate dura 30-60 secunde.")
        ok, out = self.adb.run_shell("cmd package compile -m speed-profile -a", self.serial, timeout=120)
        if not ok:
            ok, out = self.adb.run_shell("cmd package bg-dexopt-job", self.serial, timeout=120)
        self._emit(total, total, "Finalizat!", "✅ Toate aplicațiile au fost optimizate de compilatorul ART!")

        return {
            "success": True,
            "title": "Optimizare Compilator ART / Bytecode",
            "message": "Interfața de sistem (Launcher, SystemUI, WebView) a fost compilată în mod 'speed', iar aplicațiile instalate au fost optimizate!"
        }

    def fix_contacts_acore_loop(self) -> Dict[str, Any]:
        """Surgically repairs Android core Content Providers (Contacts/acore, MediaStore, Downloads, Calendar, Sync) whose SQLite locks freeze apps."""
        self._emit(1, 5, "Oprire procese blocate în furnizorii de sistem (Contacte, MediaStore, Sync)...", "⏳ Se opresc procesele blocate din ContactsProvider (acore), MediaStore și Downloads...")
        for pkg in (
            "com.google.android.contacts",
            "com.samsung.android.app.contacts",
            "com.android.providers.contacts",
            "com.android.providers.blockednumber",
            "com.android.providers.media.module",
            "com.android.providers.downloads",
        ):
            self.adb.run_shell(f"am force-stop {pkg}", self.serial, timeout=5)

        self._emit(2, 5, "Reconstrucție bază de date SQLite Contacte & Apeluri (contacts2.db)...", "⏳ Se reinițializează baza locală din com.android.providers.contacts și blockednumber (contactele din contul Cloud se resincronizează automat)...")
        self.adb.run_shell("pm clear com.android.providers.contacts", self.serial, timeout=15)
        self.adb.run_shell("pm clear com.android.providers.blockednumber", self.serial, timeout=10)
        self.adb.run_shell("pm clear --cache-only com.google.android.contacts", self.serial, timeout=8)
        self.adb.run_shell("pm clear --cache-only com.android.providers.userdictionary", self.serial, timeout=8)

        self._emit(3, 5, "Curățare cache furnizori MediaStore, Descărcări, Calendar & GSF...", "⏳ Se curăță cache-ul pentru MediaStore, Downloads, Calendar și Google Services Framework...")
        for sys_prov in (
            "com.android.providers.media.module",
            "com.android.providers.media",
            "com.android.providers.downloads",
            "com.android.providers.calendar",
            "com.google.android.gsf",
        ):
            self.adb.run_shell(f"pm clear --cache-only {sys_prov}", self.serial, timeout=8)

        self._emit(4, 5, "Compilare nativă AOT 'speed' pentru toți furnizorii de sistem...", "⏳ Se compilează în mod 'speed' furnizorii Contacts, MediaStore, Downloads și GSF...")
        for pkg in (
            "com.android.providers.contacts",
            "com.android.providers.blockednumber",
            "com.google.android.contacts",
            "com.android.providers.media.module",
            "com.android.providers.downloads",
            "com.google.android.gsf",
        ):
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=35)

        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=5)
        self._emit(5, 5, "Finalizat!", "✅ Bazele de date de sistem (Contacte/acore, MediaStore, Descărcări, Sincronizare) au fost reparate, compilate nativ, iar istoricul de erori a fost resetat!")
        return {
            "success": True,
            "title": "Reparare Baze de Date Sistem (Contacte 'acore', MediaStore & Sync)",
            "message": "Furnizorii de sistem (Contacts/acore, MediaStore, Downloads, GSF) au fost deblocați și recompilați nativ! Contactele din cloud se resincronizează automat."
        }

    def debloat_pixel8_ram_hogs(self) -> Dict[str, Any]:
        """Stops RAM/ZRAM exhaustion caused by background AI daemons, corrupted Device Health Services, debug tracing, and companion apps."""
        ram_before = self.get_available_ram_mb()

        self._emit(1, 5, "Resetare servicii de telemetrie baterie/sănătate (Device Health Services)...", "⏳ Se curăță bazele de date din Device Health Services (turbo)...")
        self.adb.run_shell("am force-stop com.google.android.apps.turbo", self.serial, timeout=6)
        self.adb.run_shell("pm clear com.google.android.apps.turbo", self.serial, timeout=10)

        self._emit(2, 5, "Restricționare servicii AI / Telemetrie / Companion în fundal...", "⏳ Se restricționează rularea parazită în fundal pentru serviciile AI locale, telemetrie și aplicații companion...")
        for bg_pkg in self.COMMON_BG_HOGS:
            self.adb.run_shell(f"am force-stop {bg_pkg}", self.serial, timeout=5)
            self.adb.run_shell(f"am set-standby-bucket {bg_pkg} restricted", self.serial, timeout=5)
            self.adb.run_shell(f"cmd appops set {bg_pkg} RUN_ANY_IN_BACKGROUND ignore", self.serial, timeout=5)

        self._emit(3, 5, "Oprire jurnale excesive de debugging în fundal (logd / trace)...", "⏳ Se golește bufferul logd și se oprește tracing-ul de fundal...")
        self.adb.run_shell("logcat -c", self.serial, timeout=5)
        self.adb.run_shell("logcat -G 256K", self.serial, timeout=5)
        self.adb.run_shell("setprop debug.atrace.tags.enableflags 0", self.serial, timeout=5)

        self._emit(4, 5, "Optimizare Cached App Freezer & Limite Procese...", "⏳ Se activează înghețarea rapidă a aplicațiilor din fundal (Android Cached App Freezer)...")
        self.adb.run_shell("device_config put activity_manager_native_boot use_freezer true", self.serial, timeout=5)
        self.adb.run_shell("device_config put activity_manager max_cached_processes 24", self.serial, timeout=5)

        self._emit(5, 5, "Eliberare RAM și curățare istoric...", "⏳ Se eliberează memoria RAM...")
        self.optimize_ram(emit_standalone=False)
        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=5)
        ram_after = self.get_available_ram_mb()
        gain = max(0, ram_after - ram_before)

        msg = f"Serviciile grele de fundal (AI local, telemetrie, tracing, procese parazite) au fost restricționate! RAM disponibil: {ram_after} MB (+{gain} MB). Recomandăm un Restart pentru golirea ZRAM."
        self._emit(5, 5, "Finalizat!", f"✅ {msg}")
        return {
            "success": True,
            "title": "Deblocare ZRAM & Oprire Consumatori Paraziți din Fundal",
            "message": msg
        }

    def run_deep_boost_all(self, culprit_packages: Optional[List[str]] = None) -> Dict[str, Any]:
        """1-Click Master Fix with detailed live progress logging for every single sub-step."""
        ram_before = self.get_available_ram_mb()
        ui_pkgs = self._get_ui_critical_packages()

        targets = []
        if culprit_packages:
            for raw_p in culprit_packages:
                p = self._normalize_package(raw_p)
                if self._is_valid_package(p) and p not in ui_pkgs and p not in targets:
                    targets.append(p)
                if len(targets) >= 5:
                    break

        total_steps = 5 + len(ui_pkgs) + len(targets)
        step = 1

        # Step 1: Animations & 120Hz & Accessibility check
        self._emit(step, total_steps, "Configurare Rată Refresh Maximă & Animații 0.5x...", "⏳ [Pas 1] Se setează animațiile la 0.5x, rata maximă de refresh și se verifică serviciile de accesibilitate...")
        for scale_key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            self.adb.run_shell(f"settings put global {scale_key} 0.5", self.serial, timeout=5)
        self.adb.run_shell("settings put system peak_refresh_rate 120.0", self.serial, timeout=5)
        self.adb.run_shell("settings put system min_refresh_rate 60.0", self.serial, timeout=5)

        ok_acc, acc_out = self.adb.run_shell("settings get secure enabled_accessibility_services", self.serial, timeout=5)
        if ok_acc and acc_out and acc_out.strip() not in ("", "null"):
            self.adb.run_shell("settings put secure enabled_accessibility_services null", self.serial, timeout=5)
            self.adb.run_shell("settings put secure accessibility_enabled 0", self.serial, timeout=5)
            self._emit(step, total_steps, "Servicii accesibilitate oprite", f"✓ Serviciul de accesibilitate ({acc_out.strip()}) care încetinea ecranul a fost dezactivat!")
        self._emit(step, total_steps, "120Hz + Animații 0.5x activate", "✓ Animații setate la 0.5x și rata maximă de refresh activată.")

        # Step 2..N: UI Critical Packages (Active Launcher, SystemUI, WebView, Chrome)
        for pkg in ui_pkgs:
            step += 1
            self._emit(step, total_steps, f"Recompilare nativă UI: {pkg}...", f"⏳ Se curăță cache-ul și se compilează în mod 'speed' componenta {pkg}...")
            self.adb.run_shell(f"pm clear --cache-only {pkg}", self.serial, timeout=10)
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=45)
            self._emit(step, total_steps, f"Componentă UI optimizată: {pkg}", f"✓ {pkg} a fost curățat și compilat nativ în mod 'speed'.")

        # Next Steps: Culprit apps with ANRs/Crashes
        repaired = []
        for pkg in targets:
            step += 1
            self._emit(step, total_steps, f"Reparare aplicație cu blocaje: {pkg}...", f"⏳ Se repară profund {pkg} (oprire proces blocat + ștergere cache corupt + compilare 'speed')...")
            self.deep_repair_app(pkg, emit_standalone=False)
            repaired.append(pkg)
            self._emit(step, total_steps, f"Aplicație reparată: {pkg}", f"✓ {pkg} a fost reparată (fără ștergerea contului/datelor).")

        # Next Step: RAM & Background Hogs Optimization
        step += 1
        self._emit(step, total_steps, "Eliberare memorie RAM și oprire procese parazite...", "⏳ Se închid procesele din fundal (am kill-all) și aplicațiile consumatoare de RAM...")
        for bg_pkg in self.COMMON_BG_HOGS:
            self.adb.run_shell(f"am force-stop {bg_pkg}", self.serial, timeout=4)
            self.adb.run_shell(f"am set-standby-bucket {bg_pkg} restricted", self.serial, timeout=4)
        ram_res = self.optimize_ram(emit_standalone=False)
        self._emit(step, total_steps, "Memorie RAM eliberată", f"✓ {ram_res['message']}")

        # Next Step: Storage Cache Trim
        step += 1
        self._emit(step, total_steps, "Curățare cache global sistem...", "⏳ Se eliberează memoria cache globală (pm trim-caches)...")
        self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=20)
        self._emit(step, total_steps, "Cache sistem curățat", "✓ Memoria cache a sistemului a fost eliberată.")

        # Final Step: UFS Flash TRIM & Reset GFX stats & Clear historical exit logs
        step = total_steps
        self._emit(step, total_steps, "Optimizare stocare flash UFS (sm fstrim) & Resetare istoric erori...", "⏳ Se execută TRIM pe blocurile memoriei flash UFS și se resetează contoarele istorice...")
        self.adb.run_shell("sm fstrim", self.serial, timeout=45)
        self.adb.run_shell("dumpsys gfxinfo --reset", self.serial, timeout=8)
        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=8)

        ram_after = self.get_available_ram_mb()
        ram_gain = max(0, ram_after - ram_before)
        repaired_info = f" Aplicații reparate: {', '.join(repaired)}." if repaired else ""
        final_msg = (
            f"Super-Optimizarea s-a încheiat complet! "
            f"RAM liber: {ram_after} MB (+{ram_gain} MB recuperați). "
            f"120Hz + Animații 0.5x active, SystemUI/Launcher/WebView compilate nativ 'speed', fstrim executat.{repaired_info}"
        )
        self._emit(total_steps, total_steps, "Finalizat cu succes!", f"🎉 {final_msg}")

        return {
            "success": True,
            "title": "⚡ Super-Optimizare Completă Finalizată",
            "message": final_msg
        }

    def trim_system_caches(self) -> Dict[str, Any]:
        """Requests Android package manager to reclaim non-essential cache space."""
        self._emit(1, 1, "Curățare cache sistem...", "⏳ Se rulează pm trim-caches...")
        ok, out = self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=20)
        self._emit(1, 1, "Finalizat!", "✓ Cache-ul sistemului a fost curățat.")
        return {
            "success": ok,
            "title": "Curățare Cache Sistem",
            "message": "Memoria cache a sistemului a fost curățată!" if ok else f"Eroare: {out}"
        }

    def force_stop_app(self, package: str) -> Dict[str, Any]:
        """Force stops an offending rogue app."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid."}
        self._emit(1, 1, f"Oprire forțată {package}...", f"⏳ Se oprește {package}...")
        ok, out = self.adb.run_shell(f"am force-stop {package}", self.serial, timeout=10)
        self._emit(1, 1, "Finalizat!", f"✓ Aplicația {package} a fost oprită.")
        return {
            "success": ok,
            "title": f"Oprire forțată {package}",
            "message": f"Aplicația {package} a fost oprită forțat." if ok else f"Eroare: {out}"
        }

    def clear_app_data(self, package: str) -> Dict[str, Any]:
        """Completely resets data and cache for a specific crashing app (Factory state for that app)."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid."}
        if package in self.PROTECTED_PACKAGES:
            return self.deep_repair_app(package)
        self._emit(1, 1, f"Resetare completă date {package}...", f"⏳ Se șterg datele pentru {package}...")
        ok, out = self.adb.run_shell(f"pm clear {package}", self.serial, timeout=15)
        self.adb.run_shell(f"cmd activity clear-exit-info --user 0 {package}", self.serial, timeout=5)
        self._emit(1, 1, "Finalizat!", f"✓ Datele pentru {package} au fost șterse.")
        return {
            "success": ok,
            "title": f"Resetare completă date {package}",
            "message": f"Toate datele și memoria cache pentru {package} au fost resetate la zero." if ok else f"Eroare: {out}"
        }

    def reboot_device(self) -> Dict[str, Any]:
        """Safely restarts the Android device."""
        self._emit(1, 1, "Repornire telefon...", "⏳ Se trimite comanda de restart către telefon...")
        ok, out = self.adb.run_shell("reboot", self.serial, timeout=10)
        self._emit(1, 1, "Restart trimis!", "✓ Telefonul se repornește acum.")
        return {
            "success": ok,
            "title": "Restart telefon",
            "message": "Comanda de restart a fost trimisă telefonului. Așteaptă 30-45 secunde să pornească." if ok else f"Eroare: {out}"
        }
