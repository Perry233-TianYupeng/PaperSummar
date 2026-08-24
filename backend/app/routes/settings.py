"""个人设置路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import Settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_manager():
    from ..main import get_settings_manager  # 局部导入避免循环

    return get_settings_manager()


@router.get("")
def get_settings() -> dict[str, str]:
    """返回设置，api_key 做掩码。"""
    manager = _get_manager()
    settings = manager.load()
    return manager.to_public(settings)


@router.put("")
def update_settings(body: Settings) -> dict[str, str]:
    """保存设置。data_dir 变更时尝试迁移旧数据。"""
    manager = _get_manager()
    current = manager.load()

    # 校验并迁移数据目录（仅在用户显式修改 data_dir 时）
    new_data_dir = body.data_dir.strip()
    old_data_dir = current.data_dir.strip()
    if new_data_dir and new_data_dir != old_data_dir:
        try:
            manager.apply_data_dir_change(new_data_dir, current)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # api_key / search_api_key 支持“留空表示不修改”：前端传掩码时此处应传空以保留原 key
    if not body.api_key.strip():
        body.api_key = current.api_key
    if not body.search_api_key.strip():
        body.search_api_key = current.search_api_key

    manager.save(body)
    return manager.to_public(body)
