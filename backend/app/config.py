"""设置管理：读写本地 config.json，路径解析，API key 掩码。"""
from __future__ import annotations

import shutil
from pathlib import Path

from .models import Settings
from .utils.atomic_io import atomic_write_json, read_json

DEFAULT_DATA_DIR_NAME = "data"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class SettingsManager:
    """负责 config.json 的读写与 data_dir 变更迁移。"""

    def __init__(self, config_file: Path, app_root: Path) -> None:
        self.config_file = Path(config_file)
        self.app_root = Path(app_root)

    # ---------- 路径 ----------

    def default_data_dir(self) -> Path:
        return self.app_root / DEFAULT_DATA_DIR_NAME

    def resolve_data_dir(self, data_dir: str | None = None) -> Path:
        """解析保存路径为绝对路径。空值回退到默认 <app_root>/data。"""
        raw = (data_dir or self.load().data_dir or "").strip()
        if not raw:
            return self.app_root / DEFAULT_DATA_DIR_NAME
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self.app_root / p
        return p

    # ---------- 读写 ----------

    def load(self) -> Settings:
        raw = read_json(self.config_file, default={})
        if not isinstance(raw, dict):
            raw = {}
        return Settings(**raw)

    def save(self, settings: Settings) -> Settings:
        settings = self.normalize_data_dir(settings)
        atomic_write_json(self.config_file, settings.model_dump())
        return settings

    def normalize_data_dir(self, settings: Settings) -> Settings:
        """保存前规范化 data_dir：把「项目内部的绝对路径」转为相对路径。

        这样用户剪切 / 移动整个项目文件夹后，相对路径仍然指向新位置的
        data 目录，数据不会因为旧绝对路径失效而"丢失"。项目外部的绝对
        路径（如 D:\\mydata）保持不变。
        """
        raw = settings.data_dir.strip()
        if not raw:
            return settings
        p = Path(raw).expanduser()
        if p.is_absolute():
            try:
                rel = p.relative_to(self.app_root)
            except ValueError:
                return settings  # 项目外绝对路径，保留原样
            rel_str = rel.as_posix()
            settings.data_dir = rel_str if rel_str != "." else DEFAULT_DATA_DIR_NAME
        return settings

    def to_public(self, settings: Settings) -> dict[str, str]:
        """返回给前端的设置，api_key 做掩码（sk-****后4位）。

        data_dir 返回**存储的原始值**（相对路径就显示相对路径），而不是解析后的
        绝对路径——这样前端保存时原样回传，config.json 保持相对路径，移动项目
        文件夹后数据依旧可用。
        """
        stored = settings.data_dir.strip()
        return {
            "owner_name": settings.owner_name,
            "api_key": mask_api_key(settings.api_key),
            "base_url": settings.base_url,
            "model": settings.model,
            "theme": settings.theme,
            "data_dir": stored or DEFAULT_DATA_DIR_NAME,
            "search_provider": settings.search_provider,
            "search_api_key": mask_api_key(settings.search_api_key),
        }

    # ---------- data_dir 变更迁移 ----------

    def apply_data_dir_change(self, new_dir: str, current: Settings) -> None:
        """将 data_dir 从 current 改为 new_dir：校验可写、建子目录、尽力迁移旧数据。"""
        new_path = self.resolve_data_dir(new_dir)
        old_path = self.resolve_data_dir(current.data_dir)

        try:
            for sub in ("cards", "exports", "logs"):
                (new_path / sub).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"无法在新路径下创建数据目录：{new_path}（{exc}）") from exc

        # 探测可写性
        probe = new_path / ".write_test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise ValueError(f"新路径不可写：{new_path}（{exc}）") from exc

        # 尽力迁移旧数据（源存在且不等于目标时才迁移）
        if old_path != new_path and old_path.exists():
            for sub in ("cards", "exports"):
                src = old_path / sub
                if src.exists():
                    try:
                        for item in src.iterdir():
                            if item.is_file():
                                shutil.copy2(item, new_path / sub / item.name)
                    except OSError as exc:
                        raise ValueError(f"迁移旧数据失败：{src}（{exc}）") from exc


def mask_api_key(key: str) -> str:
    """对 API key 做掩码：sk-****后4位；空串原样返回。"""
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return key[:3] + "****" + key[-4:]
