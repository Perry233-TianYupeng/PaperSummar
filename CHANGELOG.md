# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 与 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-08-23

### 新增
- 论文资料卡完整管理：新建 / 打开 / 编辑 / 保存 / 删除
- 13 个卡片字段：题目、Arxiv ID、作者、团队信息、研究方向、首发时间、期刊/会议、内容、创新点、代码仓库、个人感想、AI 总结
- AI 联网补全（arXiv API + DuckDuckGo + LLM），严格只填充未填字段
- AI 总结，写入「AI 总结」字段
- Markdown 导出，首行标注 `# 卡片ID`
- 按题目 / 作者 / 内容三种模式搜索
- 黑白双主题切换
- 任务进度条与日志（`data/logs/`）
- 个人设置：名称、API Key、Base URL、模型、数据路径、主题
- 一键启动脚本（Windows / macOS / Linux）与 CI / Release 工作流

### 改进
- 启动脚本重构：`start.bat` / `start.ps1` / `start.sh` 只负责 Python 探测，安装与启动逻辑统一在 `scripts/launch.py`（三平台共用；自动跳过已完成的安装步骤，秒开）
- Python 探测自动跳过 Microsoft Store 占位 python，支持 `PAPERSUMMAR_PYTHON` 环境变量覆盖
- LLM 错误处理：401 认证失败 / 429 限流转换为友好中文提示并写入日志，避免无效重试
- 数据保存路径支持相对路径（以项目根为基准），项目内部绝对路径保存时自动相对化，剪切 / 移动项目文件夹后数据不丢失
- AI 功能启用规则：需填写真实论文题目（排除默认占位标题）并首次确认「保存修改」后才会启用，前后端双重校验
- 联网搜索改为**三级自动优先级**：Tavily（填 Key 优先）→ DeepSeek 内置联网搜索（LLM 为 DeepSeek 时自动启用）→ DuckDuckGo（免费兜底），显著改善论文信息补全质量
- AI 任务串行执行（一次一个），避免并发调用不同搜索 C 库导致的进程崩溃
- AI 补全 / 总结完成后自动刷新卡片草稿（无未保存修改时同步显示结果；用户编辑中则不覆盖）
