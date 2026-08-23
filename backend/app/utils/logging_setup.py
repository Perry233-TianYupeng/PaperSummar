"""日志配置。

双 handler：
- StreamHandler：输出到 stdout，一键启动窗口可见；
- RotatingFileHandler：滚动写入 ``<data_dir>/logs/app.log``（UTF-8，1MB×3）。
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "papersummar"


def setup_logging(data_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """初始化全局 logger，返回主 logger。可重复调用（幂等）。"""
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:  # 已初始化过
        return logger

    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    log_dir = Path(data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
