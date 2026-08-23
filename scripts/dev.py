"""开发模式：同进程拉起后端 uvicorn 与前端 Vite dev server。

用法：python scripts/dev.py
- 后端 http://127.0.0.1:8000
- 前端 http://127.0.0.1:5173 （Vite proxy 将 /api 转发到后端）
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BACKEND_CMD = [
    sys.executable,
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--app-dir",
    str(ROOT / "backend"),
    "--reload",
]
FRONTEND_CMD = ["npm", "run", "dev", "--", "--host", "127.0.0.1"]


def main() -> None:
    procs: list[subprocess.Popen] = []

    def shutdown(*_args) -> None:  # noqa: ANN002, ANN003
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    os.chdir(ROOT)
    backend = subprocess.Popen(BACKEND_CMD, cwd=ROOT)
    frontend = subprocess.Popen(FRONTEND_CMD, cwd=ROOT / "frontend")
    procs = [backend, frontend]

    print("后端: http://127.0.0.1:8000")
    print("前端: http://127.0.0.1:5173")
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5173")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
