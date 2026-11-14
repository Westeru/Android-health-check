import os
import time
import datetime
import threading
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

adb = AdbManager()
last_report: Optional[dict] = None

# Live job tracking state so the UI can show real-time step-by-step progress
job_lock = threading.Lock()
job_state: Dict[str, Any] = {
    "running": False,
    "action": None,
    "title": "",
    "step": 0,
    "total_steps": 1,
    "percent": 0,
    "current_task": "În așteptare",
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

class WirelessPairRequest(BaseModel):
    pairing_addr: str
    pairing_code: str
    connect_addr: Optional[str] = None

class WirelessConnectRequest(BaseModel):
    connect_addr: str

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
def get_status():
    available = adb.is_available()
    devices = adb.get_devices() if available else []
    authorized = [d for d in devices if d["state"] == "device"]

    phone_activity = {"busy": False, "active_tasks": [], "summary": "Nicio operațiune în fundal"}
    if authorized:
        try:
            opt = PhoneOptimizer(adb, authorized[0]["serial"])
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
def wireless_discover():
    if not adb.is_available():
        raise HTTPException(status_code=400, detail="ADB nu este disponibil.")
    return adb.discover_wireless_services()

@app.post("/api/wireless/pair")
def wireless_pair(req: WirelessPairRequest):
    if not adb.is_available():
        raise HTTPException(status_code=400, detail="ADB nu este disponibil.")
    res = adb.pair_wireless(req.pairing_addr, req.pairing_code, req.connect_addr)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Eroare la asociere."))
    return res

@app.post("/api/wireless/connect")
def wireless_connect(req: WirelessConnectRequest):
    if not adb.is_available():
        raise HTTPException(status_code=400, detail="ADB nu este disponibil.")
    res = adb.connect_wireless(req.connect_addr)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Eroare la conectare."))
    return res

@app.post("/api/wireless/disconnect")
def wireless_disconnect(req: dict = None):
    addr = req.get("address") if req else None
    return adb.disconnect_wireless(addr)

@app.get("/api/job-status")
def get_job_status():
    devices = adb.get_devices()
    authorized = [d for d in devices if d["state"] == "device"]
    phone_activity = {"busy": False, "active_tasks": [], "summary": "Telefonul este în repaus"}
    if authorized:
        try:
            opt = PhoneOptimizer(adb, authorized[0]["serial"])
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
def list_installed_packages(serial: Optional[str] = None):
    devices = adb.get_devices()
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(status_code=400, detail="Niciun dispozitiv autorizat conectat.")
    target_serial = serial or authorized[0]["serial"]
    opt = PhoneOptimizer(adb, target_serial)
    return {"packages": opt.get_installed_packages()}

@app.post("/api/scan")
def run_scan(req: dict = None):
    global last_report
    serial = req.get("serial") if req else None

    devices = adb.get_devices()
    if not devices:
        raise HTTPException(status_code=400, detail="Niciun telefon conectat (USB sau Wi-Fi).")

    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(
            status_code=400,
            detail="Telefonul este conectat dar neautorizat. Deblochează ecranul telefonului și apasă pe 'Permiteți' (Allow USB/Wireless debugging)."
        )

    target_serial = serial or authorized[0]["serial"]
    try:
        diag = PhoneDiagnostics(adb, target_serial)
        report = diag.run_full_scan()
        last_report = report
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare internă la scanare: {str(e)}")

@app.get("/api/report")
def get_report():
    if not last_report:
        raise HTTPException(status_code=404, detail="Nu s-a efectuat încă nicio scanare.")
    return last_report

def _execute_job_worker(action: str, target_serial: str, package: Optional[str]):
    optimizer = PhoneOptimizer(adb, target_serial, progress_cb=_update_progress)
    try:
        if action == "deep_boost_all":
            culprits = []
            if last_report and "anrs_and_crashes" in last_report:
                culprits = [c["package"] for c in last_report["anrs_and_crashes"].get("top_culprits", [])]
            else:
                # Quick scan of exit-info if user didn't scan first
                diag = PhoneDiagnostics(adb, target_serial)
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
        elif action == "fstrim":
            res = optimizer.run_fstrim()
        elif action == "trim_caches":
            res = optimizer.trim_system_caches()
        elif action == "force_stop":
            res = optimizer.force_stop_app(package or "")
        elif action == "clear_package_cache":
            res = optimizer.clear_app_data(package or "")
        elif action == "reboot":
            res = optimizer.reboot_device()
        else:
            res = {"success": False, "title": "Eroare", "message": f"Acțiune necunoscută: {action}"}

        with job_lock:
            job_state["running"] = False
            job_state["completed"] = True
            job_state["percent"] = 100
            job_state["success"] = res.get("success", True)
            job_state["title"] = res.get("title", "Finalizat")
            job_state["result_message"] = res.get("message", "Acțiune finalizată.")
            job_state["current_task"] = "✅ FINALIZAT CU SUCCES!" if res.get("success", True) else "⚠️ Finalizat cu erori"
            job_state["elapsed_sec"] = round(time.time() - job_state["started_at"], 1)
    except Exception as e:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        with job_lock:
            job_state["running"] = False
            job_state["completed"] = True
            job_state["success"] = False
            job_state["current_task"] = f"❌ Eroare: {str(e)}"
            job_state["result_message"] = str(e)
            job_state["logs"].append(f"[{now_str}] ❌ Eroare la execuție: {str(e)}")
            job_state["elapsed_sec"] = round(time.time() - job_state["started_at"], 1)

@app.post("/api/optimize")
def run_optimization(req: ActionRequest):
    devices = adb.get_devices()
    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        raise HTTPException(status_code=400, detail="Niciun dispozitiv autorizat conectat.")

    with job_lock:
        if job_state["running"]:
            return {
                "started": False,
                "already_running": True,
                "message": "O optimizare este deja în curs de desfășurare! Urmărește consola live de pe ecran."
            }

        target_serial = req.serial or authorized[0]["serial"]
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        job_state["running"] = True
        job_state["completed"] = False
        job_state["action"] = req.action
        job_state["title"] = f"Execuție: {req.action}"
        job_state["step"] = 0
        job_state["total_steps"] = 1
        job_state["percent"] = 5
        job_state["current_task"] = "Inițializare conexiune ADB cu telefonul..."
        job_state["logs"] = [f"[{now_str}] 🚀 S-a pornit acțiunea '{req.action}' pe dispozitivul {target_serial}..."]
        job_state["started_at"] = time.time()
        job_state["elapsed_sec"] = 0
        job_state["success"] = True
        job_state["result_message"] = ""

    worker = threading.Thread(
        target=_execute_job_worker,
        args=(req.action, target_serial, req.package),
        daemon=True
    )
    worker.start()

    return {
        "started": True,
        "message": "Optimizarea a pornit! Urmărește progresul pas cu pas în panoul live."
    }
