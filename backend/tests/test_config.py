"""config.py 单元测试：相对路径支持、自动相对化、剪切文件夹后数据跟随。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.config import SettingsManager  # noqa: E402
from app.models import Settings  # noqa: E402


def make_manager(app_root: Path) -> SettingsManager:
    return SettingsManager(app_root / "config.json", app_root)


class TestResolveDataDir:
    def test_empty_uses_default(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        assert m.resolve_data_dir("") == tmp_path / "data"

    def test_relative_resolved_against_app_root(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        assert m.resolve_data_dir("data") == tmp_path / "data"
        assert m.resolve_data_dir("mydata") == tmp_path / "mydata"
        assert m.resolve_data_dir("./data") == tmp_path / "data"
        assert m.resolve_data_dir("sub/dir") == tmp_path / "sub" / "dir"

    def test_absolute_kept_as_is(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        assert m.resolve_data_dir("D:/mydata") == Path("D:/mydata")


class TestToPublic:
    def test_returns_stored_relative_value(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        s = Settings(data_dir="data")
        assert m.to_public(s)["data_dir"] == "data"  # 相对路径原样返回，不解析成绝对

    def test_empty_returns_default_name(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        assert m.to_public(Settings(data_dir=""))["data_dir"] == "data"

    def test_absolute_stored_value_returned(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        s = Settings(data_dir="D:/mydata")
        assert m.to_public(s)["data_dir"] == "D:/mydata"


class TestNormalizeDataDir:
    def test_project_internal_absolute_becomes_relative(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        s = Settings(data_dir=str(tmp_path / "data"))
        m.normalize_data_dir(s)
        assert s.data_dir == "data"  # 项目内绝对路径 → 相对

    def test_project_internal_nested_absolute_becomes_relative(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        s = Settings(data_dir=str(tmp_path / "my" / "data"))
        m.normalize_data_dir(s)
        assert s.data_dir == "my/data"  # 正斜杠，跨平台安全

    def test_external_absolute_kept(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        s = Settings(data_dir="D:/mydata")
        m.normalize_data_dir(s)
        assert s.data_dir == "D:/mydata"  # 项目外绝对路径保留

    def test_relative_kept(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        s = Settings(data_dir="data")
        m.normalize_data_dir(s)
        assert s.data_dir == "data"


class TestSaveStoresRelative:
    def test_save_persists_relative_path(self, tmp_path: Path) -> None:
        m = make_manager(tmp_path)
        # 模拟旧版本存的是项目内绝对路径
        s = Settings(data_dir=str(tmp_path / "data"))
        m.save(s)
        # 落盘后应该是相对路径
        assert m.load().data_dir == "data"


class TestMoveFolderDataFollows:
    def test_data_dir_survives_moving_app_root(self, tmp_path: Path) -> None:
        """模拟剪切项目文件夹：config 存相对路径，换个新根目录后仍能解析到对应位置。"""
        old_root = tmp_path / "old_project"
        new_root = tmp_path / "new_project"
        old_root.mkdir()
        new_root.mkdir()

        # 在原项目保存相对路径配置
        m1 = make_manager(old_root)
        m1.save(Settings(data_dir="data"))
        assert m1.load().data_dir == "data"

        # 剪切到新位置：用同一份 config.json 内容在新根目录解析
        m2 = make_manager(new_root)
        assert m2.resolve_data_dir(m1.load().data_dir) == new_root / "data"
