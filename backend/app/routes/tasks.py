"""任务状态查询路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import Task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_manager():
    from ..main import get_task_manager  # 局部导入避免循环

    return get_task_manager()


@router.get("")
def list_tasks(limit: int = 20) -> list[Task]:
    return _get_manager().list(limit=limit)


@router.get("/{task_id}")
def get_task(task_id: str) -> Task:
    task = _get_manager().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在或已失效：{task_id}")
    return task
