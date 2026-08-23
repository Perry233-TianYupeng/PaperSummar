"""One-command launcher core (shared by start.bat / start.ps1 / start.sh).

负责：创建 venv → 安装后端依赖 → 构建前端（如需要）→ 打开浏览器 → 启动服务。
把复杂逻辑放在 Python 中，避免各平台 shell 的解析陷阱。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable  # 调用本脚本的 python
PORT = 8000
URL = f"http://127.0.0.1:{PORT}"


def fail(msg: str) -> int:
    print(f"[ERROR] {msg}")
    input("Press Enter to exit ...") if os.name == "nt" else None
    return 1


def step(num: str, msg: str) -> None:
    print(f"[{num}] {msg}")


def venv_python() -> Path:
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def main() -> int:
    vpy = venv_python()

    # ---- 1. 虚拟环境 ----
    if not vpy.exists():
        step("2/4", "Creating virtual environment ...")
        r = subprocess.run([PY, "-m", "venv", str(ROOT / ".venv")])
        if r.returncode != 0 or not vpy.exists():
            return fail("venv creation failed. Is Python installed correctly?")

    # ---- 2. 后端依赖（带标记，已装则跳过）----
    marker = ROOT / ".venv" / ".papersummar_ready"
    if not marker.exists():
        step("3/4", "Installing backend dependencies ...")
        r = subprocess.run([str(vpy), "-m", "pip", "install", "-e", str(ROOT)])
        if r.returncode != 0:
            return fail("backend dependency install failed. It needs Python 3.11+.")
        marker.write_text("ok", encoding="utf-8")

    # ---- 3. 前端构建（如缺 dist）----
    dist = ROOT / "frontend" / "dist"
    if not dist.is_dir():
        npm = shutil.which("npm")
        if not npm:
            return fail(
                "npm not found. Install Node.js 20+ and re-run, "
                "or download a Release package that already includes frontend/dist."
            )
        step("4/4", "Building frontend (first run only, may take a while) ...")
        try:
            subprocess.check_call("npm install", shell=True, cwd=str(ROOT / "frontend"))
            subprocess.check_call("npm run build", shell=True, cwd=str(ROOT / "frontend"))
        except subprocess.CalledProcessError:
            return fail("frontend build failed. See messages above.")

    # ---- 4. 启动 ----
    step("4/4", f"Launching ... open {URL} in your browser")
    threading.Timer(1.5, webbrowser.open, args=[URL]).start()
    cmd = [
        str(vpy),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
        "--app-dir",
        str(ROOT / "backend"),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
