"""上下文压缩：阈值触发的批量压缩（练习 2.4b）。

对应原书第二章“上下文压缩策略”与实验 2-10 的策略六“自适应窗口化”：
平时不压，提示词超过预算的 80% 时，一次性压缩所有尚未压缩的工具结果，并打上标记防止重复处理。
"""
from __future__ import annotations

from typing import Callable

from .context import serialize, tokenize

MARKER = "[COMPRESSED]"


def count_tokens(messages: list[dict]) -> int:
    return len(tokenize(serialize(messages)))


def compress_if_needed(
    messages: list[dict],
    budget: int,
    summarize: Callable[[str], str],
    *,
    threshold: float = 0.8,
    min_chars: int = 200,
    count: Callable[[list[dict]], int] = count_tokens,
) -> tuple[list[dict], int]:
    """返回 (新的消息列表, 本次压缩的条数)。规则：

    1. count(messages) <= budget * threshold 时什么也不做，原样返回（同一个列表对象）和 0。
    2. 否则，对每条 role == "tool"、content 不以 MARKER 开头、且长度 >= min_chars 的消息，
       把 content 换成 f"{MARKER} " + summarize(原内容)。
    3. 不修改 system / user / assistant 消息，不改变消息顺序，tool_call_id 保持不变。
    4. 不能原地修改传入的 messages 或其中的 dict：返回新列表，被压缩的消息是新 dict。
    """
    # >>> EXERCISE 2.4b 阈值触发的批量压缩
    # HINT: 用 {**m, "content": ...} 生成新 dict；未改动的消息可以直接复用原对象。
    if count(messages) <= budget * threshold:
        return messages, 0
    out: list[dict] = []
    n = 0
    for m in messages:
        content = m.get("content") or ""
        if m["role"] == "tool" and not content.startswith(MARKER) and len(content) >= min_chars:
            out.append({**m, "content": f"{MARKER} {summarize(content)}"})
            n += 1
        else:
            out.append(m)
    return out, n
    # <<< EXERCISE
