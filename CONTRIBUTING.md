# 贡献指南

感谢你愿意为 PaperSummar 贡献代码！请花两分钟阅读以下约定。

## 环境要求

- Python 3.11+
- Node.js 20+
- 可选：DuckDuckGo 搜索需要能访问网络（arXiv 在国内可能较慢，属已知限制）

## 开发环境搭建

```bash
# 后端
python -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

# 前端
cd frontend && npm install && cd ..

# 开发模式（前后端热更新）
python scripts/dev.py
```

## 代码规范

- 后端使用 [Ruff](https://docs.astral.sh/ruff/)（`E,F,I,W,UP,B,SIM` 规则集）与 [Mypy](https://mypy.readthedocs.io/)。
- 前端使用 TypeScript `strict` 模式。

运行检查：

```bash
ruff check backend/
mypy backend/ --ignore-missing-imports
cd frontend && npm run typecheck
```

## 测试

```bash
pytest backend/tests
```

**特别要求**：任何对「AI 补全 / 合并」逻辑的改动，必须保证 `backend/tests/test_ai_pipeline.py` 继续通过 —— 该文件验证的是产品核心保证：**已填字段绝不被 AI 覆盖、个人感想永不参与补全**。

## 提交 PR

1. Fork 并创建分支：`git checkout -b feature/xxx`
2. 提交前请通过全部检查（上述 `ruff`、`mypy`、`pytest`、`typecheck`）
3. PR 描述请说明：改动内容、为什么改、如何验证
4. 新功能请附带对应的单元测试

## 版本与发布

- 版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。
- 每次改动更新 `CHANGELOG.md`。
- 打 Tag 触发 `release.yml`，自动构建并生成包含 `frontend/dist` 的 Release 包。
