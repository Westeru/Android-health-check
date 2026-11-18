import os
import sys
import time
import tempfile
import datetime
import threading
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from adb_manager import AdbManager
from diagnostics import PhoneDiagnostics
from optimizer import PhoneOptimizer

app = FastAPI(title="Android Health & Performance Doctor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = getattr(sys, "_MEIPASS")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if not getattr(sys, "frozen", False):
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

adb = AdbManager()
last_report: Optional[dict] = None
initial_baselines: Dict[str, Dict[str, Any]] = {}

# Live job tracking state so the UI can show real-time step-by-step progress
job_lock = threading.Lock()
job_state: Dict[str, Any] = {
    "running": False,
    "action": None,
    "title": "",
    "step": 0,
    "total_steps": 1,
    "percent": 0,
    "current_task": "Idle",
    "logs": [],
    "started_at": 0.0,
    "elapsed_sec": 0,
    "completed": False,
    "success": True,
    "result_message": ""
}

class ActionRequest(BaseModel):
    action: str
    serial: Optional[str] = None
    package: Optional[str] = None
    lang: Optional[str] = "en"

class WirelessPairRequest(BaseModel):
    pairing_addr: str
    pairing_code: str
    connect_addr: Optional[str] = None
    lang: Optional[str] = "en"

class WirelessConnectRequest(BaseModel):
    connect_addr: str
    lang: Optional[str] = "en"

def _update_progress(step: int, total: int, current_task: str, log_msg: str):
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    with job_lock:
        job_state["step"] = step
        job_state["total_steps"] = max(1, total)
        job_state["percent"] = min(100, round((step / max(1, total)) * 100))
        job_state["current_task"] = current_task
        if log_msg:
            job_state["logs"].append(f"[{now_str}] {log_msg}")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/status")
def get_status(lang: str = "en"):
    ro = (lang == "ro")
    available = adb.is_available()
    devices = adb.get_devices(lang=lang) if available else []
    authorized = [d for d in devices if d["state"] == "device"]

    phone_activity = {
        "busy": False,
        "active_tasks": [],
        "summary": "Nicio operațiune în fundal" if ro else "Idle (no background tasks)"
    }
    if authorized:
        try:
            opt = PhoneOptimizer(adb, authorized[0]["serial"], lang=lang)
            phone_activity = opt.get_live_phone_activity()
        except Exception:
            pass

    with job_lock:
        is_job_running = job_state["running"]

    return {
        "adb_available": available,
        "adb_path": adb.adb_path,
        "devices": devices,
        "connected": len(devices) > 0,
        "has_authorized_device": len(authorized) > 0,
        "phone_activity": phone_activity,
        "job_running": is_job_running
    }

@app.get("/api/wireless/discover")
def wireless_discover(lang: str = "en"):
    if not adb.is_available():
        raise HTTPException(status_code=400, detail="ADB nu este disponibil." if lang == "ro" else "ADB is not available.")
    return adb.discover_wireless_services()

@app.post("/api/wireless/pair")
def wireless_pair(req: WirelessPairRequest):
    lang = req.lang or "en"
    if not adb.is_available():
        raise HTTPException(status_code=400, detail="ADB nu este disponibil." if lang == "ro" else "ADB is not available.")
    res = adb.pair_wireless(req.pairing_addr, req.pairing_code, req.connect_addr, lang=lang)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Pairing failed."))
    return res

@app.post("/api/wireless/connect")
def wireless_connect(req: WirelessConnectRequest):
    lang = req.lang or "en"
    if not adb.is_available():
        raise HTTPException(status_code=400, detail="ADB nu este disponibil." if lang == "ro" else "ADB is not available.")
    res = adb.connect_wireless(req.connect_addr, lang=lang)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Connection failed."))
    return res

@app.post("/api/wireless/disconnect")
def wireless_disconnect(req: dict = None):
    addr = req.get("address") if req else None
    lang = (req.get("lang") if req else "en") or "en"
    return adb.disconnect_wireless(addr, lang=lang)

@app.get("/api/job-status")
def get_job_status(lang: str = "en"):
    ro = (lang == "ro")
    devices = adb.get_devices(lang=lang)
    authorized = [d for d in devices if d["state"] == "device"]
    phone_activity = {
        "busy": False,
        "active_tasks": [],
        "summary": "Telefonul este în repaus" if ro else "Idle (all background tasks completed)"
    }
    if authorized:
        try:
            opt = PhoneOptimizer(adb, authorized[0]["serial"], lang=lang)
            phone_activity = opt.get_live_phone_activity()
        except Exception:
            pass

    with job_lock:
        if job_state["running"] and job_state["started_at"] > 0:
            job_state["elapsed_sec"] = round(time.time() - job_state["started_at"], 1)
        snapshot = dict(job_state)
        snapshot["logs"] = list(job_state["logs"])

    snapshot["phone_activity"] = phone_activity
    return snapshot

@app.get("/api/packages")
def list_installed_packages(serial: Optional[str] = None, lang: str = "en"):
    devices = adb.get_devices(lang=lang)
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(status_code=400, detail="Niciun dispozitiv autorizat conectat." if lang == "ro" else "No authorized device connected.")
    target_serial = serial or authorized[0]["serial"]
    opt = PhoneOptimizer(adb, target_serial, lang=lang)
    return {"packages": opt.get_installed_packages()}

@app.post("/api/scan")
def run_scan(req: dict = None):
    global last_report
    serial = req.get("serial") if req else None
    lang = ((req.get("lang") if req else "en") or "en")
    ro = (lang == "ro")

    devices = adb.get_devices(lang=lang)
    if not devices:
        raise HTTPException(
            status_code=400,
            detail="Niciun telefon conectat (USB sau Wi-Fi)." if ro else "No phone connected (USB or Wi-Fi)."
        )

    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(
            status_code=400,
            detail=(
                "Telefonul este conectat dar neautorizat. Deblochează ecranul telefonului și apasă pe 'Permiteți' (Allow USB/Wireless debugging)."
                if ro else
                "Phone is connected but unauthorized. Unlock your phone screen and tap 'Allow' on the USB/Wireless debugging prompt."
            )
        )

    target_serial = serial or authorized[0]["serial"]
    try:
        diag = PhoneDiagnostics(adb, target_serial, lang=lang)
        report = diag.run_full_scan()

        snap = {
            "timestamp": report["timestamp"],
            "score": report["health_evaluation"]["score"],
            "available_mb": report["memory"]["available_mb"],
            "ram_percent_used": report["memory"]["ram_percent_used"],
            "swap_used_mb": report["memory"]["swap_used_mb"],
            "swap_percent_used": report["memory"]["swap_percent_used"],
            "global_jank_percent": report["ui_fluency"]["global_jank_percent"],
            "total_anrs": report["anrs_and_crashes"]["total_anrs"],
        }
        if target_serial not in initial_baselines:
            initial_baselines[target_serial] = snap
        report["before_baseline"] = initial_baselines[target_serial]

        last_report = report
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{'Eroare internă la scanare' if ro else 'Internal scan error'}: {str(e)}"
        )

@app.get("/api/report")
def get_report():
    if not last_report:
        raise HTTPException(status_code=404, detail="No scan has been run yet.")
    return last_report

def _execute_job_worker(action: str, target_serial: str, package: Optional[str], lang: str = "en"):
    ro = (lang == "ro")
    optimizer = PhoneOptimizer(adb, target_serial, progress_cb=_update_progress, lang=lang)
    try:
        if action == "deep_boost_all":
            culprits = []
            if last_report and "anrs_and_crashes" in last_report:
                culprits = [c["package"] for c in last_report["anrs_and_crashes"].get("top_culprits", [])]
            else:
                diag = PhoneDiagnostics(adb, target_serial, lang=lang)
                anrs = diag.get_anr_and_crash_logs()
                culprits = [c["package"] for c in anrs.get("top_culprits", [])]
            res = optimizer.run_deep_boost_all(culprit_packages=culprits)
        elif action == "fix_ui_stutter":
            res = optimizer.fix_ui_stutter()
        elif action == "fix_contacts_acore":
            res = optimizer.fix_contacts_acore_loop()
        elif action == "debloat_pixel8":
            res = optimizer.debloat_pixel8_ram_hogs()
        elif action == "restore_animations":
            res = optimizer.restore_default_animations()
        elif action == "disable_accessibility":
            res = optimizer.disable_accessibility_services()
        elif action == "deep_repair_app":
            res = optimizer.deep_repair_app(package or "")
        elif action == "restrict_app_background":
            res = optimizer.restrict_app_background(package or "")
        elif action == "optimize_ram":
            res = optimizer.optimize_ram()
        elif action == "cool_down":
            res = optimizer.cool_down_cpu()
        elif action == "art_optimize":
            res = optimizer.run_art_optimization()
        elif action in ("fstrim", "storage_clean"):
            res = optimizer.run_fstrim()
        elif action == "trim_caches":
            res = optimizer.trim_system_caches()
        elif action == "force_stop":
            res = optimizer.force_stop_app(package or "")
        elif action == "clear_package_cache":
            res = optimizer.clear_app_data(package or "")
        elif action == "debloat_uninstall":
            res = optimizer.debloat_uninstall(package or "")
        elif action == "debloat_restore":
            res = optimizer.debloat_restore(package or "")
        elif action == "debloat_uninstall_all":
            res = optimizer.debloat_uninstall_all()
        elif action == "enable_adguard_dns":
            res = optimizer.enable_adguard_dns()
        elif action == "disable_private_dns":
            res = optimizer.disable_private_dns()
        elif action == "enable_deep_doze":
            res = optimizer.enable_deep_doze()
        elif action == "clean_storage_junk":
            res = optimizer.clean_storage_junk()
        elif action == "tv_clean_home":
            res = optimizer.toggle_tv_clean_home(True)
        elif action == "reboot":
            res = optimizer.reboot_device()
        else:
            res = {
                "success": False,
                "title": "Eroare" if ro else "Error",
                "message": f"{'Acțiune necunoscută' if ro else 'Unknown action'}: {action}"
            }

        with job_lock:
            job_state["running"] = False
            job_state["completed"] = True
            job_state["percent"] = 100
            job_state["success"] = res.get("success", True)
            job_state["title"] = res.get("title", "Finalizat" if ro else "Completed")
            job_state["result_message"] = res.get("message", "Acțiune finalizată." if ro else "Action completed.")
            job_state["current_task"] = (
                ("✅ FINALIZAT CU SUCCES!" if res.get("success", True) else "⚠️ Finalizat cu erori")
                if ro else
                ("✅ COMPLETED SUCCESSFULLY!" if res.get("success", True) else "⚠️ Completed with warnings")
            )
            job_state["elapsed_sec"] = round(time.time() - job_state["started_at"], 1)
    except Exception as e:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        with job_lock:
            job_state["running"] = False
            job_state["completed"] = True
            job_state["success"] = False
            job_state["current_task"] = f"❌ {'Eroare' if ro else 'Error'}: {str(e)}"
            job_state["result_message"] = str(e)
            job_state["logs"].append(f"[{now_str}] ❌ {'Eroare la execuție' if ro else 'Execution error'}: {str(e)}")
            job_state["elapsed_sec"] = round(time.time() - job_state["started_at"], 1)

@app.post("/api/optimize")
def run_optimization(req: ActionRequest):
    lang = req.lang or "en"
    ro = (lang == "ro")
    devices = adb.get_devices(lang=lang)
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(
            status_code=400,
            detail="Niciun dispozitiv autorizat conectat." if ro else "No authorized device connected."
        )

    with job_lock:
        if job_state["running"]:
            return {
                "started": False,
                "already_running": True,
                "message": (
                    "O optimizare este deja în curs de desfășurare! Urmărește consola live de pe ecran."
                    if ro else "An optimization is already running! Check the live execution console on screen."
                )
            }

        target_serial = req.serial or authorized[0]["serial"]
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        job_state["running"] = True
        job_state["completed"] = False
        job_state["action"] = req.action
        job_state["title"] = f"{'Execuție' if ro else 'Running'}: {req.action}"
        job_state["step"] = 0
        job_state["total_steps"] = 1
        job_state["percent"] = 5
        job_state["current_task"] = (
            "Inițializare conexiune ADB cu telefonul..."
            if ro else "Initializing ADB connection with device..."
        )
        job_state["logs"] = [
            f"[{now_str}] 🚀 {'S-a pornit acțiunea' if ro else 'Started action'} '{req.action}' {'pe dispozitivul' if ro else 'on device'} {target_serial}..."
        ]
        job_state["started_at"] = time.time()
        job_state["elapsed_sec"] = 0
        job_state["success"] = True
        job_state["result_message"] = ""

    worker = threading.Thread(
        target=_execute_job_worker,
        args=(req.action, target_serial, req.package, lang),
        daemon=True
    )
    worker.start()

    return {
        "started": True,
        "message": (
            "Optimizarea a pornit! Urmărește progresul pas cu pas în panoul live."
            if ro else "Optimization started! Watch real-time step-by-step progress in the live console."
        )
    }

@app.post("/api/remote/key")
def remote_key(req: dict):
    keycode = req.get("keycode", "")
    serial = req.get("serial")
    lang = req.get("lang", "en")
    devices = adb.get_devices(lang=lang)
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(status_code=400, detail="No authorized device connected.")
    target_serial = serial or authorized[0]["serial"]
    opt = PhoneOptimizer(adb, target_serial, lang=lang)
    return opt.send_remote_key(keycode)

@app.post("/api/remote/text")
def remote_text(req: dict):
    text = req.get("text", "")
    submit_enter = bool(req.get("submit_enter", False))
    serial = req.get("serial")
    lang = req.get("lang", "en")
    devices = adb.get_devices(lang=lang)
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(status_code=400, detail="No authorized device connected.")
    target_serial = serial or authorized[0]["serial"]
    opt = PhoneOptimizer(adb, target_serial, lang=lang)
    return opt.send_remote_text(text, submit_enter=submit_enter)

@app.post("/api/install-apk")
async def install_apk(request: Request, filename: str = "app.apk", serial: Optional[str] = None, lang: str = "en"):
    ro = (lang == "ro")
    devices = adb.get_devices(lang=lang)
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(status_code=400, detail="Niciun dispozitiv conectat." if ro else "No authorized device connected.")
    target_serial = serial or authorized[0]["serial"]

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Fișier APK gol." if ro else "Empty APK file.")

    safe_name = os.path.basename(filename)
    if not safe_name.lower().endswith(".apk"):
        safe_name += ".apk"
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, safe_name)
    with open(tmp_path, "wb") as f:
        f.write(body)

    def _apk_worker():
        opt = PhoneOptimizer(adb, target_serial, progress_cb=_update_progress, lang=lang)
        try:
            res = opt.install_apk_file(tmp_path)
            with job_lock:
                job_state["running"] = False
                job_state["completed"] = True
                job_state["percent"] = 100
                job_state["success"] = res.get("success", False)
                job_state["title"] = res.get("title", "APK Install")
                job_state["result_message"] = res.get("message", "")
                job_state["current_task"] = res.get("message", "")
                job_state["elapsed_sec"] = round(time.time() - job_state["started_at"], 1)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    with job_lock:
        job_state["running"] = True
        job_state["completed"] = False
        job_state["action"] = "install_apk"
        job_state["title"] = f"APK Install: {safe_name}"
        job_state["step"] = 1
        job_state["total_steps"] = 2
        job_state["percent"] = 25
        job_state["current_task"] = f"{'Se instalează' if ro else 'Installing'} {safe_name}..."
        job_state["logs"] = [f"[{now_str}] 📦 {'Transfer și instalare APK' if ro else 'Uploading & installing APK'}: {safe_name}..."]
        job_state["started_at"] = time.time()
        job_state["elapsed_sec"] = 0
        job_state["success"] = True
        job_state["result_message"] = ""

    threading.Thread(target=_apk_worker, daemon=True).start()
    return {"started": True, "filename": safe_name}
