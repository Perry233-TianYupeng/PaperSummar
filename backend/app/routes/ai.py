"""AI 触发路由：补全 / 总结 / md 导出。

三个接口统一「触发 → 返回 task_id」异步模型，前端轮询 /api/tasks/{id}。
规则：**未填写论文题目时禁用 AI 功能**（前端 disabled + 后端 400 双保险）。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import Task

router = APIRouter(prefix="/api/ai", tags=["ai"])


class TriggerBody(BaseModel):
    card_id: str


def _get_card(store, card_id):
    try:
        return store.get(card_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"资料卡不存在：{card_id}") from None


def _ensure_ready(card) -> None:
    """校验卡片存在且已填写题目。"""
    if not card.is_title_filled():
        raise HTTPException(status_code=400, detail="请先填写论文题目后再使用 AI 功能")


def _submit(kind: str, card_id: str, fn) -> Task:
    from ..main import get_task_manager  # 局部导入避免循环

    return get_task_manager().submit(kind, card_id, fn)


@router.post("/completion", status_code=202)
def trigger_completion(body: TriggerBody) -> Task:
    from ..main import get_settings_manager, get_store

    card = _get_card(get_store(), body.card_id)
    _ensure_ready(card)
    settings = get_settings_manager().load()
    data_dir = get_settings_manager().resolve_data_dir(settings.data_dir)

    from ..services.ai_pipeline import run_completion

    def fn(progress):
        return run_completion(card, settings, data_dir, progress)

    return _submit("ai_completion", card.id, fn)


@router.post("/summary", status_code=202)
def trigger_summary(body: TriggerBody) -> Task:
    from ..main import get_settings_manager, get_store

    card = _get_card(get_store(), body.card_id)
    _ensure_ready(card)
    settings = get_settings_manager().load()
    data_dir = get_settings_manager().resolve_data_dir(settings.data_dir)

    from ..services.ai_pipeline import run_summary

    def fn(progress):
        return run_summary(card, settings, data_dir, progress)

    return _submit("ai_summary", card.id, fn)


@router.post("/md-export", status_code=202)
def trigger_md_export(body: TriggerBody) -> Task:
    from ..main import get_settings_manager, get_store

    card = _get_card(get_store(), body.card_id)
    _ensure_ready(card)
    settings = get_settings_manager().load()
    exports_dir = get_settings_manager().resolve_data_dir(settings.data_dir) / "exports"

    from ..services.md_exporter import export_markdown

    def fn(progress):
        progress(0.3, "export", "正在渲染 Markdown ...")
        result = export_markdown(card, exports_dir)
        progress(1.0, "done", "导出完成")
        return result

    return _submit("md_export", card.id, fn)
