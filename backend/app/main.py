"""FastAPI 应用工厂与入口。

- 启动时初始化日志、解析数据目录、建立 TaskManager
- 生产模式托管 frontend/dist 静态文件（同源，无 CORS）
- 开发模式由 Vite dev server + proxy 转发 /api
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import SettingsManager
from .routes import ai, cards
from .routes import settings as settings_route
from .routes import tasks as tasks_route
from .store import CardStore
from .tasks import TaskManager
from .utils.logging_setup import setup_logging

APP_ROOT = Path(__file__).resolve().parents[2]  # 项目根目录
DIST_DIR = APP_ROOT / "frontend" / "dist"


class AppContext:
    """运行时的共享单例容器。"""

    def __init__(self, app_root: Path) -> None:
        self.app_root = Path(app_root)
        self.config_file = self.app_root / "data" / "config.json"
        self.settings = SettingsManager(self.config_file, self.app_root)
        self.task_manager: TaskManager | None = None
        self._store_cache: dict[str, CardStore] = {}

    def ensure_dirs(self) -> None:
        data_dir = self.settings.resolve_data_dir(self.settings.load().data_dir)
        for sub in ("cards", "exports", "logs"):
            (data_dir / sub).mkdir(parents=True, exist_ok=True)

    def get_store(self) -> CardStore:
        data_dir = self.settings.resolve_data_dir(self.settings.load().data_dir)
        key = str(data_dir)
        store = self._store_cache.get(key)
        if store is None:
            store = CardStore(data_dir)
            self._store_cache[key] = store
        return store

    def get_task_manager(self) -> TaskManager:
        if self.task_manager is None:
            self.task_manager = TaskManager(self._logs_dir_provider)
        return self.task_manager

    def _logs_dir_provider(self) -> Path:
        data_dir = self.settings.resolve_data_dir(self.settings.load().data_dir)
        return data_dir / "logs"


# 模块级共享上下文（路由经局部导入访问）
_ctx: AppContext | None = None


def get_store() -> CardStore:
    if _ctx is None:
        raise RuntimeError("应用尚未初始化")
    return _ctx.get_store()


def get_settings_manager() -> SettingsManager:
    if _ctx is None:
        raise RuntimeError("应用尚未初始化")
    return _ctx.settings


def get_task_manager() -> TaskManager:
    if _ctx is None:
        raise RuntimeError("应用尚未初始化")
    return _ctx.get_task_manager()


def create_app(app_root: Path = APP_ROOT) -> FastAPI:
    """创建 FastAPI 应用。app_root 可覆盖（测试时用临时目录）。"""
    global _ctx
    _ctx = AppContext(app_root)
    ctx = _ctx

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        data_dir = ctx.settings.resolve_data_dir(ctx.settings.load().data_dir)
        logger = setup_logging(data_dir)
        ctx.ensure_dirs()
        logger.info("PaperSummar 启动，数据目录：%s", data_dir)
        yield

    app = FastAPI(title="PaperSummar", version="0.1.0", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(cards.router)
    app.include_router(ai.router)
    app.include_router(tasks_route.router)
    app.include_router(settings_route.router)

    # 生产模式静态托管（同源，无需 CORS）
    if DIST_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(DIST_DIR / "index.html")

        @app.get("/favicon.svg")
        def favicon() -> FileResponse:
            return FileResponse(DIST_DIR / "favicon.svg")

        @app.get("/{path:path}")
        def spa_fallback(path: str) -> FileResponse:
            """SPA 深链回退：非 /api 路径统一返回 index.html。"""
            candidate = DIST_DIR / path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(DIST_DIR / "index.html")

    return app


app = create_app()


def run() -> None:
    """console_scripts 入口：uvicorn 启动。"""
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, app_dir=str(APP_ROOT / "backend"))


if __name__ == "__main__":
    run()
