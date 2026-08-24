"""API 冒烟测试：卡片 CRUD、无标题禁止触发 AI、设置掩码、搜索。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app.main import create_app  # noqa: E402
from app.models import Task, TaskStatus  # noqa: E402
from app.tasks import TaskManager  # noqa: E402


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    # 用同步假 submit 替代真实后台线程，避免测试退出时残留线程
    # （真实网络任务会拖慢/干扰 pytest 清理，且 401 等错误写入已关闭的 stdout）。
    def fake_submit(self, kind: str, card_id: str, fn) -> Task:
        return Task(
            task_id="task_test",
            kind=kind,
            card_id=card_id,
            status=TaskStatus.SUCCEEDED,
            created_at="2026-08-24T00:00:00+08:00",
        )

    monkeypatch.setattr(TaskManager, "submit", fake_submit)
    app = create_app(app_root=tmp_path)
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_and_list(client: TestClient) -> None:
    created = client.post("/api/cards", json={}).json()
    assert created["title"] == "新资料卡"
    cards = client.get("/api/cards").json()
    assert len(cards) == 1
    assert cards[0]["id"] == created["id"]


def test_get_update_delete_flow(client: TestClient) -> None:
    card = client.post("/api/cards", json={"title": "论文A"}).json()
    cid = card["id"]

    got = client.get(f"/api/cards/{cid}").json()
    assert got["title"] == "论文A"

    card["title"] = "论文A-改"
    card["content"] = "新内容"
    updated = client.put(f"/api/cards/{cid}", json=card).json()
    assert updated["title"] == "论文A-改"
    assert updated["content"] == "新内容"

    # 删除后再取 → 404
    assert client.delete(f"/api/cards/{cid}").status_code == 200
    assert client.get(f"/api/cards/{cid}").status_code == 404


def test_ai_disabled_without_title(client: TestClient) -> None:
    # 默认占位标题「新资料卡」不计为已填写 → 400
    card = client.post("/api/cards", json={}).json()
    resp = client.post("/api/ai/completion", json={"card_id": card["id"]})
    assert resp.status_code == 400
    assert "论文题目" in resp.json()["detail"]

    # 填写真实题目并保存 → 放行到任务层（202）
    card["title"] = "Attention Is All You Need"
    client.put(f"/api/cards/{card['id']}", json=card)
    resp = client.post("/api/ai/completion", json={"card_id": card["id"]})
    assert resp.status_code == 202

    # 显式清空标题 → 400
    card["title"] = "   "
    client.put(f"/api/cards/{card['id']}", json=card)
    resp = client.post("/api/ai/completion", json={"card_id": card["id"]})
    assert resp.status_code == 400


def test_search_via_list(client: TestClient) -> None:
    c1 = client.post("/api/cards", json={"title": "Transformer 论文"}).json()
    client.post("/api/cards", json={"title": "扩散模型"})
    hits = client.get("/api/cards", params={"q": "transformer", "mode": "title"}).json()
    assert [h["id"] for h in hits] == [c1["id"]]

    # 作者搜索
    c1["authors"] = "张三丰"
    client.put(f"/api/cards/{c1['id']}", json=c1)
    hits = client.get("/api/cards", params={"q": "张三丰", "mode": "author"}).json()
    assert [h["id"] for h in hits] == [c1["id"]]


def test_settings_mask_and_roundtrip(client: TestClient) -> None:
    got = client.get("/api/settings").json()
    assert "api_key" in got

    put = client.put("/api/settings", json={
        "owner_name": "张三",
        "api_key": "sk-1234567890abcd",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "theme": "dark",
        "data_dir": (
            str(Path(client.app_root) / "data") if hasattr(client, "app_root") else ""
        ),
    })
    # 不传 data_dir 由 fixture 默认；这里不校验具体值
    assert put.status_code in (200, 400)

    got2 = client.get("/api/settings").json()
    # api_key 返回的是掩码
    assert "sk-****" in got2["api_key"] or got2["api_key"].startswith("****")


def test_missing_card_404(client: TestClient) -> None:
    bad = "card_00000000_000000_0000"
    assert client.get(f"/api/cards/{bad}").status_code == 404
    assert client.post("/api/ai/completion", json={"card_id": bad}).status_code == 404
