import os
import sys
import shutil
import subprocess
from adb_manager import AdbManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 68)
    print("  Building Standalone Windows Executable: AndroidHealthDoctor.exe")
    print("=" * 68)

    # 1. Ensure ADB binaries are available to bundle inside the EXE
    adb_mgr = AdbManager()
    adb_exe = adb_mgr.adb_path
    if not os.path.isfile(adb_exe):
        adb_exe = adb_mgr.auto_download_adb() or ""

    bundle_pt_dir = os.path.join(BASE_DIR, "build_platform_tools")
    os.makedirs(bundle_pt_dir, exist_ok=True)

    if adb_exe and os.path.isfile(adb_exe):
        pt_src_dir = os.path.dirname(adb_exe)
        for fname in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "libwinpthread-1.dll"):
            src_file = os.path.join(pt_src_dir, fname)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, os.path.join(bundle_pt_dir, fname))
        print(f"[+] Bundling official ADB binaries from: {pt_src_dir}")
    else:
        print("[!] Warning: ADB binaries not found locally; EXE will auto-download ADB on first run.")

    excluded_modules = [
        "numpy", "PIL", "matplotlib", "pandas", "scipy", "torch",
        "tkinter", "unittest", "pydoc", "test", "sqlite3"
    ]
    exclude_args = []
    for mod in excluded_modules:
        exclude_args.extend(["--exclude-module", mod])

    # 2. Run PyInstaller with clean environment
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", "AndroidHealthDoctor",
        "--add-data", f"{os.path.join(BASE_DIR, 'templates')};templates",
        "--add-data", f"{os.path.join(BASE_DIR, 'static')};static",
        "--add-data", f"{bundle_pt_dir};platform-tools",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        *exclude_args,
        os.path.join(BASE_DIR, "main.py")
    ]

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)

    print("[*] Running PyInstaller...")
    res = subprocess.run(pyinstaller_args, cwd=BASE_DIR, env=clean_env)

    # Clean up temporary build folders
    shutil.rmtree(bundle_pt_dir, ignore_errors=True)
    shutil.rmtree(os.path.join(BASE_DIR, "build"), ignore_errors=True)
    spec_file = os.path.join(BASE_DIR, "AndroidHealthDoctor.spec")
    if os.path.isfile(spec_file):
        try:
            os.remove(spec_file)
        except Exception:
            pass

    exe_out = os.path.join(BASE_DIR, "dist", "AndroidHealthDoctor.exe")
    if res.returncode == 0 and os.path.isfile(exe_out):
        size_mb = round(os.path.getsize(exe_out) / (1024 * 1024), 2)
        print("\n" + "=" * 68)
        print(f"[SUCCESS] Standalone app built: {exe_out} ({size_mb} MB)")
        print("          No Python or ADB installation required on target PCs!")
        print("=" * 68)
    else:
        print("[!] Build failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
