"""原子化文件读写工具。

写文件时先写临时文件再 ``os.replace``，保证在 Windows / POSIX 上都是原子替换，
避免写了一半被其它线程或进程读到。
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子写入文本文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def atomic_write_json(path: Path, data: Any, encoding: str = "utf-8") -> None:
    """原子写入 JSON 文件（UTF-8，ensure_ascii=False 保留中文）。"""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    atomic_write_text(path, content, encoding=encoding)


def read_json(path: Path, default: Any = None, encoding: str = "utf-8") -> Any:
    """读取 JSON 文件；文件不存在返回 default，损坏时抛出异常由上层处理。"""
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding=encoding) as f:
        return json.load(f)
