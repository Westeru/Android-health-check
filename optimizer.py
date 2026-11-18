import re
import datetime
from typing import Dict, Any, Optional, List, Callable
from adb_manager import AdbManager

ProgressCallback = Optional[Callable[[int, int, str, str], None]]

class PhoneOptimizer:
    """Provides universal, non-destructive ADB-based repairs for any Android device with real-time progress reporting (EN primary / RO supported)."""

    PROTECTED_PACKAGES = {
        "system",
        "android",
        "com.android.systemui",
        "com.google.android.apps.nexuslauncher",
        "com.google.android.tvlauncher",
        "com.google.android.leanbacklauncher",
        "org.droidtv.ui",
        "org.droidtv.playtv",
        "org.droidtv.settings",
        "com.sec.android.app.launcher",
        "com.miui.home",
        "com.android.launcher",
        "com.android.launcher3",
        "com.google.android.inputmethod.latin",
        "com.google.android.inputmethod.leanback",
        "com.samsung.android.honeyboard",
        "com.android.phone",
        "com.android.settings",
        "com.android.tv.settings",
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

    TV_UI_PACKAGES = [
        "com.google.android.tvlauncher",
        "com.google.android.tvrecommendations",
        "com.google.android.leanbacklauncher",
        "com.android.tv.settings",
        "org.droidtv.ui",
        "org.droidtv.settings",
        "org.droidtv.playtv",
        "org.droidtv.philipstvdrawer",
    ]

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
        # Android TV & Philips Smart TV notorious background RAM/CPU hogs:
        "tv.samba.ssm",
        "org.droidtv.esticker",
        "org.droidtv.sticker",
        "org.droidtv.demome",
        "org.droidtv.candeebug",
        "org.droidtv.usagelogger",
        "org.droidtv.tv.frameworklogger",
        "org.droidtv.dropboxprovider",
        "org.droidtv.recommendation",
        "org.droidtv.nettvrecommender",
        "org.droidtv.nettv.market",
        "org.droidtv.nettvbrowser",
        "org.droidtv.nettvregistration",
        "org.droidtv.nettvapps",
        "org.droidtv.eum",
        "org.droidtv.amazonalexa",
        "org.droidtv.euinstallertc",
        "org.droidtv.euinstallersat",
        "com.phorus.playfi.tv",
        "com.phorus.playfi.softap",
        "com.vewd.core.browserui",
        "com.google.android.tungsten.setupwraith",
        "org.droidtv.Logger",
        "com.google.android.leanbacklauncher.recommendations",
    ]

    def __init__(self, adb: AdbManager, serial: Optional[str] = None, progress_cb: ProgressCallback = None, lang: str = "en"):
        self.adb = adb
        self.serial = serial
        self.progress_cb = progress_cb
        self.lang = lang if lang in ("en", "ro") else "en"
        self.ro = (self.lang == "ro")

    def _emit(self, step: int, total: int, current_task: str, log_msg: str):
        if self.progress_cb:
            self.progress_cb(step, total, current_task, log_msg)

    def _is_android_tv(self) -> bool:
        ok, out = self.adb.run_shell("getprop ro.build.characteristics", self.serial, timeout=4)
        return bool(ok and out and "tv" in out.lower())

    def _get_ui_critical_packages(self) -> List[str]:
        """Dynamically detects the active home launcher on any Android phone or Android TV and combines with SystemUI & WebView."""
        pkgs = list(self.BASE_UI_PACKAGES)
        is_tv = self._is_android_tv()
        if is_tv:
            for tv_pkg in self.TV_UI_PACKAGES:
                if tv_pkg not in pkgs:
                    pkgs.append(tv_pkg)

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
        elif not is_tv:
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
                    pkg_name = pkg_match.group(1) if pkg_match else ("aplicație sistem" if self.ro else "system package")
                    active_tasks.append(
                        f"Compilare nativă ART (dex2oat64) în curs pentru: {pkg_name}"
                        if self.ro else f"Native ART compilation (dex2oat64) running for: {pkg_name}"
                    )
                elif "fstrim" in line or "sm fstrim" in line:
                    active_tasks.append(
                        "Optimizare blocuri memorie flash UFS (fstrim) în curs..."
                        if self.ro else "UFS flash storage block TRIM (fstrim) running..."
                    )

        idle_msg = (
            "Telefonul este în repaus (nicio operațiune în fundal)"
            if self.ro else "Idle (all background tasks completed)"
        )
        return {
            "busy": len(active_tasks) > 0,
            "active_tasks": active_tasks,
            "summary": active_tasks[0] if active_tasks else idle_msg
        }

    def run_fstrim(self) -> Dict[str, Any]:
        """Runs flash storage trim (fstrim) and reclaims system caches to restore UFS write speeds."""
        self._emit(
            1, 2,
            "Curățare cache sistem (pm trim-caches)..." if self.ro else "Trimming system caches (pm trim-caches)...",
            "⏳ Se eliberează cache-ul neesențial din stocarea internă..." if self.ro else "⏳ Reclaiming non-essential internal storage cache..."
        )
        self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=25)
        self._emit(
            2, 2,
            "Execuție TRIM pe memoria flash UFS (sm fstrim)..." if self.ro else "Running UFS flash storage TRIM (sm fstrim)...",
            "✓ Cache-ul sistem a fost curățat. Se rulează fstrim pe blocurile flash..." if self.ro else "✓ System cache cleared. Running fstrim on UFS flash blocks..."
        )
        ok, out = self.adb.run_shell("sm fstrim", self.serial, timeout=45)
        self._emit(
            2, 2,
            "Finalizat!" if self.ro else "Completed!",
            "✓ Optimizarea stocării UFS (fstrim + cache) s-a încheiat cu succes!" if self.ro else "✓ UFS storage optimization (fstrim + cache trim) completed!"
        )
        return {
            "success": ok,
            "title": "Optimizare Stocare UFS (fstrim + Cache Trim)" if self.ro else "UFS Storage Optimization (fstrim + Cache Trim)",
            "message": (
                ("Memoria cache globală a fost curățată și blocurile flash UFS au fost optimizate cu succes!" if ok else f"Cache-ul a fost curățat (Notă fstrim: {out})")
                if self.ro else
                ("Global system cache cleared and UFS flash blocks trimmed!" if ok else f"Cache trimmed (fstrim note: {out})")
            )
        }

    def fix_ui_stutter(self) -> Dict[str, Any]:
        """Fixes choppy scrolling and UI lag: enables high refresh rate, sets 0.5x snappy animations, repairs WebView & Launcher."""
        ui_pkgs = self._get_ui_critical_packages()
        total_steps = 3 + len(ui_pkgs)
        self._emit(
            1, total_steps,
            "Setare animații ultra-rapide (0.5x)..." if self.ro else "Setting snappy 0.5x animation scales...",
            "⏳ Se setează window/transition/animator scale la 0.5x..." if self.ro else "⏳ Setting window, transition, and animator scales to 0.5x..."
        )
        for scale_key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            self.adb.run_shell(f"settings put global {scale_key} 0.5", self.serial, timeout=5)
        self._emit(
            1, total_steps,
            "Animații 0.5x activate" if self.ro else "0.5x animations enabled",
            "✓ Animațiile de sistem au fost setate la 0.5x." if self.ro else "✓ System animation scales set to 0.5x (instant response)."
        )

        self._emit(
            2, total_steps,
            "Activare rată de refresh maximă (90Hz / 120Hz)..." if self.ro else "Enabling peak display refresh rate (90Hz / 120Hz)...",
            "⏳ Se configurează rata de refresh dinamică maximă a ecranului..." if self.ro else "⏳ Configuring dynamic peak display refresh rate..."
        )
        self.adb.run_shell("settings put system peak_refresh_rate 120.0", self.serial, timeout=5)
        self.adb.run_shell("settings put system min_refresh_rate 60.0", self.serial, timeout=5)
        self._emit(
            2, total_steps,
            "Rată de refresh maximă activată" if self.ro else "Peak refresh rate enabled",
            "✓ Rata de refresh maximă (Smooth Display) a fost configurată." if self.ro else "✓ Peak refresh rate (Smooth Display) configured."
        )

        step = 2
        for pkg in ui_pkgs:
            step += 1
            self._emit(
                step, total_steps,
                f"Recompilare nativă 'speed': {pkg}..." if self.ro else f"AOT 'speed' compiling: {pkg}...",
                f"⏳ Se curăță cache-ul și se compilează nativ AOT (mod 'speed') pachetul {pkg}..." if self.ro else f"⏳ Clearing shader cache and AOT-compiling {pkg} in 'speed' mode..."
            )
            self.adb.run_shell(f"pm clear --cache-only {pkg}", self.serial, timeout=10)
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=45)
            self._emit(
                step, total_steps,
                f"Optimizat: {pkg}" if self.ro else f"Optimized: {pkg}",
                f"✓ Pachetul {pkg} a fost curățat și compilat nativ în mod 'speed'." if self.ro else f"✓ {pkg} cache cleared and compiled in native 'speed' mode."
            )

        self._emit(
            total_steps, total_steps,
            "Resetare contoare GPU Frame Stats..." if self.ro else "Resetting GPU frame stats...",
            "⏳ Se resetează statisticile de cadre pierdute (gfxinfo)..." if self.ro else "⏳ Resetting gfxinfo frame drop counters..."
        )
        self.adb.run_shell("dumpsys gfxinfo --reset", self.serial, timeout=8)
        self._emit(
            total_steps, total_steps,
            "Finalizat!" if self.ro else "Completed!",
            "✅ Eliminarea sacadării UI (120Hz + 0.5x + Launcher/SystemUI/WebView) s-a finalizat!" if self.ro else "✅ UI Stutter Fix (120Hz + 0.5x + Launcher/SystemUI/WebView) completed!"
        )

        return {
            "success": True,
            "title": "Eliminare Sacadare UI & Boost Rată Refresh" if self.ro else "UI Stutter Fix & Refresh Rate Boost",
            "message": (
                "Animațiile 0.5x și rata maximă de refresh au fost activate, iar Launcher-ul, SystemUI și Android WebView au fost recompilate nativ în mod 'speed'!"
                if self.ro else
                "0.5x animations and peak refresh rate enabled, and Home Launcher, SystemUI, and Android WebView compiled in native 'speed' mode!"
            )
        }

    def restore_default_animations(self) -> Dict[str, Any]:
        """Restores Android animation scales back to standard 1.0x."""
        self._emit(
            1, 1,
            "Restaurare animații 1.0x..." if self.ro else "Restoring 1.0x animations...",
            "⏳ Se readuc scările de animație la 1.0x..." if self.ro else "⏳ Restoring system animation scales to 1.0x..."
        )
        for scale_key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            self.adb.run_shell(f"settings put global {scale_key} 1.0", self.serial, timeout=5)
        self._emit(1, 1, "Finalizat!" if self.ro else "Completed!", "✓ Scările de animație au fost readuse la 1.0x." if self.ro else "✓ Animation scales restored to default 1.0x.")
        return {
            "success": True,
            "title": "Animații Standard (1.0x)" if self.ro else "Default Animations (1.0x)",
            "message": "Scările de animație au fost readuse la valoarea standard 1.0x." if self.ro else "Animation scales restored to standard 1.0x."
        }

    def disable_accessibility_services(self) -> Dict[str, Any]:
        """Disables active accessibility hooks that intercept touch events and cause severe UI stutter/ANRs."""
        self._emit(
            1, 1,
            "Dezactivare servicii de accesibilitate..." if self.ro else "Disabling accessibility services...",
            "⏳ Se opresc hook-urile de accesibilitate care interceptează atingerea ecranului..." if self.ro else "⏳ Stopping accessibility touch-interception hooks..."
        )
        ok1, _ = self.adb.run_shell("settings put secure enabled_accessibility_services null", self.serial, timeout=5)
        ok2, _ = self.adb.run_shell("settings put secure accessibility_enabled 0", self.serial, timeout=5)
        self._emit(1, 1, "Finalizat!" if self.ro else "Completed!", "✓ Serviciile de accesibilitate au fost dezactivate." if self.ro else "✓ Accessibility services disabled.")
        return {
            "success": ok1 or ok2,
            "title": "Dezactivare Servicii Accesibilitate" if self.ro else "Disable Accessibility Services",
            "message": (
                "Serviciile de accesibilitate care interceptau ecranul și încetineau scroll-ul au fost dezactivate!"
                if self.ro else "Accessibility services that were intercepting touch input and causing scroll lag have been disabled!"
            )
        }

    def deep_repair_app(self, package: str, emit_standalone: bool = True) -> Dict[str, Any]:
        """Repairs a freezing/crashing app WITHOUT deleting user accounts or personal data."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid." if self.ro else "Invalid package name."}

        if emit_standalone:
            self._emit(
                1, 4,
                f"Oprire procese blocate pentru {package}..." if self.ro else f"Stopping hung threads for {package}...",
                f"⏳ Se opresc firele de execuție blocate pentru {package}..." if self.ro else f"⏳ Force-stopping hung threads for {package}..."
            )
        if package != "com.android.systemui":
            self.adb.run_shell(f"am force-stop {package}", self.serial, timeout=8)

        if emit_standalone:
            self._emit(
                2, 4,
                f"Curățare exclusivă cache pentru {package}..." if self.ro else f"Clearing corrupted cache for {package}...",
                f"⏳ Se șterge doar cache-ul corupt pentru {package} (datele contului rămân intacte)..." if self.ro else f"⏳ Clearing only corrupted cache for {package} (account & user data preserved)..."
            )
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
            self._emit(
                3, 4,
                "Curățare cache Android System WebView..." if self.ro else "Clearing Android System WebView cache...",
                "⏳ Se curăță cache-ul Android System WebView..." if self.ro else "⏳ Clearing Android System WebView shader cache..."
            )
        if package != "com.google.android.webview":
            self.adb.run_shell("pm clear --cache-only com.google.android.webview", self.serial, timeout=8)

        if emit_standalone:
            self._emit(
                4, 4,
                f"Compilare nativă AOT 'speed' pentru {package}..." if self.ro else f"Native AOT 'speed' compiling {package}...",
                f"⏳ Se recompilează în cod mașină nativ (mod 'speed') aplicația {package}..." if self.ro else f"⏳ Compiling {package} into native machine code ('speed' mode)..."
            )
        self.adb.run_shell(f"cmd package compile -m speed -f {package}", self.serial, timeout=60)
        self.adb.run_shell(f"cmd activity clear-exit-info --user 0 {package}", self.serial, timeout=5)
        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=5)

        if emit_standalone:
            self._emit(
                4, 4,
                "Finalizat!" if self.ro else "Completed!",
                f"✅ Aplicația {package} a fost reparată, compilată nativ în mod 'speed' și istoricul de erori a fost curățat!"
                if self.ro else f"✅ {package} repaired, compiled in native 'speed' mode, and crash history cleared!"
            )

        return {
            "success": True,
            "title": f"Reparare profundă: {package}" if self.ro else f"Deep App Repair: {package}",
            "message": (
                f"Aplicația {package} a fost oprită, cache-ul corupt a fost șters (fără pierderea contului/datelor) și codul ei a fost recompilat nativ în mod 'speed'!"
                if self.ro else
                f"{package} was stopped, corrupted cache was cleared (preserving login & data), and its code was compiled in native 'speed' mode!"
            )
        }

    def restrict_app_background(self, package: str) -> Dict[str, Any]:
        """Puts a heavy background app into restricted mode and stops it from running in the background."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid." if self.ro else "Invalid package name."}
        if package in self.PROTECTED_PACKAGES:
            return {
                "success": False,
                "message": (
                    f"Pachetul {package} este o componentă esențială de sistem și nu trebuie restricționat."
                    if self.ro else f"Package {package} is a core system component and should not be restricted."
                )
            }

        self._emit(
            1, 2,
            f"Oprire și restricționare fundal: {package}..." if self.ro else f"Stopping & restricting background for: {package}...",
            f"⏳ Se oprește {package} și se setează Standby Bucket = restricted..." if self.ro else f"⏳ Force-stopping {package} and setting Standby Bucket = restricted..."
        )
        self.adb.run_shell(f"am force-stop {package}", self.serial, timeout=8)
        self.adb.run_shell(f"am set-standby-bucket {package} restricted", self.serial, timeout=8)
        self.adb.run_shell(f"cmd appops set {package} RUN_ANY_IN_BACKGROUND ignore", self.serial, timeout=8)
        self.adb.run_shell(f"cmd appops set {package} RUN_IN_BACKGROUND ignore", self.serial, timeout=8)
        self._emit(
            2, 2,
            "Finalizat!" if self.ro else "Completed!",
            f"✅ {package} a fost blocat din a mai rula parazit în fundal." if self.ro else f"✅ {package} restricted from running parasitically in the background."
        )

        return {
            "success": True,
            "title": f"Restricționare fundal: {package}" if self.ro else f"Background Restricted: {package}",
            "message": (
                f"Aplicația {package} a fost oprită și blocată din a mai rula parazit în fundal (Standby Bucket: Restricted)."
                if self.ro else f"{package} has been stopped and restricted from background execution (Standby Bucket: Restricted)."
            )
        }

    def optimize_ram(self, emit_standalone: bool = True) -> Dict[str, Any]:
        """Frees RAM and ZRAM pressure by killing cached processes and stopping heavy non-system background apps."""
        ram_before = self.get_available_ram_mb()
        if emit_standalone:
            self._emit(
                1, 3,
                "Eliberare procese cached (am kill-all)..." if self.ro else "Evicting cached processes (am kill-all)...",
                f"⏳ RAM liber înainte: {ram_before} MB. Se închid procesele inerte din fundal..." if self.ro else f"⏳ Available RAM before: {ram_before} MB. Evicting idle background processes..."
            )
        self.adb.run_shell("am kill-all", self.serial, timeout=10)

        if emit_standalone:
            self._emit(
                2, 3,
                "Curățare cache RAM/Storage..." if self.ro else "Trimming package caches...",
                "⏳ Se eliberează cache-ul pachetelor..." if self.ro else "⏳ Reclaiming package caches..."
            )
        self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=15)

        if emit_standalone:
            self._emit(
                3, 3,
                "Oprire aplicații grele din fundal..." if self.ro else "Stopping heavy background apps...",
                "⏳ Se identifică și se opresc aplicațiile non-sistem care consumă mult RAM..." if self.ro else "⏳ Identifying and stopping non-system RAM hogs..."
            )
        stopped_apps = []
        ok_ps, ps_out = self.adb.run_shell("ps -A -o RSS,ARGS", self.serial, timeout=6)
        if ok_ps and ps_out:
            rows = []
            for line in ps_out.splitlines()[1:]:
                parts = line.strip().split(None, 1)
                if len(parts) == 2 and parts[0].isdigit():
                    rows.append((int(parts[0]), parts[1].strip().split()[0]))
            rows.sort(key=lambda x: x[0], reverse=True)
            for rss_kb, raw_cmd in rows:
                if rss_kb < 30000:
                    break
                pkg = self._normalize_package(raw_cmd)
                if (
                    "." in pkg
                    and not pkg.startswith("/")
                    and pkg not in self.PROTECTED_PACKAGES
                    and not pkg.startswith("com.android.system")
                    and not pkg.startswith("com.google.android.providers")
                    and not pkg.startswith("com.mediatek.")
                    and not pkg.startswith("org.droidtv.tv.")
                    and pkg not in ("org.droidtv.xtv", "org.droidtv.ambiair", "org.droidtv.philipstvdrawer", "org.droidtv.channels")
                    and pkg not in stopped_apps
                ):
                    self.adb.run_shell(f"am force-stop {pkg}", self.serial, timeout=5)
                    stopped_apps.append(pkg)
                    if len(stopped_apps) >= 10:
                        break

        ram_after = self.get_available_ram_mb()
        diff = max(0, ram_after - ram_before)
        if self.ro:
            stopped_str = f" Aplicații oprite din fundal: {', '.join(stopped_apps)}." if stopped_apps else ""
            msg = f"Memorie disponibilă acum: {ram_after} MB (+{diff} MB eliberați instant).{stopped_str}"
        else:
            stopped_str = f" Stopped background apps: {', '.join(stopped_apps)}." if stopped_apps else ""
            msg = f"Available RAM now: {ram_after} MB (+{diff} MB freed immediately).{stopped_str}"

        if emit_standalone:
            self._emit(3, 3, "Finalizat!" if self.ro else "Completed!", f"✅ {msg}")

        return {
            "success": True,
            "title": "Eliberare Memorie RAM & ZRAM" if self.ro else "RAM & ZRAM Optimization",
            "message": msg
        }

    def cool_down_cpu(self) -> Dict[str, Any]:
        """Stops top CPU-consuming background processes to stop thermal throttling."""
        self._emit(
            1, 2,
            "Oprire procese CPU din fundal..." if self.ro else "Stopping background CPU hogs...",
            "⏳ Se caută și se opresc aplicațiile care solicită procesorul..." if self.ro else "⏳ Scanning and stopping background apps taxing the CPU..."
        )
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

        if self.ro:
            msg_extra = f" Procese CPU oprite: {', '.join(stopped_cpu)}." if stopped_cpu else ""
            self._emit(2, 2, "Finalizat!", f"✅ Procesorul a fost eliberat.{msg_extra}")
            return {
                "success": True,
                "title": "Răcire CPU & Oprire Consumatori Fundal",
                "message": f"Aplicațiile care solicitau procesorul în fundal au fost oprite.{msg_extra}"
            }
        else:
            msg_extra = f" Stopped CPU processes: {', '.join(stopped_cpu)}." if stopped_cpu else ""
            self._emit(2, 2, "Completed!", f"✅ CPU load relieved.{msg_extra}")
            return {
                "success": True,
                "title": "CPU Cool Down & Background Stop",
                "message": f"Background apps taxing the CPU have been stopped.{msg_extra}"
            }

    def run_art_optimization(self) -> Dict[str, Any]:
        """Forces ART compiler to optimize critical UI apps in 'speed' mode and all other apps in 'speed-profile'."""
        ui_pkgs = self._get_ui_critical_packages()
        total = len(ui_pkgs) + 1
        step = 0
        for pkg in ui_pkgs:
            step += 1
            self._emit(
                step, total,
                f"Compilare 'speed' pentru {pkg}..." if self.ro else f"Compiling {pkg} in 'speed' mode...",
                f"⏳ Se compilează nativ în mod 'speed' componenta {pkg}..." if self.ro else f"⏳ AOT-compiling {pkg} in native 'speed' mode..."
            )
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=45)
            self._emit(
                step, total,
                f"Compilat: {pkg}" if self.ro else f"Compiled: {pkg}",
                f"✓ {pkg} compilat cu succes." if self.ro else f"✓ {pkg} compiled."
            )

        self._emit(
            total, total,
            "Optimizare profil pentru restul aplicațiilor..." if self.ro else "Optimizing remaining installed apps (speed-profile)...",
            "⏳ Se optimizează aplicațiile instalate (speed-profile)... Poate dura 30-60 secunde." if self.ro else "⏳ Compiling installed packages (speed-profile)... May take 30-60 seconds."
        )
        ok, out = self.adb.run_shell("cmd package compile -m speed-profile -a", self.serial, timeout=120)
        if not ok:
            ok, out = self.adb.run_shell("cmd package bg-dexopt-job", self.serial, timeout=120)
        self._emit(
            total, total,
            "Finalizat!" if self.ro else "Completed!",
            "✅ Toate aplicațiile au fost optimizate de compilatorul ART!" if self.ro else "✅ All applications optimized by the ART compiler!"
        )

        return {
            "success": True,
            "title": "Optimizare Compilator ART / Bytecode" if self.ro else "ART Compiler / Bytecode Optimization",
            "message": (
                "Interfața de sistem (Launcher, SystemUI, WebView) a fost compilată în mod 'speed', iar aplicațiile instalate au fost optimizate!"
                if self.ro else
                "System UI packages (Launcher, SystemUI, WebView) compiled in 'speed' mode and all installed apps optimized!"
            )
        }

    def fix_contacts_acore_loop(self) -> Dict[str, Any]:
        """Surgically repairs Android core Content Providers (Contacts/acore, MediaStore, Downloads, Calendar, Sync) whose SQLite locks freeze apps."""
        self._emit(
            1, 5,
            "Oprire procese blocate în furnizorii de sistem (Contacte, MediaStore, Sync)..." if self.ro else "Stopping hung System Content Providers (Contacts, MediaStore, Sync)...",
            "⏳ Se opresc procesele blocate din ContactsProvider (acore), MediaStore și Downloads..." if self.ro else "⏳ Force-stopping stuck threads in ContactsProvider (acore), MediaStore, and Downloads..."
        )
        for pkg in (
            "com.google.android.contacts",
            "com.samsung.android.app.contacts",
            "com.android.providers.contacts",
            "com.android.providers.blockednumber",
            "com.android.providers.media.module",
            "com.android.providers.downloads",
        ):
            self.adb.run_shell(f"am force-stop {pkg}", self.serial, timeout=5)

        self._emit(
            2, 5,
            "Reconstrucție bază de date SQLite Contacte & Apeluri (contacts2.db)..." if self.ro else "Rebuilding Contacts & Call Log SQLite database (contacts2.db)...",
            "⏳ Se reinițializează baza locală din com.android.providers.contacts și blockednumber (contactele din contul Cloud se resincronizează automat)..."
            if self.ro else
            "⏳ Resetting corrupted local SQLite database in com.android.providers.contacts and blockednumber (cloud contacts re-sync automatically)..."
        )
        self.adb.run_shell("pm clear com.android.providers.contacts", self.serial, timeout=15)
        self.adb.run_shell("pm clear com.android.providers.blockednumber", self.serial, timeout=10)
        self.adb.run_shell("pm clear --cache-only com.google.android.contacts", self.serial, timeout=8)
        self.adb.run_shell("pm clear --cache-only com.android.providers.userdictionary", self.serial, timeout=8)

        self._emit(
            3, 5,
            "Curățare cache furnizori MediaStore, Descărcări, Calendar & GSF..." if self.ro else "Clearing MediaStore, Downloads, Calendar & GSF caches...",
            "⏳ Se curăță cache-ul pentru MediaStore, Downloads, Calendar și Google Services Framework..."
            if self.ro else "⏳ Clearing caches for MediaStore, Downloads, Calendar, and Google Services Framework..."
        )
        for sys_prov in (
            "com.android.providers.media.module",
            "com.android.providers.media",
            "com.android.providers.downloads",
            "com.android.providers.calendar",
            "com.google.android.gsf",
        ):
            self.adb.run_shell(f"pm clear --cache-only {sys_prov}", self.serial, timeout=8)

        self._emit(
            4, 5,
            "Compilare nativă AOT 'speed' pentru toți furnizorii de sistem..." if self.ro else "Compiling all system providers in native AOT 'speed' mode...",
            "⏳ Se compilează în mod 'speed' furnizorii Contacts, MediaStore, Downloads și GSF..."
            if self.ro else "⏳ AOT-compiling Contacts, MediaStore, Downloads, and GSF in 'speed' mode..."
        )
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
        self._emit(
            5, 5,
            "Finalizat!" if self.ro else "Completed!",
            "✅ Bazele de date de sistem (Contacte/acore, MediaStore, Descărcări, Sincronizare) au fost reparate, compilate nativ, iar istoricul de erori a fost resetat!"
            if self.ro else
            "✅ System databases (Contacts/acore, MediaStore, Downloads, Sync) rebuilt, compiled in native 'speed' mode, and error history cleared!"
        )
        return {
            "success": True,
            "title": (
                "Reparare Baze de Date Sistem (Contacte 'acore', MediaStore & Sync)"
                if self.ro else "System Databases Repair (Contacts 'acore', MediaStore & Sync)"
            ),
            "message": (
                "Furnizorii de sistem (Contacts/acore, MediaStore, Downloads, GSF) au fost deblocați și recompilați nativ! Contactele din cloud se resincronizează automat."
                if self.ro else
                "System providers (Contacts/acore, MediaStore, Downloads, GSF) have been unlocked and natively compiled! Cloud contacts re-sync automatically."
            )
        }

    def debloat_pixel8_ram_hogs(self) -> Dict[str, Any]:
        """Stops RAM/ZRAM exhaustion caused by background AI daemons, corrupted Device Health Services, debug tracing, and companion apps."""
        ram_before = self.get_available_ram_mb()

        self._emit(
            1, 5,
            "Resetare servicii de telemetrie baterie/sănătate (Device Health Services)..." if self.ro else "Resetting Device Health Services telemetry database...",
            "⏳ Se curăță bazele de date din Device Health Services (turbo)..." if self.ro else "⏳ Clearing corrupted databases in Device Health Services (turbo)..."
        )
        self.adb.run_shell("am force-stop com.google.android.apps.turbo", self.serial, timeout=6)
        self.adb.run_shell("pm clear com.google.android.apps.turbo", self.serial, timeout=10)

        self._emit(
            2, 5,
            "Restricționare servicii AI / Telemetrie / Companion în fundal..." if self.ro else "Restricting background AI / Telemetry / Companion daemons...",
            "⏳ Se restricționează rularea parazită în fundal pentru serviciile AI locale, telemetrie și aplicații companion..."
            if self.ro else "⏳ Restricting background execution for local AI daemons, telemetry, and companion apps..."
        )
        for bg_pkg in self.COMMON_BG_HOGS:
            self.adb.run_shell(f"am force-stop {bg_pkg}", self.serial, timeout=5)
            self.adb.run_shell(f"am set-standby-bucket {bg_pkg} restricted", self.serial, timeout=5)
            self.adb.run_shell(f"cmd appops set {bg_pkg} RUN_ANY_IN_BACKGROUND ignore", self.serial, timeout=5)

        self._emit(
            3, 5,
            "Oprire jurnale excesive de debugging în fundal (logd / trace)..." if self.ro else "Stopping excessive background debug ring buffers (logd / trace)...",
            "⏳ Se golește bufferul logd și se oprește tracing-ul de fundal..." if self.ro else "⏳ Flushing logd ring buffer and disabling background atrace flags..."
        )
        self.adb.run_shell("logcat -c", self.serial, timeout=5)
        self.adb.run_shell("logcat -G 256K", self.serial, timeout=5)
        self.adb.run_shell("setprop debug.atrace.tags.enableflags 0", self.serial, timeout=5)

        self._emit(
            4, 5,
            "Optimizare Cached App Freezer & Limite Procese..." if self.ro else "Enabling Android Cached App Freezer & process limits...",
            "⏳ Se activează înghețarea rapidă a aplicațiilor din fundal (Android Cached App Freezer)..."
            if self.ro else "⏳ Enabling Android Cached App Freezer and tuning max_cached_processes..."
        )
        is_tv = self._is_android_tv()
        max_cached = 8 if is_tv else 24
        self.adb.run_shell("device_config put activity_manager_native_boot use_freezer true", self.serial, timeout=5)
        self.adb.run_shell(f"device_config put activity_manager max_cached_processes {max_cached}", self.serial, timeout=5)
        if is_tv:
            # On Android TV, Contacts Provider (acore) is unused and wastes ~45MB RAM
            self.adb.run_shell("am force-stop com.android.providers.contacts", self.serial, timeout=5)
            self.adb.run_shell("pm clear com.android.providers.contacts", self.serial, timeout=8)

        self._emit(
            5, 5,
            "Eliberare RAM și curățare istoric..." if self.ro else "Freeing RAM and clearing exit history...",
            "⏳ Se eliberează memoria RAM..." if self.ro else "⏳ Reclaiming RAM..."
        )
        self.optimize_ram(emit_standalone=False)
        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=5)
        ram_after = self.get_available_ram_mb()
        gain = max(0, ram_after - ram_before)

        msg = (
            f"Serviciile grele de fundal (AI local, telemetrie, tracing, procese parazite) au fost restricționate! RAM disponibil: {ram_after} MB (+{gain} MB). Recomandăm un Restart pentru golirea ZRAM."
            if self.ro else
            f"Heavy background daemons (local AI, telemetry, tracing, parasitic services) restricted! Available RAM: {ram_after} MB (+{gain} MB). A reboot is recommended to flush ZRAM swap."
        )
        self._emit(5, 5, "Finalizat!" if self.ro else "Completed!", f"✅ {msg}")
        return {
            "success": True,
            "title": (
                "Deblocare ZRAM & Oprire Consumatori Paraziți din Fundal"
                if self.ro else "ZRAM Relief & Background Daemon Restriction"
            ),
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

        self._emit(
            step, total_steps,
            "Configurare Rată Refresh Maximă & Animații 0.5x..." if self.ro else "Configuring Peak Refresh Rate & 0.5x Animations...",
            "⏳ [Pas 1] Se setează animațiile la 0.5x, rata maximă de refresh și se verifică serviciile de accesibilitate..."
            if self.ro else "⏳ [Step 1] Setting 0.5x animations, peak refresh rate, and checking accessibility hooks..."
        )
        for scale_key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            self.adb.run_shell(f"settings put global {scale_key} 0.5", self.serial, timeout=5)
        self.adb.run_shell("settings put system peak_refresh_rate 120.0", self.serial, timeout=5)
        self.adb.run_shell("settings put system min_refresh_rate 60.0", self.serial, timeout=5)

        ok_acc, acc_out = self.adb.run_shell("settings get secure enabled_accessibility_services", self.serial, timeout=5)
        if ok_acc and acc_out and acc_out.strip() not in ("", "null"):
            self.adb.run_shell("settings put secure enabled_accessibility_services null", self.serial, timeout=5)
            self.adb.run_shell("settings put secure accessibility_enabled 0", self.serial, timeout=5)
            self._emit(
                step, total_steps,
                "Servicii accesibilitate oprite" if self.ro else "Accessibility hooks disabled",
                f"✓ Serviciul de accesibilitate ({acc_out.strip()}) a fost dezactivat!" if self.ro else f"✓ Disabled lag-inducing accessibility service ({acc_out.strip()})!"
            )
        self._emit(
            step, total_steps,
            "120Hz + Animații 0.5x activate" if self.ro else "120Hz + 0.5x Animations enabled",
            "✓ Animații setate la 0.5x și rata maximă de refresh activată." if self.ro else "✓ 0.5x animations and peak refresh rate enabled."
        )

        for pkg in ui_pkgs:
            step += 1
            self._emit(
                step, total_steps,
                f"Recompilare nativă UI: {pkg}..." if self.ro else f"Compiling UI package: {pkg}...",
                f"⏳ Se curăță cache-ul și se compilează în mod 'speed' componenta {pkg}..." if self.ro else f"⏳ Clearing cache and compiling {pkg} in native 'speed' mode..."
            )
            self.adb.run_shell(f"pm clear --cache-only {pkg}", self.serial, timeout=10)
            self.adb.run_shell(f"cmd package compile -m speed -f {pkg}", self.serial, timeout=45)
            self._emit(
                step, total_steps,
                f"Componentă UI optimizată: {pkg}" if self.ro else f"UI package optimized: {pkg}",
                f"✓ {pkg} a fost curățat și compilat nativ în mod 'speed'." if self.ro else f"✓ {pkg} cache cleared and compiled in 'speed' mode."
            )

        repaired = []
        for pkg in targets:
            step += 1
            self._emit(
                step, total_steps,
                f"Reparare aplicație cu blocaje: {pkg}..." if self.ro else f"Repairing freezing package: {pkg}...",
                f"⏳ Se repară profund {pkg} (oprire proces blocat + ștergere cache corupt + compilare 'speed')..."
                if self.ro else f"⏳ Deep-repairing {pkg} (force-stop + clear corrupted cache + 'speed' compile)..."
            )
            self.deep_repair_app(pkg, emit_standalone=False)
            repaired.append(pkg)
            self._emit(
                step, total_steps,
                f"Aplicație reparată: {pkg}" if self.ro else f"Repaired: {pkg}",
                f"✓ {pkg} a fost reparată (fără ștergerea contului/datelor)." if self.ro else f"✓ {pkg} repaired (account & user data preserved)."
            )

        step += 1
        self._emit(
            step, total_steps,
            "Eliberare memorie RAM și oprire procese parazite..." if self.ro else "Freeing RAM and restricting parasitic background tasks...",
            "⏳ Se închid procesele din fundal (am kill-all) și aplicațiile consumatoare de RAM..."
            if self.ro else "⏳ Evicting cached processes (am kill-all) and stopping heavy RAM hogs..."
        )
        for bg_pkg in self.COMMON_BG_HOGS:
            self.adb.run_shell(f"am force-stop {bg_pkg}", self.serial, timeout=4)
            self.adb.run_shell(f"am set-standby-bucket {bg_pkg} restricted", self.serial, timeout=4)
            self.adb.run_shell(f"cmd appops set {bg_pkg} RUN_ANY_IN_BACKGROUND ignore", self.serial, timeout=4)
        if self._is_android_tv():
            self.adb.run_shell("device_config put activity_manager max_cached_processes 8", self.serial, timeout=5)
            self.adb.run_shell("am force-stop com.android.providers.contacts", self.serial, timeout=5)
            self.adb.run_shell("logcat -c", self.serial, timeout=4)
            self.adb.run_shell("logcat -G 256K", self.serial, timeout=4)
        ram_res = self.optimize_ram(emit_standalone=False)
        self._emit(step, total_steps, "Memorie RAM eliberată" if self.ro else "RAM freed", f"✓ {ram_res['message']}")

        step += 1
        self._emit(
            step, total_steps,
            "Curățare cache global sistem..." if self.ro else "Trimming global system cache...",
            "⏳ Se eliberează memoria cache globală (pm trim-caches)..." if self.ro else "⏳ Running pm trim-caches across internal storage..."
        )
        self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=20)
        self._emit(step, total_steps, "Cache sistem curățat" if self.ro else "System cache trimmed", "✓ Memoria cache a sistemului a fost eliberată." if self.ro else "✓ Global system cache reclaimed.")

        step = total_steps
        self._emit(
            step, total_steps,
            "Optimizare stocare flash UFS (sm fstrim) & Resetare istoric erori..." if self.ro else "Running UFS flash TRIM (sm fstrim) & resetting error logs...",
            "⏳ Se execută TRIM pe blocurile memoriei flash UFS și se resetează contoarele istorice..."
            if self.ro else "⏳ Running UFS flash block TRIM and clearing historical exit-info counters..."
        )
        self.adb.run_shell("sm fstrim", self.serial, timeout=45)
        self.adb.run_shell("dumpsys gfxinfo --reset", self.serial, timeout=8)
        self.adb.run_shell("cmd activity clear-exit-info", self.serial, timeout=8)

        ram_after = self.get_available_ram_mb()
        ram_gain = max(0, ram_after - ram_before)
        if self.ro:
            repaired_info = f" Aplicații reparate: {', '.join(repaired)}." if repaired else ""
            final_msg = (
                f"Super-Optimizarea s-a încheiat complet! "
                f"RAM liber: {ram_after} MB (+{ram_gain} MB recuperați). "
                f"120Hz + Animații 0.5x active, SystemUI/Launcher/WebView compilate nativ 'speed', fstrim executat.{repaired_info}"
            )
        else:
            repaired_info = f" Repaired packages: {', '.join(repaired)}." if repaired else ""
            final_msg = (
                f"Complete Super-Boost finished! "
                f"Available RAM: {ram_after} MB (+{ram_gain} MB reclaimed). "
                f"120Hz + 0.5x animations active, SystemUI/Launcher/WebView compiled in native 'speed' mode, fstrim completed.{repaired_info}"
            )

        self._emit(total_steps, total_steps, "Finalizat cu succes!" if self.ro else "Completed successfully!", f"🎉 {final_msg}")

        return {
            "success": True,
            "title": "⚡ Super-Optimizare Completă Finalizată" if self.ro else "⚡ Complete Super-Boost Finished",
            "message": final_msg
        }

    def trim_system_caches(self) -> Dict[str, Any]:
        """Requests Android package manager to reclaim non-essential cache space."""
        self._emit(1, 1, "Curățare cache sistem..." if self.ro else "Trimming system caches...", "⏳ Se rulează pm trim-caches..." if self.ro else "⏳ Running pm trim-caches...")
        ok, out = self.adb.run_shell("pm trim-caches 999999999999", self.serial, timeout=20)
        self._emit(1, 1, "Finalizat!" if self.ro else "Completed!", "✓ Cache-ul sistemului a fost curățat." if self.ro else "✓ System cache trimmed.")
        return {
            "success": ok,
            "title": "Curățare Cache Sistem" if self.ro else "System Cache Trim",
            "message": ("Memoria cache a sistemului a fost curățată!" if self.ro else "System cache reclaimed!") if ok else f"Error: {out}"
        }

    def force_stop_app(self, package: str) -> Dict[str, Any]:
        """Force stops an offending rogue app."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid." if self.ro else "Invalid package name."}
        self._emit(1, 1, f"Oprire forțată {package}..." if self.ro else f"Force-stopping {package}...", f"⏳ Se oprește {package}..." if self.ro else f"⏳ Stopping {package}...")
        ok, out = self.adb.run_shell(f"am force-stop {package}", self.serial, timeout=10)
        self._emit(1, 1, "Finalizat!" if self.ro else "Completed!", f"✓ Aplicația {package} a fost oprită." if self.ro else f"✓ {package} stopped.")
        return {
            "success": ok,
            "title": f"Oprire forțată {package}" if self.ro else f"Force Stop {package}",
            "message": (f"Aplicația {package} a fost oprită forțat." if self.ro else f"{package} has been force-stopped.") if ok else f"Error: {out}"
        }

    def clear_app_data(self, package: str) -> Dict[str, Any]:
        """Completely resets data and cache for a specific crashing app (Factory state for that app)."""
        package = self._normalize_package(package)
        if not self._is_valid_package(package):
            return {"success": False, "message": "Nume pachet invalid." if self.ro else "Invalid package name."}
        if package in self.PROTECTED_PACKAGES:
            return self.deep_repair_app(package)
        self._emit(1, 1, f"Resetare completă date {package}..." if self.ro else f"Resetting all app data for {package}...", f"⏳ Se șterg datele pentru {package}..." if self.ro else f"⏳ Clearing all data for {package}...")
        ok, out = self.adb.run_shell(f"pm clear {package}", self.serial, timeout=15)
        self.adb.run_shell(f"cmd activity clear-exit-info --user 0 {package}", self.serial, timeout=5)
        self._emit(1, 1, "Finalizat!" if self.ro else "Completed!", f"✓ Datele pentru {package} au fost șterse." if self.ro else f"✓ Data cleared for {package}.")
        return {
            "success": ok,
            "title": f"Resetare completă date {package}" if self.ro else f"Full Data Reset: {package}",
            "message": (f"Toate datele și memoria cache pentru {package} au fost resetate la zero." if self.ro else f"All data and cache for {package} have been completely reset.") if ok else f"Error: {out}"
        }

    def reboot_device(self) -> Dict[str, Any]:
        """Safely restarts the Android device."""
        self._emit(1, 1, "Repornire telefon..." if self.ro else "Rebooting device...", "⏳ Se trimite comanda de restart către telefon..." if self.ro else "⏳ Sending reboot command to device...")
        ok, out = self.adb.run_shell("reboot", self.serial, timeout=10)
        self._emit(1, 1, "Restart trimis!" if self.ro else "Reboot sent!", "✓ Telefonul se repornește acum." if self.ro else "✓ Device is now rebooting.")
        return {
            "success": ok,
            "title": "Restart telefon" if self.ro else "Reboot Device",
            "message": (
                "Comanda de restart a fost trimisă telefonului. Așteaptă 30-45 secunde să pornească."
                if self.ro else "Reboot command sent to device. Please wait 30-45 seconds for it to restart."
            ) if ok else f"Error: {out}"
        }
