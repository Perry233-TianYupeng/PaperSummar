"""从 LLM 输出中稳健提取 JSON。

LLM 输出可能带有 ```json 围栏、前后解释文字、多个花括号嵌套，
这里通过定位最外层大括号对来提取，避免直接 ``json.loads`` 因杂质失败。
"""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """从任意文本中提取第一个 JSON 对象并解析。

    依次尝试：
    1. 去掉 markdown ```json 围栏后再整体 json.loads；
    2. 去掉围栏后直接 json.loads；
    3. 定位最外层花括号对截取后 json.loads。
    """
    if not text:
        raise ValueError("LLM 返回内容为空，无法提取 JSON")

    # 1) 围栏包裹的情况
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 2) 全量直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 3) 定位最外层花括号
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM 返回内容中未找到 JSON 对象")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    raise ValueError("找到的 JSON 片段无法解析") from None
    raise ValueError("LLM 返回内容的括号未闭合，无法提取 JSON")
