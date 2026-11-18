import re
import datetime
from typing import Dict, Any, List, Optional
from adb_manager import AdbManager

class PhoneDiagnostics:
    """Performs deep health, UI jank/stutter, and freeze diagnostics on any connected Android device (EN primary / RO supported)."""

    PROCESS_TO_PACKAGE_MAP = {
        "android.process.acore": "com.android.providers.contacts",
        "android.process.media": "com.android.providers.media.module",
        "com.google.process.gservices": "com.google.android.gsf",
        "com.google.process.gapps": "com.google.android.gms",
    }

    SYSTEM_PROVIDER_LABELS_EN = {
        "com.android.providers.contacts": "Contacts & Call Log Database (acore)",
        "com.android.providers.media.module": "MediaStore & File Indexer",
        "com.android.providers.media": "MediaStore Indexer",
        "com.android.providers.downloads": "Downloads Provider",
        "com.android.providers.calendar": "Calendar Storage Provider",
        "com.google.android.gsf": "Google Services Framework (Sync)",
        "com.google.android.gms": "Google Play Services",
    }

    SYSTEM_PROVIDER_LABELS_RO = {
        "com.android.providers.contacts": "Baza de date Contacte & Apeluri (acore)",
        "com.android.providers.media.module": "Indexul Media & Fișiere (MediaStore)",
        "com.android.providers.media": "Indexul Media (MediaStore)",
        "com.android.providers.downloads": "Managerul de Descărcări (Downloads)",
        "com.android.providers.calendar": "Baza de date Calendar",
        "com.google.android.gsf": "Google Services Framework (Sincronizare)",
        "com.google.android.gms": "Google Play Services",
    }

    KNOWN_BLOATWARE = {
        # Philips & Android TV bloatware
        "org.droidtv.demome": {"en": "Philips Retail Store Demo Mode", "ro": "Mod Demo Magazin Philips (Retail Demo)"},
        "org.droidtv.sticker": {"en": "Philips Retail E-Sticker Overlay", "ro": "Overlay Reclame Magazin (E-Sticker)"},
        "org.droidtv.esticker": {"en": "Philips E-Sticker Demo Service", "ro": "Serviciu Demo E-Sticker Philips"},
        "org.droidtv.candeebug": {"en": "Philips Internal Debug Logger", "ro": "Serviciu Intern Debugging Philips (50MB RAM)"},
        "org.droidtv.usagelogger": {"en": "Philips Usage Telemetry Logger", "ro": "Telemetrie Utilizare Philips"},
        "org.droidtv.tv.frameworklogger": {"en": "Philips Framework Debug Logger", "ro": "Jurnal Intern Framework Philips"},
        "org.droidtv.dropboxprovider": {"en": "Philips Crash Log Uploader", "ro": "Serviciu Trimitere Jurnale Eroare Philips"},
        "org.droidtv.nettvbrowser": {"en": "Legacy Philips NetTV Browser", "ro": "Browser Vechi Philips NetTV (Consumă RAM în fundal)"},
        "org.droidtv.nettv.market": {"en": "Legacy Philips App Gallery Store", "ro": "Magazin Vechi Philips App Gallery"},
        "org.droidtv.nettvrecommender": {"en": "Philips NetTV Ad Recommender", "ro": "Recomandări & Reclame Philips NetTV"},
        "org.droidtv.recommendation": {"en": "Philips Banner Recommendations", "ro": "Serviciu Recomandări Philips"},
        "org.droidtv.eum": {"en": "Electronic User Manual (Background)", "ro": "Manual Electronic în Fundal (40MB RAM)"},
        "com.vewd.core.browserui": {"en": "Vewd Legacy TV Browser Engine", "ro": "Motor Browser Vechi Vewd TV"},
        "com.phorus.playfi.tv": {"en": "DTS Play-Fi Multiroom Daemon", "ro": "Serviciu Audio Multiroom DTS Play-Fi"},
        "com.phorus.playfi.softap": {"en": "DTS Play-Fi Wi-Fi Hotspot Daemon", "ro": "Serviciu Hotspot DTS Play-Fi"},
        "org.droidtv.amazonalexa": {"en": "Philips Amazon Alexa Background Agent", "ro": "Serviciu Amazon Alexa în Fundal"},
        "tv.samba.ssm": {"en": "Samba TV ACR Tracking & Telemetry", "ro": "Telemetrie & Urmărire Ecran Samba TV"},
        # Phone OEM & general bloatware
        "com.facebook.services": {"en": "Meta/Facebook Background Services", "ro": "Servicii Meta/Facebook Preinstalate în Fundal"},
        "com.facebook.system": {"en": "Meta App Installer Daemon", "ro": "Instalator Sistem Meta/Facebook"},
        "com.facebook.appmanager": {"en": "Meta App Manager Background Service", "ro": "Manager Aplicații Meta în Fundal"},
        "com.samsung.android.bixby.agent": {"en": "Samsung Bixby Voice Assistant", "ro": "Asistent Vocal Samsung Bixby"},
        "com.samsung.android.app.spage": {"en": "Samsung Free / Daily Feed", "ro": "Samsung Free / Știri pe Ecran"},
        "com.samsung.android.game.gos": {"en": "Samsung Game Optimizing Service (Throttler)", "ro": "Samsung Game Optimizing Service (Limitator)"},
        "com.miui.msa.global": {"en": "MIUI System Ads (MSA)", "ro": "Serviciu Reclame în Sistem Xiaomi (MSA)"},
        "com.miui.analytics": {"en": "Xiaomi Analytics & Telemetry", "ro": "Telemetrie & Analiză Xiaomi"},
        "com.google.android.printservice.recommendation": {"en": "Print Service Recommendation Scanner", "ro": "Scaner Permanent Imprimante în Fundal"},
        "com.google.android.feedback": {"en": "Google Crash & Feedback Reporter", "ro": "Raportare Erori & Telemetrie Feedback"},
    }

    def __init__(self, adb: AdbManager, serial: Optional[str] = None, lang: str = "en"):
        self.adb = adb
        self.serial = serial
        self.lang = lang if lang in ("en", "ro") else "en"
        self.ro = (self.lang == "ro")

    def run_full_scan(self) -> Dict[str, Any]:
        """Runs the complete diagnostic suite and aggregates findings."""
        device_info = self.get_device_info()
        storage = self.get_storage_info()
        storage_breakdown = self.get_storage_breakdown()
        memory = self.get_memory_info()
        anrs_crashes = self.get_anr_and_crash_logs()
        thermals_cpu = self.get_thermal_and_cpu_info(device_info.get("soc", "SoC"), is_tv=device_info.get("is_tv", False))
        battery = self.get_battery_info()
        ui_fluency = self.get_ui_fluency_and_jank()
        system_pressure = self.get_psi_and_accessibility()
        bloatware = self.get_bloatware_scan()
        battery_drain = self.get_wakelocks_and_battery_drain()
        security_audit = self.get_security_and_privacy_audit()

        system_health = self.calculate_health_score(
            storage, memory, anrs_crashes, thermals_cpu, battery, device_info, ui_fluency, system_pressure
        )

        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lang": self.lang,
            "device": device_info,
            "storage": storage,
            "storage_breakdown": storage_breakdown,
            "memory": memory,
            "anrs_and_crashes": anrs_crashes,
            "thermals_and_cpu": thermals_cpu,
            "battery": battery,
            "ui_fluency": ui_fluency,
            "system_pressure": system_pressure,
            "bloatware": bloatware,
            "battery_drain": battery_drain,
            "security_audit": security_audit,
            "health_evaluation": system_health
        }

    def get_bloatware_scan(self) -> Dict[str, Any]:
        """Detects active bloatware that can be safely uninstalled (rootless) and previously removed bloatware that can be restored."""
        ok_act, out_act = self.adb.run_shell("pm list packages", self.serial, timeout=8)
        ok_all, out_all = self.adb.run_shell("pm list packages -u", self.serial, timeout=8)

        active_set = set()
        if ok_act and out_act:
            for line in out_act.splitlines():
                if line.startswith("package:"):
                    active_set.add(line.replace("package:", "").strip())

        all_set = set(active_set)
        if ok_all and out_all:
            for line in out_all.splitlines():
                if line.startswith("package:"):
                    all_set.add(line.replace("package:", "").strip())

        active_bloat = []
        removed_bloat = []
        for pkg, labels in self.KNOWN_BLOATWARE.items():
            desc = labels["ro"] if self.ro else labels["en"]
            if pkg in active_set:
                active_bloat.append({"package": pkg, "description": desc, "state": "active"})
            elif pkg in all_set:
                removed_bloat.append({"package": pkg, "description": desc, "state": "removed"})

        return {
            "active_count": len(active_bloat),
            "removed_count": len(removed_bloat),
            "active_bloatware": active_bloat,
            "removed_bloatware": removed_bloat
        }

    def get_wakelocks_and_battery_drain(self) -> Dict[str, Any]:
        """Detects active CPU WakeLocks keeping the device awake and checks Deep Doze status."""
        wakelocks = []
        seen_wl = set()
        ok_pw, out_pw = self.adb.run_shell("dumpsys power | grep -E 'PARTIAL_WAKE_LOCK|Wake Locks: size'", self.serial, timeout=6)
        if ok_pw and out_pw:
            for line in out_pw.splitlines():
                line = line.strip()
                if "PARTIAL_WAKE_LOCK" in line:
                    tag_m = re.search(r"PARTIAL_WAKE_LOCK\s+'([^']+)'", line)
                    uid_m = re.search(r"uid=(\d+)", line)
                    tag = tag_m.group(1) if tag_m else "WakeLock"
                    key = f"{tag}_{uid_m.group(1) if uid_m else ''}"
                    if key not in seen_wl:
                        seen_wl.add(key)
                        wakelocks.append({"tag": tag, "raw": line[:120]})

        doze_enabled = True
        ok_dz, out_dz = self.adb.run_shell("dumpsys deviceidle enabled", self.serial, timeout=5)
        if ok_dz and out_dz and out_dz.strip() == "0":
            doze_enabled = False

        return {
            "active_wakelocks_count": len(wakelocks),
            "wakelocks": wakelocks[:10],
            "deep_doze_enabled": doze_enabled
        }

    def get_storage_breakdown(self) -> Dict[str, Any]:
        """Scans /sdcard top folders, leftover .apk installers in Download, and thumbnail cache size."""
        folders = []
        ok_du, out_du = self.adb.run_shell("du -m -d 1 /sdcard 2>/dev/null | sort -rn | head -n 10", self.serial, timeout=10)
        if ok_du and out_du:
            for line in out_du.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) == 2 and parts[0].isdigit():
                    size_mb = int(parts[0])
                    path = parts[1].strip()
                    if path != "/sdcard" and size_mb >= 5:
                        folders.append({"path": path, "size_mb": size_mb})

        apk_files = []
        ok_apk, out_apk = self.adb.run_shell("find /sdcard/Download -maxdepth 2 -name '*.apk' 2>/dev/null", self.serial, timeout=6)
        if ok_apk and out_apk:
            for line in out_apk.splitlines():
                line = line.strip()
                if line.endswith(".apk"):
                    apk_files.append(line)

        thumb_mb = 0
        ok_th, out_th = self.adb.run_shell("du -sm /sdcard/DCIM/.thumbnails 2>/dev/null", self.serial, timeout=5)
        if ok_th and out_th:
            parts = out_th.strip().split()
            if parts and parts[0].isdigit():
                thumb_mb = int(parts[0])

        return {
            "top_folders": folders[:8],
            "leftover_apks_count": len(apk_files),
            "leftover_apks": apk_files[:10],
            "thumbnails_cache_mb": thumb_mb
        }

    def get_security_and_privacy_audit(self) -> Dict[str, Any]:
        """Audits Private DNS (AdGuard AdBlock status) and sideloaded third-party packages."""
        ok_mode, mode_out = self.adb.run_shell("settings get global private_dns_mode", self.serial, timeout=5)
        ok_host, host_out = self.adb.run_shell("settings get global private_dns_specifier", self.serial, timeout=5)
        dns_mode = (mode_out or "").strip()
        dns_host = (host_out or "").strip()
        if dns_host == "null":
            dns_host = ""

        adguard_active = (dns_mode == "hostname" and "adguard" in dns_host.lower())

        sideloaded_apps = []
        trusted_installers = {
            "com.android.vending",
            "com.google.android.packageinstaller",
            "com.android.packageinstaller",
            "com.sec.android.app.samsungapps",
            "com.xiaomi.mipicks",
            "org.droidtv.nettv.market",
        }
        ok_inst, out_inst = self.adb.run_shell("pm list packages -3 -i", self.serial, timeout=8)
        if ok_inst and out_inst:
            for line in out_inst.splitlines():
                m = re.search(r"package:([^\s]+)\s+installer=([^\s]+)", line.strip())
                if m:
                    pkg, installer = m.group(1), m.group(2)
                    if installer not in trusted_installers:
                        sideloaded_apps.append({
                            "package": pkg,
                            "installer": ("Necunoscut / APK Manual" if self.ro else "Unknown / Manual Sideload") if installer == "null" else installer
                        })

        return {
            "private_dns_mode": dns_mode,
            "private_dns_host": dns_host,
            "adguard_active": adguard_active,
            "sideloaded_count": len(sideloaded_apps),
            "sideloaded_apps": sideloaded_apps[:15]
        }

    def get_device_info(self) -> Dict[str, Any]:
        """Gathers core model, brand, SoC chipset, OS version, security patch, and uptime."""
        def get_prop(prop_name: str, fallback: str = "") -> str:
            ok, out = self.adb.run_shell(f"getprop {prop_name}", self.serial, timeout=5)
            val = out.strip() if ok and out else ""
            return val if val else fallback

        model = get_prop("ro.product.model", "Dispozitiv Android" if self.ro else "Android Device")
        brand = get_prop("ro.product.brand", "Android").capitalize()
        device_codename = get_prop("ro.product.device", "generic")
        android_ver = get_prop("ro.build.version.release", "N/A")
        sdk_ver = get_prop("ro.build.version.sdk", "N/A")
        security_patch = get_prop("ro.build.version.security_patch", "N/A")
        build_id = get_prop("ro.build.id", "N/A")
        soc_model = get_prop("ro.soc.model") or get_prop("ro.board.platform") or get_prop("ro.hardware") or "ARM64 SoC"
        characteristics = get_prop("ro.build.characteristics", "")
        is_tv = "tv" in characteristics.lower()

        uptime_str = "Necunoscut" if self.ro else "Unknown"
        uptime_days = 0.0
        ok, uptime_out = self.adb.run_shell("cat /proc/uptime", self.serial, timeout=5)
        if ok and uptime_out:
            try:
                seconds = float(uptime_out.split()[0])
                uptime_days = round(seconds / 86400, 1)
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                day_unit = "z" if self.ro else "d"
                uptime_str = f"{hours // 24}{day_unit} {hours % 24}h {minutes}m"
            except Exception:
                pass

        return {
            "model": model,
            "brand": brand,
            "codename": device_codename,
            "soc": soc_model,
            "is_tv": is_tv,
            "android_version": android_ver,
            "sdk_version": sdk_ver,
            "security_patch": security_patch,
            "build_id": build_id,
            "uptime_str": uptime_str,
            "uptime_days": uptime_days,
            "needs_reboot": uptime_days >= 7.0
        }

    def get_storage_info(self) -> Dict[str, Any]:
        """Analyzes internal storage usage and warning thresholds."""
        ok, out = self.adb.run_shell("df -k /data", self.serial)
        total_gb = 0.0
        used_gb = 0.0
        free_gb = 0.0
        percent_used = 0

        if ok and out:
            lines = out.strip().splitlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        total_k = int(parts[1])
                        used_k = int(parts[2])
                        free_k = int(parts[3])
                        total_gb = round(total_k / (1024 * 1024), 1)
                        used_gb = round(used_k / (1024 * 1024), 1)
                        free_gb = round(free_k / (1024 * 1024), 1)
                        if total_gb > 0:
                            percent_used = round((used_gb / total_gb) * 100)
                        break
                    except Exception:
                        pass

        status = "normal"
        # Small storage partitions (<= 16 GB, e.g. Android TV) use percentage thresholds
        if total_gb <= 16.0:
            if percent_used >= 90 or (free_gb > 0 and free_gb < 0.6):
                status = "critical"
            elif percent_used >= 80 or (free_gb > 0 and free_gb < 1.2):
                status = "warning"
        else:
            if percent_used >= 90 or (free_gb > 0 and free_gb < 8.0):
                status = "critical"
            elif percent_used >= 80 or (free_gb > 0 and free_gb < 15.0):
                status = "warning"

        summary = (
            f"{used_gb} GB folosiți din {total_gb} GB ({percent_used}% • {free_gb} GB liberi)"
            if self.ro else
            f"{used_gb} GB used of {total_gb} GB ({percent_used}% • {free_gb} GB free)"
        )

        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "percent_used": percent_used,
            "status": status,
            "summary": summary
        }

    def get_memory_info(self) -> Dict[str, Any]:
        """Checks RAM usage, ZRAM swap pressure, and top memory-heavy apps."""
        ok, out = self.adb.run_shell("cat /proc/meminfo", self.serial)
        mem_data = {}
        if ok and out:
            for line in out.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    val_clean = val.strip().replace("kB", "").strip()
                    try:
                        mem_data[key.strip()] = int(val_clean)
                    except ValueError:
                        pass

        total_mb = round(mem_data.get("MemTotal", 0) / 1024)
        available_mb = round(mem_data.get("MemAvailable", 0) / 1024)
        free_mb = round(mem_data.get("MemFree", 0) / 1024)
        swap_total_mb = round(mem_data.get("SwapTotal", 0) / 1024)
        swap_free_mb = round(mem_data.get("SwapFree", 0) / 1024)
        swap_used_mb = swap_total_mb - swap_free_mb

        used_mb = total_mb - available_mb if total_mb > available_mb else 0
        ram_percent_used = round((used_mb / total_mb) * 100) if total_mb > 0 else 0
        swap_percent_used = round((swap_used_mb / swap_total_mb) * 100) if swap_total_mb > 0 else 0

        status = "normal"
        low_ram_threshold = 380 if total_mb <= 2500 else 900
        if ram_percent_used >= 88 or swap_percent_used >= 85 or (available_mb > 0 and available_mb < low_ram_threshold):
            status = "critical"
        elif ram_percent_used >= 78 or swap_percent_used >= 60:
            status = "warning"

        top_apps = []
        seen_pkgs = set()
        # Use fast `ps -A -o RSS,ARGS` first (instant even on low-RAM Android TVs where dumpsys meminfo times out)
        ok_ps, ps_out = self.adb.run_shell("ps -A -o RSS,ARGS", self.serial, timeout=6)
        if ok_ps and ps_out:
            min_mb = 35 if total_mb <= 2500 else 90
            for line in ps_out.splitlines()[1:]:
                parts = line.strip().split(None, 1)
                if len(parts) == 2 and parts[0].isdigit():
                    rss_kb = int(parts[0])
                    cmd = parts[1].strip().split()[0]
                    pkg = cmd.split(":")[0].strip()
                    if "." in pkg and not pkg.startswith("/") and pkg not in seen_pkgs:
                        mb = round(rss_kb / 1024, 1)
                        if mb >= min_mb:
                            seen_pkgs.add(pkg)
                            top_apps.append({"package": pkg, "memory_mb": mb})

        if not top_apps:
            ok_dumpsys, mem_dumpsys = self.adb.run_shell("dumpsys meminfo | head -n 45", self.serial, timeout=12)
            if ok_dumpsys and mem_dumpsys:
                for line in mem_dumpsys.splitlines():
                    line = line.strip()
                    match = re.search(r"([\d,]+)K:\s+([a-zA-Z0-9_\.]+)\s*(?:\(pid|\()?", line)
                    if match:
                        kb_str = match.group(1).replace(",", "").replace(".", "")
                        pkg = match.group(2)
                        if pkg in seen_pkgs or "." not in pkg:
                            continue
                        try:
                            mb = round(int(kb_str) / 1024, 1)
                            if mb > 50:
                                seen_pkgs.add(pkg)
                                top_apps.append({"package": pkg, "memory_mb": mb})
                        except Exception:
                            pass

        top_apps.sort(key=lambda x: x["memory_mb"], reverse=True)

        return {
            "total_mb": total_mb,
            "used_mb": used_mb,
            "available_mb": available_mb,
            "free_mb": free_mb,
            "ram_percent_used": ram_percent_used,
            "swap_total_mb": swap_total_mb,
            "swap_used_mb": swap_used_mb,
            "swap_percent_used": swap_percent_used,
            "status": status,
            "top_apps": top_apps[:10]
        }

    def get_ui_fluency_and_jank(self) -> Dict[str, Any]:
        """Analyzes refresh rate, animation scales, and GPU frame drops (jank)."""
        def get_setting(namespace: str, key: str, default: str = "") -> str:
            ok, out = self.adb.run_shell(f"settings get {namespace} {key}", self.serial, timeout=5)
            val = out.strip() if ok and out else ""
            return default if (not val or val == "null") else val

        win_anim = get_setting("global", "window_animation_scale", "1.0")
        trans_anim = get_setting("global", "transition_animation_scale", "1.0")
        dur_anim = get_setting("global", "animator_duration_scale", "1.0")
        peak_rr = (
            get_setting("system", "peak_refresh_rate", "")
            or get_setting("secure", "refresh_rate_mode", "")
            or "120.0"
        )
        min_rr = get_setting("system", "min_refresh_rate", "60.0")

        try:
            anim_scale_val = float(win_anim)
            if anim_scale_val != anim_scale_val or anim_scale_val > 10.0:
                anim_scale_val = 1.0
        except Exception:
            anim_scale_val = 1.0

        try:
            peak_rr_val = float(peak_rr)
            if peak_rr_val != peak_rr_val or peak_rr_val > 240.0 or peak_rr_val <= 10.0:
                peak_rr_val = 120.0
        except Exception:
            peak_rr_val = 120.0

        smooth_display_enabled = peak_rr_val >= 90.0

        janky_apps = []
        total_frames_all = 0
        total_jank_all = 0

        ok_gfx, gfx_out = self.adb.run_shell("dumpsys gfxinfo", self.serial, timeout=18)
        if ok_gfx and gfx_out:
            sections = re.split(r"\*\*\s*Graphics info for pid \d+ \[([^\]]+)\]\s*\*\*", gfx_out)
            seen_gfx_pkgs = {}
            for i in range(1, len(sections) - 1, 2):
                pkg = sections[i].strip()
                body = sections[i + 1]
                t_match = re.search(r"Total frames rendered:\s*(\d+)", body)
                j_match = re.search(r"Janky frames:\s*(\d+)\s*\(([\d\.]+)%\)", body)
                p95_match = re.search(r"95th percentile:\s*(\d+)ms", body)
                p99_match = re.search(r"99th percentile:\s*(\d+)ms", body)

                if t_match and j_match:
                    total_f = int(t_match.group(1))
                    jank_f = int(j_match.group(1))
                    jank_pct = float(j_match.group(2))
                    p95 = int(p95_match.group(1)) if p95_match else 0
                    p99 = int(p99_match.group(1)) if p99_match else 0

                    if total_f >= 20:
                        total_frames_all += total_f
                        total_jank_all += jank_f
                        if pkg not in seen_gfx_pkgs or jank_pct > seen_gfx_pkgs[pkg]["jank_percent"]:
                            seen_gfx_pkgs[pkg] = {
                                "package": pkg,
                                "total_frames": total_f,
                                "janky_frames": jank_f,
                                "jank_percent": round(jank_pct, 1),
                                "p95_ms": p95,
                                "p99_ms": p99
                            }

            janky_apps = sorted(seen_gfx_pkgs.values(), key=lambda x: (x["jank_percent"], x["janky_frames"]), reverse=True)

        global_jank_percent = round((total_jank_all / total_frames_all) * 100, 1) if total_frames_all > 0 else 0.0

        status = "normal"
        if global_jank_percent >= 12.0 or not smooth_display_enabled or any(a["jank_percent"] >= 25.0 for a in janky_apps[:3]):
            status = "critical" if global_jank_percent >= 20.0 else "warning"

        return {
            "window_animation_scale": anim_scale_val,
            "transition_animation_scale": trans_anim,
            "animator_duration_scale": dur_anim,
            "peak_refresh_rate": round(peak_rr_val),
            "min_refresh_rate": min_rr,
            "smooth_display_enabled": smooth_display_enabled,
            "global_jank_percent": global_jank_percent,
            "total_frames_sampled": total_frames_all,
            "janky_apps": janky_apps[:8],
            "status": status
        }

    def get_psi_and_accessibility(self) -> Dict[str, Any]:
        """Checks Accessibility hooks, I/O & Memory stall pressure, and Battery Saver."""
        accessibility_services = []
        ok_acc, acc_out = self.adb.run_shell("settings get secure enabled_accessibility_services", self.serial, timeout=5)
        if ok_acc and acc_out:
            val = acc_out.strip()
            if val and val != "null":
                for item in val.split(":"):
                    item = item.strip()
                    if item:
                        pkg = item.split("/")[0]
                        accessibility_services.append({"service": item, "package": pkg})

        io_stall_avg10 = 0.0
        mem_stall_avg10 = 0.0
        cpu_stall_avg10 = 0.0

        ok_psi, psi_out = self.adb.run_shell(
            "cat /proc/pressure/io /proc/pressure/memory /proc/pressure/cpu 2>/dev/null",
            self.serial,
            timeout=5
        )
        if ok_psi and psi_out:
            some_matches = re.findall(r"some avg10=([\d\.]+)", psi_out)
            if len(some_matches) >= 1:
                io_stall_avg10 = float(some_matches[0])
            if len(some_matches) >= 2:
                mem_stall_avg10 = float(some_matches[1])
            if len(some_matches) >= 3:
                cpu_stall_avg10 = float(some_matches[2])

        power_save_active = False
        ok_ps, ps_out = self.adb.run_shell("settings get global low_power", self.serial, timeout=5)
        if ok_ps and ps_out.strip() == "1":
            power_save_active = True

        return {
            "accessibility_services": accessibility_services,
            "has_accessibility_hooks": len(accessibility_services) > 0,
            "io_stall_percent": io_stall_avg10,
            "mem_stall_percent": mem_stall_avg10,
            "cpu_stall_percent": cpu_stall_avg10,
            "power_save_active": power_save_active
        }

    def get_anr_and_crash_logs(self) -> Dict[str, Any]:
        """Deep search for recent Application Not Responding (ANR) events and real crashes (last 24h)."""
        anr_events = []
        crash_events = []
        app_problem_counts = {}

        now_dt = datetime.datetime.now()
        ok_date, date_out = self.adb.run_shell("date '+%Y-%m-%d %H:%M:%S'", self.serial, timeout=5)
        if ok_date and date_out:
            try:
                now_dt = datetime.datetime.strptime(date_out.strip(), "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        cutoff_dt = now_dt - datetime.timedelta(hours=24)

        ok_exit, exit_out = self.adb.run_shell("dumpsys activity exit-info", self.serial, timeout=15)
        if ok_exit and exit_out:
            blocks = exit_out.split("ApplicationExitInfo #")
            for block in blocks[1:]:
                reason_match = re.search(r"reason=(\d+)\s*\(([^)]+)\)", block)
                pkg_match = re.search(r"package=([^\s]+)", block)
                proc_match = re.search(r"process=([^\s]+)", block)
                ts_match = re.search(r"timestamp=(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", block)
                subreason_match = re.search(r"subreason=\d+\s*\(([^)]+)\)|subreason=([^\s\n]+)", block)
                desc_match = re.search(r"description=([^\n]+)", block)

                date_str = "Recent"
                if ts_match:
                    date_str = ts_match.group(1).strip()
                    try:
                        ev_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        if ev_dt < cutoff_dt:
                            continue
                    except Exception:
                        pass

                if reason_match and (pkg_match or proc_match):
                    reason_name = reason_match.group(2).strip()
                    if "LOW_MEMORY" in reason_name:
                        continue

                    raw_pkg = (pkg_match.group(1) if pkg_match else proc_match.group(1)).strip()
                    package = raw_pkg.split(":")[0].strip()
                    package = self.PROCESS_TO_PACKAGE_MAP.get(package, package)
                    if package in ("system", "android") or "." not in package or len(package) < 6:
                        continue

                    subreason = ""
                    if subreason_match:
                        subreason = (subreason_match.group(1) or subreason_match.group(2) or "").strip()

                    description = desc_match.group(1).strip() if desc_match else ""
                    if description == "null":
                        description = ""

                    if "ANR" in reason_name or "FREEZER" in reason_name or "EXCESSIVE_RESOURCE" in reason_name:
                        app_problem_counts[package] = app_problem_counts.get(package, 0) + 1
                        anr_label = ("ANR (Înghețare)" if self.ro else "ANR (Freeze)") if "ANR" in reason_name else reason_name
                        default_detail = (
                            "Firul principal UI blocat (Input dispatch timed out)"
                            if self.ro else "Main UI thread blocked (Input dispatch timed out)"
                        )
                        anr_events.append({
                            "package": package,
                            "type": anr_label,
                            "date": date_str,
                            "details": description or subreason or default_detail
                        })
                    elif "CRASH" in reason_name or "INITIALIZATION_FAILURE" in reason_name:
                        app_problem_counts[package] = app_problem_counts.get(package, 0) + 1
                        crash_events.append({
                            "package": package,
                            "type": reason_name,
                            "date": date_str,
                            "details": description or subreason or ("Eroare internă aplicație" if self.ro else "Application crash")
                        })

        sorted_culprits = sorted(app_problem_counts.items(), key=lambda x: x[1], reverse=True)
        top_culprits = [{"package": k, "count": v} for k, v in sorted_culprits]

        total_anrs = len(anr_events)
        total_crashes = len(crash_events)

        status = "normal"
        if total_anrs >= 4 or total_crashes >= 8:
            status = "critical"
        elif total_anrs >= 1 or total_crashes >= 2:
            status = "warning"

        combined_events = anr_events[:12] + [c for c in crash_events if "CRASH" in c["type"]][:8]

        return {
            "total_anrs": total_anrs,
            "total_crashes": total_crashes,
            "status": status,
            "top_culprits": top_culprits,
            "recent_anrs": combined_events[:16],
            "recent_crashes": crash_events[:10]
        }

    def get_thermal_and_cpu_info(self, soc_name: str = "SoC", is_tv: bool = False) -> Dict[str, Any]:
        """Monitors battery/board temperature, thermal throttling status, and top CPU processes."""
        battery_temp_c = 0.0
        ok_bat, bat_out = self.adb.run_shell("dumpsys battery", self.serial)
        if ok_bat and bat_out:
            match = re.search(r"temperature:\s*(\d+)", bat_out)
            if match:
                raw_temp = int(match.group(1))
                battery_temp_c = round(raw_temp / 10.0, 1)

        thermal_headroom_status = 0
        ok_th, th_out = self.adb.run_shell("dumpsys thermalservice | grep -i 'Current Status'", self.serial, timeout=6)
        if ok_th and th_out:
            m_th = re.search(r"(\d+)", th_out)
            if m_th:
                thermal_headroom_status = int(m_th.group(1))

        thermal_status = "Răcoros / Fără limitări" if self.ro else "Cool / No Throttling"
        thermal_severity = "normal"
        warn_temp = 60.0 if is_tv else 38.0
        crit_temp = 72.0 if is_tv else 41.5
        if battery_temp_c >= crit_temp or thermal_headroom_status >= 3:
            thermal_status = "Throttling Sever Activ (Procesor limitat termic!)" if self.ro else "Severe Thermal Throttling Active!"
            thermal_severity = "critical"
        elif battery_temp_c >= warn_temp or thermal_headroom_status >= 1:
            thermal_status = f"Cald (Limitare parțială {soc_name})" if self.ro else f"Warm (Light {soc_name} Throttling)"
            thermal_severity = "warning"

        top_cpu = []
        ok_cpu, cpu_out = self.adb.run_shell("dumpsys cpuinfo | head -n 30", self.serial, timeout=10)
        if ok_cpu and cpu_out:
            for line in cpu_out.splitlines():
                line = line.strip()
                match = re.search(r"(\d+(?:\.\d+)?)%\s+\d+/([a-zA-Z0-9_\.]+):", line)
                if match:
                    percent = float(match.group(1))
                    pkg = match.group(2)
                    if percent > 1.5 and "." in pkg:
                        top_cpu.append({"package": pkg, "cpu_percent": percent})

        top_cpu.sort(key=lambda x: x["cpu_percent"], reverse=True)

        return {
            "battery_temp_c": battery_temp_c,
            "thermal_throttling_level": thermal_headroom_status,
            "thermal_status": thermal_status,
            "thermal_severity": thermal_severity,
            "top_cpu_apps": top_cpu[:8]
        }

    def get_battery_info(self) -> Dict[str, Any]:
        """Gets battery health and charge cycle count."""
        level = 0
        health = "Bună" if self.ro else "Good"
        cycles = "N/A"

        ok_bat, bat_out = self.adb.run_shell("dumpsys battery", self.serial)
        if ok_bat and bat_out:
            lvl_match = re.search(r"level:\s*(\d+)", bat_out)
            if lvl_match:
                level = int(lvl_match.group(1))
            health_match = re.search(r"health:\s*(\d+)", bat_out)
            if health_match:
                h_val = int(health_match.group(1))
                if self.ro:
                    health_map = {1: "Necunoscută", 2: "Bună (Optim)", 3: "Supraîncălzire", 4: "Uzată / Defectă", 5: "Supratensiune"}
                    health = health_map.get(h_val, "Normală")
                else:
                    health_map = {1: "Unknown", 2: "Good (Optimal)", 3: "Overheat", 4: "Dead / Degraded", 5: "Overvoltage"}
                    health = health_map.get(h_val, "Normal")

        ok_cyc, cyc_out = self.adb.run_shell("cat /sys/class/power_supply/battery/cycle_count", self.serial)
        if ok_cyc and cyc_out and cyc_out.strip().isdigit():
            cycles = int(cyc_out.strip())
        else:
            m = re.search(r"mCycleCount:\s*(\d+)", bat_out if ok_bat else "")
            if m:
                cycles = int(m.group(1))

        return {
            "level": level,
            "health": health,
            "cycles": cycles
        }

    def calculate_health_score(
        self,
        storage: Dict,
        memory: Dict,
        anrs: Dict,
        thermals: Dict,
        battery: Dict,
        device: Dict,
        ui_fluency: Dict,
        system_pressure: Dict
    ) -> Dict[str, Any]:
        """Calculates global score (0-100) and generates actionable recommendations with direct buttons."""
        score = 100
        issues = []
        recommendations = []
        provider_map = self.SYSTEM_PROVIDER_LABELS_RO if self.ro else self.SYSTEM_PROVIDER_LABELS_EN

        # 0. Master 1-Click Deep Fix Recommendation
        recommendations.append({
            "severity": "urgent",
            "title": (
                "⚡ Super-Optimizare Completă (Anti-Sacadare & Deblocare Aplicații)"
                if self.ro else "⚡ Complete 1-Click Super Boost (Anti-Stutter & App Unfreeze)"
            ),
            "description": (
                "Rulează automat protocolul complet de reparație: curăță cache-ul corupt din SystemUI, Launcher și Android WebView, eliberează memoria RAM/ZRAM, setează animațiile la 0.5x (instant), activează rata de refresh maximă, optimizează stocarea flash (fstrim) și recompilează nativ (în mod 'speed') toate aplicațiile cu blocaje."
                if self.ro else
                "Automatically runs the full repair protocol: clears corrupted caches in SystemUI, Launcher, and Android WebView, frees RAM/ZRAM, sets snappy 0.5x animations, enables peak refresh rate, runs UFS flash TRIM (fstrim), and AOT-compiles ('speed' mode) all freezing apps."
            ),
            "action_type": "deep_boost_all"
        })

        # 1. UI Fluency / Stutter Check
        jank_pct = ui_fluency.get("global_jank_percent", 0.0)
        janky_apps = ui_fluency.get("janky_apps", [])
        smooth_on = ui_fluency.get("smooth_display_enabled", True)
        anim_scale = ui_fluency.get("window_animation_scale", 1.0)

        if jank_pct >= 10.0 or not smooth_on:
            score -= 15
            if not smooth_on:
                issues.append(
                    f"Ecranul rulează la doar {ui_fluency.get('peak_refresh_rate', 60)}Hz (rata de refresh înaltă 90/120Hz este oprită)"
                    if self.ro else
                    f"Display is capped at {ui_fluency.get('peak_refresh_rate', 60)}Hz (high 90/120Hz refresh rate is disabled)"
                )
            if jank_pct >= 10.0:
                worst_jank = ", ".join([f"{a['package']} ({a['jank_percent']}%)" for a in janky_apps[:3]])
                issues.append(
                    f"Pierderi ridicate de cadre UI (Frame Drops / Sacadare: {jank_pct}% global) în: {worst_jank}"
                    if self.ro else
                    f"High GPU UI frame drops (Global Jank: {jank_pct}%) in: {worst_jank}"
                )

        if anim_scale >= 1.0 or not smooth_on or jank_pct >= 8.0:
            recommendations.append({
                "severity": "urgent" if (jank_pct >= 15.0 or not smooth_on) else "recomandat",
                "title": (
                    "Eliminare Mișcare Sacadată (Boost 120Hz + Animații 0.5x + Optimizare Launcher/WebView)"
                    if self.ro else
                    "Fix UI Stutter & Frame Drops (120Hz Boost + 0.5x Animations + Launcher/WebView Speed)"
                ),
                "description": (
                    f"Rata de cadre pierdute (jank) este {jank_pct}%, iar scara animațiilor este {anim_scale}x. Această acțiune activează rata maximă de refresh, scurtează animațiile la 0.5x pentru răspuns instant și recompilează Launcher-ul telefonului, SystemUI și Android System WebView."
                    if self.ro else
                    f"Global frame jank is {jank_pct}% and animation scale is {anim_scale}x. This action enables peak refresh rate, sets snappy 0.5x animations, and AOT-compiles the device's Home Launcher, SystemUI, and Android System WebView."
                ),
                "action_type": "fix_ui_stutter"
            })

        # 2. Accessibility Services Check
        acc_services = system_pressure.get("accessibility_services", [])
        if acc_services:
            score -= 12
            acc_names = ", ".join([a["package"] for a in acc_services])
            issues.append(
                f"Servicii de Accesibilitate active ({acc_names}) — interceptează fiecare atingere pe ecran și provoacă sacadare în scroll și ANR-uri!"
                if self.ro else
                f"Active Accessibility Services ({acc_names}) — intercept touch input and cause severe scroll stutter and ANRs!"
            )
            recommendations.append({
                "severity": "urgent",
                "title": (
                    f"Dezactivează Serviciile de Accesibilitate care încetinesc ecranul ({len(acc_services)} active)"
                    if self.ro else
                    f"Disable Accessibility Services Causing Touch & Scroll Lag ({len(acc_services)} active)"
                ),
                "description": (
                    f"Următoarele pachete interceptează interfața grafică în timp real: {acc_names}. Serviciile de accesibilitate (autoclickere, utilitare overlay) cauzează micro-stutter sever la scroll și blocaje 'Input dispatching timed out'."
                    if self.ro else
                    f"The following packages hook into every UI event in real time: {acc_names}. Accessibility overlays and auto-clickers cause severe micro-stutter and 'Input dispatching timed out' ANRs."
                ),
                "action_type": "disable_accessibility"
            })

        # 3. ANRs and Crashes (App Freezes & System Providers)
        total_anrs = anrs.get("total_anrs", 0)
        total_crashes = anrs.get("total_crashes", 0)
        culprits = anrs.get("top_culprits", [])
        if total_anrs > 0 or total_crashes > 0:
            penalty = min(total_anrs * 6 + total_crashes * 3, 30)
            score -= penalty
            top_names = ", ".join([c["package"] for c in culprits[:4]])
            issues.append(
                f"Detectate {total_anrs} înghețări (ANR) și {total_crashes} crash-uri recente în: {top_names}"
                if self.ro else
                f"Detected {total_anrs} freezes (ANR) and {total_crashes} crashes (last 24h) in: {top_names}"
            )

            for c in culprits[:5]:
                pkg = c["package"]
                count = c["count"]
                if pkg in provider_map:
                    provider_label = provider_map[pkg]
                    recommendations.append({
                        "severity": "urgent",
                        "title": (
                            f"📇 Reconstrucție Baze de Date Sistem: {provider_label} ({count} blocaje)"
                            if self.ro else
                            f"📇 Rebuild System Database: {provider_label} ({count} incidents)"
                        ),
                        "description": (
                            f"Componenta de sistem {pkg} ({provider_label}) are baza de date SQLite blocată sau într-o buclă de sincronizare, ceea ce face ca aplicațiile care depind de ea (WhatsApp, Telefon, Galerie, Mesaje, Tastatură) să înghețe! Apasă pentru reconstrucția curată a bazelor de date de sistem."
                            if self.ro else
                            f"System provider {pkg} ({provider_label}) has a locked SQLite database or sync loop, causing dependent apps (WhatsApp, Phone, Gallery, Messages, Keyboard) to freeze! Click to cleanly rebuild system provider databases."
                        ),
                        "action_type": "fix_contacts_acore",
                        "package": pkg
                    })
                else:
                    recommendations.append({
                        "severity": "urgent" if count >= 2 else "recomandat",
                        "title": (
                            f"Repară profund aplicația (fără ștergerea contului): {pkg}"
                            if self.ro else
                            f"Deep Repair App (Preserves Account & Data): {pkg}"
                        ),
                        "description": (
                            f"S-a blocat sau a crăpat de {count} ori în ultimele 24h. Această reparație oprește procesele blocate, șterge DOAR cache-ul corupt (păstrând datele și logarea!) și forțează recompilarea nativă AOT ('speed') a pachetului."
                            if self.ro else
                            f"Froze or crashed {count} times in the last 24h. This repair stops hung threads, clears ONLY corrupted cache (keeping login & user data intact!), and forces native AOT ('speed') compilation."
                        ),
                        "action_type": "deep_repair_app",
                        "package": pkg
                    })

        # 4. Storage & I/O Pressure Check
        io_stall = system_pressure.get("io_stall_percent", 0.0)
        if storage.get("status") == "critical" or io_stall >= 15.0:
            score -= 25
            issues.append(
                f"Blocaj pe stocarea internă ({storage.get('percent_used')}% ocupat, I/O stall {io_stall}%)"
                if self.ro else
                f"Internal storage bottleneck ({storage.get('percent_used')}% used, I/O stall {io_stall}%)"
            )
            recommendations.append({
                "severity": "urgent",
                "title": (
                    "Deblocare Viteză Stocare Flash (fstrim + Curățare Cache Sistem)"
                    if self.ro else "Restore UFS Flash Storage Speed (fstrim + System Cache Trim)"
                ),
                "description": (
                    f"Stocarea este ocupată {storage.get('percent_used')}% ({storage.get('free_gb')} GB liberi). Curăță toate fișierele cache neesențiale ale sistemului și rulează TRIM pe blocurile memoriei flash UFS."
                    if self.ro else
                    f"Storage is {storage.get('percent_used')}% full ({storage.get('free_gb')} GB free). Reclaims non-essential system caches and runs fstrim on UFS flash blocks."
                ),
                "action_type": "fstrim"
            })
        elif storage.get("status") == "warning":
            score -= 10
            issues.append(
                f"Stocare peste 80% ({storage.get('percent_used')}%)"
                if self.ro else f"Storage usage above 80% ({storage.get('percent_used')}%)"
            )
            recommendations.append({
                "severity": "recomandat",
                "title": (
                    "Mentenanță Stocare Flash (fstrim & Cache Trim)"
                    if self.ro else "Flash Storage Maintenance (fstrim & Cache Trim)"
                ),
                "description": (
                    "Eliberează cache-ul global de sistem și optimizează blocurile flash."
                    if self.ro else "Reclaims global system cache and optimizes UFS flash blocks."
                ),
                "action_type": "fstrim"
            })

        # 5. Memory & ZRAM Pressure
        mem_stall = system_pressure.get("mem_stall_percent", 0.0)
        if memory.get("swap_percent_used", 0) >= 85:
            score -= 20
            issues.append(
                f"ZRAM Swap saturat la {memory.get('swap_percent_used')}% ({memory.get('swap_used_mb')} MB) — procesele persistente din fundal sufocă memoria RAM"
                if self.ro else
                f"ZRAM Swap saturated at {memory.get('swap_percent_used')}% ({memory.get('swap_used_mb')} MB) — persistent background daemons are exhausting RAM"
            )
            recommendations.append({
                "severity": "urgent",
                "title": (
                    "🧠 Deblocare ZRAM & Temperare Servicii Grele de Fundal (AI / Telemetrie / Sync)"
                    if self.ro else
                    "🧠 Relieve ZRAM & Restrict Parasitic Background Services (AI / Telemetry / Sync)"
                ),
                "description": (
                    f"Memoria ZRAM este aproape plină ({memory.get('swap_percent_used')}%), forțând procesorul să comprime memorie continuu. Această acțiune restricționează serviciile parazite din fundal (servicii AI locale, telemetrie, debugging, aplicații companion), activează Cached App Freezer și eliberează RAM."
                    if self.ro else
                    f"ZRAM is nearly full ({memory.get('swap_percent_used')}%), forcing the CPU to constantly swap memory pages. This action restricts parasitic background daemons (local AI services, telemetry, debug tracing, companion apps), enables the Cached App Freezer, and frees RAM."
                ),
                "action_type": "debloat_pixel8"
            })
        elif memory.get("status") in ("critical", "warning") or mem_stall >= 10.0:
            score -= 15 if memory.get("status") == "critical" else 8
            issues.append(
                f"Presiune ridicată pe RAM ({memory.get('ram_percent_used')}%) și ZRAM Swap ({memory.get('swap_percent_used')}%)"
                if self.ro else
                f"High pressure on RAM ({memory.get('ram_percent_used')}%) and ZRAM Swap ({memory.get('swap_percent_used')}%)"
            )
            recommendations.append({
                "severity": "urgent" if memory.get("status") == "critical" else "recomandat",
                "title": (
                    "Eliberare RAM & Oprire Procese Parazite din Fundal"
                    if self.ro else "Free RAM & Stop Heavy Background Processes"
                ),
                "description": (
                    f"Doar {memory.get('available_mb')} MB RAM sunt disponibili, iar procesorul comprimă {memory.get('swap_used_mb')} MB în ZRAM. Apasă pentru a închide aplicațiile grele din fundal și a elibera memoria RAM instant."
                    if self.ro else
                    f"Only {memory.get('available_mb')} MB RAM available while {memory.get('swap_used_mb')} MB is compressed in ZRAM. Click to stop heavy background apps and free RAM immediately."
                ),
                "action_type": "optimize_ram"
            })

        # 6. Thermal / CPU Throttling
        temp = thermals.get("battery_temp_c", 0.0)
        if thermals.get("thermal_severity") in ("critical", "warning"):
            score -= 18 if thermals.get("thermal_severity") == "critical" else 8
            issues.append(
                f"Limitare termică procesor ({temp}°C - {thermals.get('thermal_status')})"
                if self.ro else
                f"CPU Thermal Throttling ({temp}°C - {thermals.get('thermal_status')})"
            )
            recommendations.append({
                "severity": "urgent",
                "title": (
                    "Oprire Consumatori CPU & Răcire Procesor"
                    if self.ro else "Stop Background CPU Hogs & Cool Down SoC"
                ),
                "description": (
                    f"La {temp}°C, procesorul își reduce frecvența pentru protecție termică, ceea ce cauzează sacadare severă. Această acțiune oprește forțat aplicațiile care consumă CPU în fundal."
                    if self.ro else
                    f"At {temp}°C, the SoC throttles clock speeds for thermal protection, causing severe UI lag. This action force-stops background apps consuming CPU."
                ),
                "action_type": "cool_down"
            })

        # 7. Uptime check
        uptime_days = device.get("uptime_days", 0)
        if uptime_days >= 5.0:
            score -= 8
            issues.append(
                f"Telefonul nu a fost repornit de {uptime_days} zile"
                if self.ro else f"Device has not been rebooted for {uptime_days} days"
            )
            recommendations.append({
                "severity": "recomandat",
                "title": (
                    "Restart Curat al Sistemului Android"
                    if self.ro else "Clean Android System Reboot"
                ),
                "description": (
                    f"După {uptime_days} zile fără restart, sistemul Android acumulează fragmentare în memoria grafică și ZRAM. Un restart curăță complet tabela de procese."
                    if self.ro else
                    f"After {uptime_days} days of uptime, Android accumulates GPU heap and ZRAM fragmentation. A clean reboot flushes the kernel process table."
                ),
                "action_type": "reboot"
            })

        # 8. Full AOT Speed Compilation
        recommendations.append({
            "severity": "optimizare",
            "title": (
                "Compilare Forțată 'Speed' pentru Toate Aplicațiile (ART AOT)"
                if self.ro else "Force 'Speed' ART Compilation for All Apps (AOT)"
            ),
            "description": (
                "Forțează compilarea codului aplicațiilor în cod mașină nativ rapid (modul 'speed-profile' + 'speed' pe pachetele critice), eliminând întârzierile de compilare JIT din timpul utilizării."
                if self.ro else
                "Forces Ahead-of-Time native machine code compilation ('speed' for critical UI packages + 'speed-profile' for all apps), eliminating runtime JIT lag."
            ),
            "action_type": "art_optimize"
        })

        score = max(5, min(100, score))

        if self.ro:
            verdict = "Excelent"
            badge_class = "success"
            if score < 50:
                verdict = "Problematic / Sacadare & Blocaje Active"
                badge_class = "danger"
            elif score < 75:
                verdict = "Performanță Scăzută / Necesită Optimizare"
                badge_class = "warning"
            elif score < 90:
                verdict = "Bună cu Mici Încetiniri"
                badge_class = "info"
        else:
            verdict = "Excellent"
            badge_class = "success"
            if score < 50:
                verdict = "Critical / Active Stutter & App Freezes"
                badge_class = "danger"
            elif score < 75:
                verdict = "Degraded Performance / Needs Optimization"
                badge_class = "warning"
            elif score < 90:
                verdict = "Good (Minor Bottlenecks)"
                badge_class = "info"

        return {
            "score": score,
            "verdict": verdict,
            "badge_class": badge_class,
            "issues": issues,
            "recommendations": recommendations
        }
