"""后台任务管理：内存任务表 + daemon 线程执行 + 进度回调 + 落盘日志。"""
from __future__ import annotations

import secrets
import threading
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Task, TaskStatus, now_iso
from .utils.logging_setup import get_logger

ProgressCallback = Callable[[float | None, str | None, str | None], None]


class TaskManager:
    """单机任务管理器。

    submit() 建任务并入队，起 daemon 线程执行 fn；fn 内通过 progress_cb 更新进度。
    内存保留最近 MAX_HISTORY 条记录供查询。失败信息写 tasks.log。
    """

    MAX_HISTORY = 50

    def __init__(self, logs_dir: Path | Callable[[], Path]) -> None:
        self._tasks: OrderedDict[str, Task] = OrderedDict()
        self._lock = threading.RLock()
        self._logs_dir = logs_dir  # Path 或返回 Path 的可调用对象
        self._logger = get_logger()

    def submit(
        self,
        kind: str,
        card_id: str,
        fn: Callable[[ProgressCallback], dict[str, Any] | None],
    ) -> Task:
        task = Task(
            task_id=self._new_task_id(),
            kind=kind,
            card_id=card_id,
            status=TaskStatus.QUEUED,
            created_at=now_iso(),
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._trim()

        def progress_cb(progress=None, stage=None, message=None) -> None:
            task.update(progress=progress, stage=stage, message=message)

        def run() -> None:
            task.status = TaskStatus.RUNNING
            try:
                result = fn(progress_cb)
                task.result = result or {}
                task.status = TaskStatus.SUCCEEDED
                task.update(progress=1.0, stage="done")
                self._logger.info("任务 %s(%s) 成功：%s", task.task_id, task.kind, task.card_id)
            except Exception as exc:  # noqa: BLE001 - 兜底记录一切失败
                task.status = TaskStatus.FAILED
                task.error = f"{exc}"
                self._logger.error(
                    "任务 %s(%s) 失败 card=%s：%s", task.task_id, task.kind, task.card_id, exc
                )
                self._write_tasks_log(task)
            finally:
                task.finished_at = now_iso()

        thread = threading.Thread(target=run, name=f"task-{task.task_id}", daemon=True)
        thread.start()
        return task

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self, limit: int = 20) -> list[Task]:
        with self._lock:
            items = list(self._tasks.values())[-limit:]
            return items[::-1]

    def _new_task_id(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"task_{stamp}_{secrets.token_hex(3)}"

    def _trim(self) -> None:
        while len(self._tasks) > self.MAX_HISTORY:
            self._tasks.popitem(last=False)

    def _write_tasks_log(self, task: Task) -> None:
        logs_dir = self._logs_dir() if callable(self._logs_dir) else self._logs_dir
        logs_dir = Path(logs_dir)
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            line = (
                f"{task.finished_at} | {task.task_id} | {task.kind} | "
                f"card={task.card_id} | status={task.status} | {task.error}\n"
            )
            with (logs_dir / "tasks.log").open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError as exc:
            self._logger.warning("写入 tasks.log 失败：%s", exc)
