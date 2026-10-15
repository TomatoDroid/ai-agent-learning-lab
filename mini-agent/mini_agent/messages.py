"""消息与工具调用的数据结构。

消息统一使用 OpenAI Chat Completions 风格的 dict，这样同一份轨迹可以直接发给任何
OpenAI 兼容接口，也方便在测试里逐字比较。（本文件无练习，直接使用。）
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_api(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": json.dumps(self.arguments, ensure_ascii=False)},
        }

    @classmethod
    def from_api(cls, raw: dict) -> "ToolCall":
        fn = raw["function"]
        args = fn.get("arguments") or "{}"
        try:
            parsed = json.loads(args) if isinstance(args, str) else dict(args)
        except json.JSONDecodeError:
            # 模型偶尔会给出不合法的 JSON。保留原文，交给工具执行时报错，而不是在这里崩溃。
            parsed = {"__raw__": args}
        return cls(id=raw.get("id", ""), name=fn["name"], arguments=parsed)


def system(content: str) -> dict:
    return {"role": "system", "content": content}


def user(content: str) -> dict:
    return {"role": "user", "content": content}


def assistant(content: str | None = None, tool_calls: list[ToolCall] | None = None, reasoning: str | None = None) -> dict:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if reasoning:
        msg["reasoning_content"] = reasoning
    if tool_calls:
        msg["tool_calls"] = [c.to_api() for c in tool_calls]
    return msg


def tool_result(tool_call_id: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def tool_calls_of(message: dict) -> list[ToolCall]:
    return [ToolCall.from_api(c) for c in message.get("tool_calls") or []]
