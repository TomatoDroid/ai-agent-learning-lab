"""模型接口。

- ScriptedLLM：按剧本返回回复的假模型。测试和离线演示都用它，不需要 API Key。
  它会记录每次收到的完整消息列表，方便验证“API 无状态、每次都要送回全部历史”。
- OpenAICompatLLM：调用任何 OpenAI 兼容的 Chat Completions 接口（Kimi、GLM、DeepSeek、
  OpenRouter、本地 vLLM/Ollama 等），只用标准库。

（本文件无练习，直接使用。）
"""
from __future__ import annotations

import copy
import json
import os
import urllib.request
from dataclasses import dataclass, field

from .messages import ToolCall


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: str | None = None
    usage: dict = field(default_factory=dict)


class ScriptedLLM:
    """按顺序返回预先写好的回复。剧本用完后抛出异常，避免测试悄悄死循环。"""

    def __init__(self, script: list[LLMResponse]):
        self.script = list(script)
        self.calls: list[dict] = []  # 每次调用收到的 {"messages":…, "tools":…} 深拷贝

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        self.calls.append({"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)})
        if not self.script:
            raise RuntimeError("ScriptedLLM 的剧本已经用完：Agent 调用模型的次数比预期多")
        return self.script.pop(0)


def say(text: str, reasoning: str | None = None) -> LLMResponse:
    """剧本里的一句最终回复。"""
    return LLMResponse(content=text, reasoning=reasoning)


def call(tool: str, call_id: str | None = None, /, **arguments) -> LLMResponse:
    """剧本里的一次工具调用：call("get_weather", "c1", city="温哥华")。"""
    return LLMResponse(tool_calls=[ToolCall(id=call_id or f"call_{tool}", name=tool, arguments=arguments)])


def calls(*tool_calls: ToolCall, reasoning: str | None = None) -> LLMResponse:
    """剧本里的一次并行工具调用。"""
    return LLMResponse(tool_calls=list(tool_calls), reasoning=reasoning)


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAICompatLLM":
        try:
            return cls(
                base_url=os.environ["MINI_AGENT_BASE_URL"],
                api_key=os.environ["MINI_AGENT_API_KEY"],
                model=os.environ["MINI_AGENT_MODEL"],
            )
        except KeyError as missing:
            raise SystemExit(f"缺少环境变量 {missing}。参见 mini-agent/README.md 的“接入真实模型”。") from None

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        body: dict = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        msg = data["choices"][0]["message"]
        return LLMResponse(
            content=msg.get("content"),
            tool_calls=[ToolCall.from_api(c) for c in msg.get("tool_calls") or []],
            reasoning=msg.get("reasoning_content") or msg.get("reasoning"),
            usage=data.get("usage", {}),
        )
