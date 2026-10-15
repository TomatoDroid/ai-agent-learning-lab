"""工具注册表。

工具 = 名称 + 描述 + 参数 schema + 执行函数 + 风险等级。模型只看到前三项；
执行函数和风险等级属于 Harness。（本文件无练习，直接使用。）
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .messages import ToolCall


class UnknownToolError(KeyError):
    pass


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]
    risk: str = "low"            # low / medium / high，见 1.3 课
    untrusted_output: bool = False  # 输出来自外部世界（网页、邮件…），见 2.3 课

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> Tool:
        self.tools[tool.name] = tool
        return tool

    def add(self, name: str, description: str, parameters: dict | None = None, risk: str = "low", untrusted_output: bool = False):
        """装饰器写法：@registry.add("get_weather", "查询天气", {...})"""
        def deco(fn):
            self.register(Tool(name, description, parameters or {"type": "object", "properties": {}}, fn, risk, untrusted_output))
            return fn
        return deco

    def get(self, name: str) -> Tool:
        if name not in self.tools:
            raise UnknownToolError(name)
        return self.tools[name]

    def schemas(self) -> list[dict]:
        # 顺序固定为注册顺序：工具定义是静态前缀的一部分，顺序一变缓存就失效（2.2 课）
        return [t.schema() for t in self.tools.values()]

    def execute(self, call: ToolCall) -> str:
        """执行一次工具调用并把结果转成字符串。

        未知工具抛 UnknownToolError，工具内部的异常原样抛出：
        如何把错误变成模型能看懂的观察，是 Agent 循环的职责（1.2 课练习）。
        """
        tool = self.get(call.name)
        result = tool.fn(**call.arguments)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)
