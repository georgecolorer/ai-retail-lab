import os
import subprocess
import sys
import urllib.request
import webbrowser

URL = "http://localhost:8501"

try:
    urllib.request.urlopen(f"{URL}/_stcore/health", timeout=1)
    webbrowser.open(URL)
    sys.exit(0)
except Exception:
    pass

base_dir = os.path.dirname(os.path.abspath(__file__))
py_exe = os.path.abspath(os.path.join(base_dir, "..", ".venv", "Scripts", "python.exe"))
dash = os.path.join(base_dir, "dashboard.py")

if os.path.exists(py_exe) and os.path.exists(dash):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    subprocess.Popen(
        [py_exe, "-m", "streamlit", "run", dash, "--server.port", "8501", "--server.headless", "false"],
        cwd=base_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
    )