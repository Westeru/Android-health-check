import re
import datetime
from typing import Dict, Any, List, Optional
from adb_manager import AdbManager

class PhoneDiagnostics:
    """Performs deep health, UI jank/stutter, and freeze diagnostics on any connected Android device."""

    # Map shared Android process names to their underlying package names
    PROCESS_TO_PACKAGE_MAP = {
        "android.process.acore": "com.android.providers.contacts",
        "android.process.media": "com.android.providers.media.module",
        "com.google.process.gservices": "com.google.android.gsf",
        "com.google.process.gapps": "com.google.android.gms",
    }

    # Known system provider packages whose SQLite database corruption freezes dependent apps
    SYSTEM_PROVIDER_PACKAGES = {
        "com.android.providers.contacts": "Baza de date Contacte & Apeluri (acore)",
        "com.android.providers.media.module": "Indexul Media & Fișiere (MediaStore)",
        "com.android.providers.media": "Indexul Media (MediaStore)",
        "com.android.providers.downloads": "Managerul de Descărcări (Downloads)",
        "com.android.providers.calendar": "Baza de date Calendar",
        "com.google.android.gsf": "Google Services Framework (Sincronizare)",
        "com.google.android.gms": "Google Play Services",
    }

    def __init__(self, adb: AdbManager, serial: Optional[str] = None):
        self.adb = adb
        self.serial = serial

    def run_full_scan(self) -> Dict[str, Any]:
        """Runs the complete diagnostic suite and aggregates findings."""
        device_info = self.get_device_info()
        storage = self.get_storage_info()
        memory = self.get_memory_info()
        anrs_crashes = self.get_anr_and_crash_logs()
        thermals_cpu = self.get_thermal_and_cpu_info(device_info.get("soc", "SoC"))
        battery = self.get_battery_info()
        ui_fluency = self.get_ui_fluency_and_jank()
        system_pressure = self.get_psi_and_accessibility()

        system_health = self.calculate_health_score(
            storage, memory, anrs_crashes, thermals_cpu, battery, device_info, ui_fluency, system_pressure
        )

        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "device": device_info,
            "storage": storage,
            "memory": memory,
            "anrs_and_crashes": anrs_crashes,
            "thermals_and_cpu": thermals_cpu,
            "battery": battery,
            "ui_fluency": ui_fluency,
            "system_pressure": system_pressure,
            "health_evaluation": system_health
        }

    def get_device_info(self) -> Dict[str, Any]:
        """Gathers core model, brand, SoC chipset, OS version, security patch, and uptime."""
        def get_prop(prop_name: str, fallback: str = "") -> str:
            ok, out = self.adb.run_shell(f"getprop {prop_name}", self.serial, timeout=5)
            val = out.strip() if ok and out else ""
            return val if val else fallback

        model = get_prop("ro.product.model", "Dispozitiv Android")
        brand = get_prop("ro.product.brand", "Android").capitalize()
        device_codename = get_prop("ro.product.device", "generic")
        android_ver = get_prop("ro.build.version.release", "N/A")
        sdk_ver = get_prop("ro.build.version.sdk", "N/A")
        security_patch = get_prop("ro.build.version.security_patch", "N/A")
        build_id = get_prop("ro.build.id", "N/A")
        soc_model = get_prop("ro.soc.model") or get_prop("ro.board.platform") or get_prop("ro.hardware") or "ARM64 SoC"

        # Uptime
        uptime_str = "Necunoscut"
        uptime_days = 0.0
        ok, uptime_out = self.adb.run_shell("cat /proc/uptime", self.serial, timeout=5)
        if ok and uptime_out:
            try:
                seconds = float(uptime_out.split()[0])
                uptime_days = round(seconds / 86400, 1)
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                uptime_str = f"{hours // 24}z {hours % 24}h {minutes}m"
            except Exception:
                pass

        return {
            "model": model,
            "brand": brand,
            "codename": device_codename,
            "soc": soc_model,
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
        if percent_used >= 90 or (free_gb > 0 and free_gb < 8.0):
            status = "critical"
        elif percent_used >= 80 or (free_gb > 0 and free_gb < 15.0):
            status = "warning"

        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "percent_used": percent_used,
            "status": status,
            "summary": f"{used_gb} GB folosiți din {total_gb} GB ({percent_used}% • {free_gb} GB liberi)"
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
        if ram_percent_used >= 88 or swap_percent_used >= 85 or (available_mb > 0 and available_mb < 900):
            status = "critical"
        elif ram_percent_used >= 78 or swap_percent_used >= 65:
            status = "warning"

        top_apps = []
        ok_dumpsys, mem_dumpsys = self.adb.run_shell("dumpsys meminfo | head -n 45", self.serial, timeout=15)
        if ok_dumpsys and mem_dumpsys:
            seen_pkgs = set()
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
                        if mb > 90:
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
        """Analyzes why the phone feels choppy ('sacadat'): refresh rate, animation scales, and GPU frame drops (jank)."""
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
        """Checks Accessibility hooks (major cause of lag/sacadare), I/O & Memory stall pressure, and Battery Saver."""
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
                        anr_events.append({
                            "package": package,
                            "type": "ANR (Înghețare)" if "ANR" in reason_name else reason_name,
                            "date": date_str,
                            "details": description or subreason or "Firul principal UI blocat (Input dispatch timed out)"
                        })
                    elif "CRASH" in reason_name or "INITIALIZATION_FAILURE" in reason_name:
                        app_problem_counts[package] = app_problem_counts.get(package, 0) + 1
                        crash_events.append({
                            "package": package,
                            "type": reason_name,
                            "date": date_str,
                            "details": description or subreason or "Eroare internă aplicație"
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

    def get_thermal_and_cpu_info(self, soc_name: str = "SoC") -> Dict[str, Any]:
        """Monitors battery temperature, thermal throttling status, and top CPU processes."""
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

        thermal_status = "Răcoros / Fără limitări"
        thermal_severity = "normal"
        if battery_temp_c >= 41.5 or thermal_headroom_status >= 3:
            thermal_status = "Throttling Sever Activ (Procesor limitat termic!)"
            thermal_severity = "critical"
        elif battery_temp_c >= 38.0 or thermal_headroom_status >= 1:
            thermal_status = f"Cald (Limitare parțială {soc_name})"
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
        health = "Bună"
        cycles = "N/A"

        ok_bat, bat_out = self.adb.run_shell("dumpsys battery", self.serial)
        if ok_bat and bat_out:
            lvl_match = re.search(r"level:\s*(\d+)", bat_out)
            if lvl_match:
                level = int(lvl_match.group(1))
            health_match = re.search(r"health:\s*(\d+)", bat_out)
            if health_match:
                h_val = int(health_match.group(1))
                health_map = {1: "Necunoscută", 2: "Bună (Optim)", 3: "Supraîncălzire", 4: "Uzată / Defectă", 5: "Supratensiune"}
                health = health_map.get(h_val, "Normală")

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

        # 0. Master 1-Click Deep Fix Recommendation
        recommendations.append({
            "severity": "urgent",
            "title": "⚡ Super-Optimizare Completă (Anti-Sacadare & Deblocare Aplicații)",
            "description": "Rulează automat protocolul complet de reparație: curăță cache-ul corupt din SystemUI, Launcher și Android WebView, eliberează memoria RAM/ZRAM, setează animațiile la 0.5x (instant), activează rata de refresh maximă, optimizează stocarea flash (fstrim) și recompilează nativ (în mod 'speed') toate aplicațiile cu blocaje.",
            "action_type": "deep_boost_all"
        })

        # 1. UI Fluency / Stutter ("Sacadat") Check
        jank_pct = ui_fluency.get("global_jank_percent", 0.0)
        janky_apps = ui_fluency.get("janky_apps", [])
        smooth_on = ui_fluency.get("smooth_display_enabled", True)
        anim_scale = ui_fluency.get("window_animation_scale", 1.0)

        if jank_pct >= 10.0 or not smooth_on:
            score -= 15
            if not smooth_on:
                issues.append(f"Ecranul rulează la doar {ui_fluency.get('peak_refresh_rate', 60)}Hz (rata de refresh înaltă 90/120Hz este oprită) — cauzează senzația de mișcare sacadată")
            if jank_pct >= 10.0:
                worst_jank = ", ".join([f"{a['package']} ({a['jank_percent']}%)" for a in janky_apps[:3]])
                issues.append(f"Pierderi ridicate de cadre UI (Frame Drops / Sacadare: {jank_pct}% global) în: {worst_jank}")

        if anim_scale >= 1.0 or not smooth_on or jank_pct >= 8.0:
            recommendations.append({
                "severity": "urgent" if (jank_pct >= 15.0 or not smooth_on) else "recomandat",
                "title": "Eliminare Mișcare Sacadată (Boost 120Hz + Animații 0.5x + Optimizare Launcher/WebView)",
                "description": f"Rata de cadre pierdute (jank) este {jank_pct}%, iar scara animațiilor este {anim_scale}x. Această acțiune activează rata maximă de refresh, scurtează animațiile la 0.5x pentru răspuns instant și recompilează Launcher-ul telefonului, SystemUI și Android System WebView.",
                "action_type": "fix_ui_stutter"
            })

        # 2. Accessibility Services Check
        acc_services = system_pressure.get("accessibility_services", [])
        if acc_services:
            score -= 12
            acc_names = ", ".join([a["package"] for a in acc_services])
            issues.append(f"Servicii de Accesibilitate active ({acc_names}) — interceptează fiecare atingere pe ecran și provoacă sacadare în scroll și ANR-uri!")
            recommendations.append({
                "severity": "urgent",
                "title": f"Dezactivează Serviciile de Accesibilitate care încetinesc ecranul ({len(acc_services)} active)",
                "description": f"Următoarele pachete interceptează interfața grafică în timp real: {acc_names}. Serviciile de accesibilitate (autoclickere, utilitare overlay) cauzează micro-stutter sever la scroll și blocaje 'Input dispatching timed out'.",
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
            issues.append(f"Detectate {total_anrs} înghețări (ANR) și {total_crashes} crash-uri recente în: {top_names}")

            has_provider_issue = False
            for c in culprits[:5]:
                pkg = c["package"]
                count = c["count"]
                if pkg in self.SYSTEM_PROVIDER_PACKAGES:
                    has_provider_issue = True
                    provider_label = self.SYSTEM_PROVIDER_PACKAGES[pkg]
                    recommendations.append({
                        "severity": "urgent",
                        "title": f"📇 Reconstrucție Baze de Date Sistem: {provider_label} ({count} blocaje)",
                        "description": f"Componenta de sistem {pkg} ({provider_label}) are baza de date SQLite blocată sau într-o buclă de sincronizare, ceea ce face ca aplicațiile care depind de ea (WhatsApp, Telefon, Galerie, Mesaje, Tastatură) să înghețe! Apasă pentru reconstrucția curată a bazelor de date de sistem.",
                        "action_type": "fix_contacts_acore",
                        "package": pkg
                    })
                else:
                    recommendations.append({
                        "severity": "urgent" if count >= 2 else "recomandat",
                        "title": f"Repară profund aplicația (fără ștergerea contului): {pkg}",
                        "description": f"S-a blocat sau a crăpat de {count} ori în ultimele 24h. Această reparație oprește procesele blocate, șterge DOAR cache-ul corupt (păstrând datele și logarea!) și forțează recompilarea nativă AOT ('speed') a pachetului.",
                        "action_type": "deep_repair_app",
                        "package": pkg
                    })

        # 4. Storage & I/O Pressure Check
        io_stall = system_pressure.get("io_stall_percent", 0.0)
        if storage.get("status") == "critical" or io_stall >= 15.0:
            score -= 25
            issues.append(f"Blocaj pe stocarea internă ({storage.get('percent_used')}% ocupat, I/O stall {io_stall}%)")
            recommendations.append({
                "severity": "urgent",
                "title": "Deblocare Viteză Stocare Flash (fstrim + Curățare Cache Sistem)",
                "description": f"Stocarea este ocupată {storage.get('percent_used')}% ({storage.get('free_gb')} GB liberi). Curăță toate fișierele cache neesențiale ale sistemului și rulează TRIM pe blocurile memoriei flash UFS.",
                "action_type": "storage_clean"
            })
        elif storage.get("status") == "warning":
            score -= 10
            issues.append(f"Stocare peste 80% ({storage.get('percent_used')}%)")
            recommendations.append({
                "severity": "recomandat",
                "title": "Mentenanță Stocare Flash (fstrim & Cache Trim)",
                "description": "Eliberează cache-ul global de sistem și optimizează blocurile flash.",
                "action_type": "storage_clean"
            })

        # 5. Memory & ZRAM Pressure
        mem_stall = system_pressure.get("mem_stall_percent", 0.0)
        if memory.get("swap_percent_used", 0) >= 85:
            score -= 20
            issues.append(f"ZRAM Swap saturat la {memory.get('swap_percent_used')}% ({memory.get('swap_used_mb')} MB) — procesele persistente din fundal sufocă memoria RAM")
            recommendations.append({
                "severity": "urgent",
                "title": "🧠 Deblocare ZRAM & Temperare Servicii Grele de Fundal (AI / Telemetrie / Sync)",
                "description": f"Memoria ZRAM este aproape plină ({memory.get('swap_percent_used')}%), forțând procesorul să comprime memorie continuu. Această acțiune restricționează serviciile parazite din fundal (servicii AI locale, telemetrie, debugging, aplicații companion), activează Cached App Freezer și eliberează RAM.",
                "action_type": "debloat_pixel8"
            })
        elif memory.get("status") in ("critical", "warning") or mem_stall >= 10.0:
            score -= 15 if memory.get("status") == "critical" else 8
            issues.append(f"Presiune ridicată pe RAM ({memory.get('ram_percent_used')}%) și ZRAM Swap ({memory.get('swap_percent_used')}%)")
            recommendations.append({
                "severity": "urgent" if memory.get("status") == "critical" else "recomandat",
                "title": "Eliberare RAM & Oprire Procese Parazite din Fundal",
                "description": f"Doar {memory.get('available_mb')} MB RAM sunt disponibili, iar procesorul comprimă {memory.get('swap_used_mb')} MB în ZRAM. Apasă pentru a închide aplicațiile grele din fundal și a elibera memoria RAM instant.",
                "action_type": "optimize_ram"
            })

        # 6. Thermal / CPU Throttling
        temp = thermals.get("battery_temp_c", 0.0)
        if thermals.get("thermal_severity") in ("critical", "warning"):
            score -= 18 if thermals.get("thermal_severity") == "critical" else 8
            issues.append(f"Limitare termică procesor ({temp}°C - {thermals.get('thermal_status')})")
            recommendations.append({
                "severity": "urgent",
                "title": "Oprire Consumatori CPU & Răcire Procesor",
                "description": f"La {temp}°C, procesorul își reduce frecvența pentru protecție termică, ceea ce cauzează sacadare severă. Această acțiune oprește forțat aplicațiile care consumă CPU în fundal.",
                "action_type": "cool_down"
            })

        # 7. Uptime check
        uptime_days = device.get("uptime_days", 0)
        if uptime_days >= 5.0:
            score -= 8
            issues.append(f"Telefonul nu a fost repornit de {uptime_days} zile")
            recommendations.append({
                "severity": "recomandat",
                "title": "Restart Curat al Sistemului Android",
                "description": f"După {uptime_days} zile fără restart, sistemul Android acumulează fragmentare în memoria grafică și ZRAM. Un restart curăță complet tabela de procese.",
                "action_type": "reboot"
            })

        # 8. Full AOT Speed Compilation
        recommendations.append({
            "severity": "optimizare",
            "title": "Compilare Forțată 'Speed' pentru Toate Aplicațiile (ART AOT)",
            "description": "Forțează compilarea codului aplicațiilor în cod mașină nativ rapid (modul 'speed-profile' + 'speed' pe pachetele critice), eliminând întârzierile de compilare JIT din timpul utilizării.",
            "action_type": "art_optimize"
        })

        score = max(5, min(100, score))

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

        return {
            "score": score,
            "verdict": verdict,
            "badge_class": badge_class,
            "issues": issues,
            "recommendations": recommendations
        }
