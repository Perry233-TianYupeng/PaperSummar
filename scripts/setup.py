"""项目安装助手：安装后端依赖 + 构建前端。

用法：
    python scripts/setup.py            # 后端 + 前端（无 dist 时）
    python scripts/setup.py --backend  # 仅后端
    python scripts/setup.py --frontend # 仅前端（含 build）

start.bat / start.ps1 / start.sh 内部也调用本脚本完成环境准备。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(">>>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def setup_backend() -> None:
    print("[backend] 安装 Python 依赖 ...")
    run([sys.executable, "-m", "pip", "install", "-e", "."])


def setup_frontend(force: bool = False) -> None:
    dist = ROOT / "frontend" / "dist"
    if not force and dist.is_dir():
        print("[frontend] 已存在 frontend/dist，跳过构建（使用 --force 强制重建）")
        return
    print("[frontend] 安装 npm 依赖 ...")
    run(["npm", "install"], ROOT / "frontend")
    print("[frontend] 构建 ...")
    run(["npm", "run", "build"], ROOT / "frontend")


def main() -> None:
    args = sys.argv[1:]
    if "--backend" in args:
        setup_backend()
    elif "--frontend" in args:
        setup_frontend(force="--force" in args)
    else:
        setup_backend()
        setup_frontend(force="--force" in args)
    print("完成。启动：python -m uvicorn app.main:app")
    print("        --host 127.0.0.1 --port 8000 --app-dir backend")


if __name__ == "__main__":
    main()
