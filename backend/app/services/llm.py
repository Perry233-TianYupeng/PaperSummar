"""OpenAI 兼容 LLM 客户端。

支持自定义 base_url / api_key / model。优先尝试 ``response_format=json_object``，
中转服务拒绝（400/404/不支持）时自动降级为普通文本模式并做稳健 JSON 提取。
"""
from __future__ import annotations

from typing import Any

from ..utils.json_extract import extract_json
from ..utils.logging_setup import get_logger

# 防御性导入：openai 未安装时不阻塞其它模块
try:
    from openai import AuthenticationError, RateLimitError
except ImportError:  # pragma: no cover
    class AuthenticationError(Exception):  # type: ignore[no-redef]
        pass

    class RateLimitError(Exception):  # type: ignore[no-redef]
        pass

_logger = get_logger()

_SYSTEM_PROMPT = (
    "你是一个严谨的学术论文信息助手。只依据给定的资料回答，不编造不存在的客观事实；"
    "期刊/会议名称如不确定，请如实说明是推测。"
)

# 常见可诊断错误的友好提示
_AUTH_MSG = (
    "API Key 无效或已过期（认证失败 401）。"
    "请到「个人设置」检查 Base URL 与 API Key 是否正确、完整。"
)
_RATE_MSG = "请求被限流（429），可能是频率过高或账户余额不足，请稍后重试。"


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 60.0) -> None:
        if not api_key:
            raise ValueError("未配置 API Key，请先在「个人设置」中填写")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout)
        self.model = model or "gpt-4o-mini"

    def chat_json(
        self,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """调用模型并要求返回 JSON 对象；自动降级并稳健解析。"""
        try:
            return self._chat_json_strict(user_prompt, temperature)
        except AuthenticationError as exc:
            raise RuntimeError(_AUTH_MSG) from exc
        except RateLimitError as exc:
            raise RuntimeError(_RATE_MSG) from exc
        except Exception as exc:  # noqa: BLE001
            _logger.info("JSON 模式请求失败(%s)，降级为普通模式重试", exc)
            try:
                return self._chat_json_fallback(user_prompt, temperature)
            except AuthenticationError as exc2:
                raise RuntimeError(_AUTH_MSG) from exc2
            except RateLimitError as exc2:
                raise RuntimeError(_RATE_MSG) from exc2

    # ---------- 内部 ----------

    def _chat_json_strict(self, user_prompt: str, temperature: float) -> dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        return extract_json(content)

    def _chat_json_fallback(self, user_prompt: str, temperature: float) -> dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        content = resp.choices[0].message.content or ""
        return extract_json(content)
