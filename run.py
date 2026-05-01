import subprocess
import sys
import os
import signal
import threading
import socket

base = os.path.dirname(os.path.abspath(__file__))
processes = []

# Detect virtual environment Python
def get_python_executable():
    venv_python = os.path.join(base, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    venv_python_unix = os.path.join(base, ".venv", "bin", "python")
    if os.path.exists(venv_python_unix):
        return venv_python_unix
    return sys.executable

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def stream(proc, prefix):
    for line in proc.stdout:
        print(f"[{prefix}] {line}", end="")

def shutdown(sig=None, frame=None):
    print("\nShutting down...")
    for p in processes:
        p.kill()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

if is_port_in_use(8000):
    print("[error] Port 8000 is already in use. Please free it and try again.")
    sys.exit(1)

if is_port_in_use(3000):
    print("[error] Port 3000 is already in use. Please free it and try again.")
    sys.exit(1)

python_exe = get_python_executable()
backend = subprocess.Popen(
    [python_exe, "-m", "uvicorn", "main:app", "--reload"],
    cwd=os.path.join(base, "backend"),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

frontend = subprocess.Popen(
    ["node", "server.js"],
    cwd=os.path.join(base, "frontend"),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

processes.extend([backend, frontend])

threading.Thread(target=stream, args=(backend, "backend"), daemon=True).start()
threading.Thread(target=stream, args=(frontend, "frontend"), daemon=True).start()

print("Backend  → http://localhost:8000")
print("Frontend → http://localhost:3000")
print("Press Ctrl+C to stop.\n")

backend.wait()
frontend.wait()
