"""Agent 核心循环（练习 1.2、1.3）。

对应原书第一章“ReAct 循环”与“Harness 工程”，第二章“用代码实现 Agent 的核心循环”。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import messages as M
from .guard import Guard
from .tools import ToolRegistry


@dataclass
class AgentResult:
    answer: str | None
    messages: list[dict]
    stop_reason: str          # "done" | "max_iterations" | "circuit_open"
    iterations: int
    tool_calls: int = 0
    events: list[str] = field(default_factory=list)


def run_agent(
    llm,
    registry: ToolRegistry,
    user_message: str,
    *,
    system_prompt: str = "You are a helpful assistant.",
    history: list[dict] | None = None,
    max_iterations: int = 10,
    guard: Guard | None = None,
    before_call: Callable[[list[dict]], None] | None = None,
) -> AgentResult:
    """运行一次 ReAct 循环，直到模型不再调用工具，或触发停止条件。

    - messages 只追加、不改写：上下文 = 静态前缀（system + tools）+ 轨迹。
    - before_call(messages) 在每次调用模型前执行，可以往 messages 末尾追加内容
      （第二章的状态栏、压缩都挂在这里）。
    - guard 不为空时，每次工具调用先过护栏，失败计入熔断器（练习 1.3）。
    """
    messages: list[dict] = [M.system(system_prompt), *(history or []), M.user(user_message)]
    result = AgentResult(answer=None, messages=messages, stop_reason="max_iterations", iterations=0)

    # TODO 练习 1.2：实现 ReAct 循环
    # 提示：循环最多 max_iterations 次；每次先调用 before_call(messages)（如果有），
    # 提示：再 llm.complete(messages, registry.schemas())，把回复用 M.assistant(...) 追加进 messages。
    # 提示：回复里没有 tool_calls：把 content 记为 answer，stop_reason="done"，返回。
    # 提示：否则逐个执行工具调用：调用 _execute(...) 拿到结果文本，用 M.tool_result 追加，
    # 提示：tool_call_id 必须和调用的 id 一致。别忘了维护 iterations、tool_calls 计数。
    # 提示：循环跑满仍未结束：stop_reason 保持 "max_iterations"。
    raise NotImplementedError("练习 1.2 还没有完成：实现 ReAct 循环")


def _execute(registry: ToolRegistry, call, guard: Guard | None, result: AgentResult) -> str:
    """执行一次工具调用，永远返回字符串：错误也是给模型的观察，而不是让循环崩溃。"""
    if guard is not None:
        # TODO 练习 1.3b：把护栏接进循环
        # 提示：先 guard.check(call)：返回 (allowed, reason)。不允许时返回 "DENIED: " + reason，不执行工具。
        # 提示：允许时执行工具，成功调用 guard.record(True)，异常时 guard.record(False)。
        # 提示：错误文本的格式与下面无护栏时保持一致。
        raise NotImplementedError("练习 1.3b 还没有完成：把护栏接进循环")

    # TODO 练习 1.2b：把错误变成观察
    # 提示：调用 registry.execute(call)。未知工具、参数错误、工具内部异常都不能让循环崩溃：
    # 提示：捕获异常，返回 _error_text(call, exc)，让模型在下一轮看到发生了什么。
    raise NotImplementedError("练习 1.2b 还没有完成：把错误变成观察")


def _error_text(call, exc: Exception) -> str:
    """详细错误信息：类型、参数、提示。原书实验 2-9 发现这类信息能显著提高恢复成功率。"""
    return f"ERROR: {type(exc).__name__}: {exc} | tool={call.name} arguments={call.arguments}"
