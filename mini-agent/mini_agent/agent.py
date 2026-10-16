"""把各课的零件装配成一个 Agent。（本文件无练习；随课程推进，这里会接入更多能力。）

装配顺序就是第二章的上下文布局：
  [system：系统提示词 + 用户记忆 + Skill 目录] [tools] [轨迹……] [状态栏（追加）]
每次调用模型前，before_call 依次：记录工具调用 → 追加已激活的 Skill 正文 → 必要时压缩 → 追加状态栏。
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from . import messages as M
from .compress import compress_if_needed
from .guard import Guard
from .injection import wrap_external
from .loop import AgentResult, run_agent
from .memory import MemoryStore
from .skills import activation_message, catalog_text, load_skills
from .status import StatusTracker
from .tools import Tool, ToolRegistry


class Agent:
    def __init__(
        self,
        llm,
        registry: ToolRegistry,
        system_prompt: str = "You are a helpful assistant. Use tools when you need real data.",
        *,
        guard: Guard | None = None,
        skills_dir: str | None = None,
        status: StatusTracker | None = None,
        clock: Callable[[], str] | None = None,
        budget: int | None = None,
        summarize: Callable[[str], str] | None = None,
        wrap_untrusted: bool = True,
        memory: MemoryStore | None = None,
        max_iterations: int = 20,
    ):
        self.llm = llm
        self.guard = guard
        self.status = status
        self.clock = clock
        self.budget = budget
        self.summarize = summarize or (lambda text: text[:200] + "…")
        self.max_iterations = max_iterations
        self.history: list[dict] = []
        self._pending: list[dict] = []
        self._seen_calls = 0

        # 2.3：外部世界来的工具输出，进入上下文前先包上来源标记
        self.registry = ToolRegistry()
        for tool in registry.tools.values():
            if wrap_untrusted and tool.untrusted_output:
                tool = replace(tool, fn=_wrapped(tool))
            self.registry.register(tool)

        # 2.4：Skill 目录放进系统提示词（静态前缀），正文由 load_skill 按需追加
        self.skills = load_skills(skills_dir) if skills_dir else {}
        self.system_prompt = system_prompt
        # 3.1：用户记忆在会话开始时渲染一次，整个会话内不变，属于静态前缀
        self.memory = memory
        if memory is not None and memory.render():
            self.system_prompt += "\n\n" + memory.render()
        if self.skills:
            self.system_prompt += "\n\n" + catalog_text(self.skills)
            self.registry.register(Tool(
                "load_skill", "Load the full instructions of a skill listed in the system prompt.",
                {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, self._load_skill))

    def _load_skill(self, name: str) -> str:
        if name not in self.skills:
            raise KeyError(f"没有名为 {name} 的 Skill。可用：{', '.join(self.skills)}")
        self._pending.append(activation_message(self.skills[name]))
        return f"Skill {name} loaded; its instructions follow."

    def _before_call(self, messages: list[dict]) -> None:
        if self.status is not None:
            calls = [c for m in messages if m["role"] == "assistant" for c in M.tool_calls_of(m)]
            for c in calls[self._seen_calls:]:
                self.status.record_call(c)
            self._seen_calls = len(calls)
        messages.extend(self._pending)
        self._pending.clear()
        if self.budget:
            new, _ = compress_if_needed(messages, self.budget, self.summarize)
            messages[:] = new
        if self.status is not None:
            messages.append(self.status.as_message(self.clock() if self.clock else None))

    def run(self, user_message: str) -> AgentResult:
        self._seen_calls = sum(len(M.tool_calls_of(m)) for m in self.history if m["role"] == "assistant")
        result = run_agent(
            self.llm, self.registry, user_message,
            system_prompt=self.system_prompt, history=self.history,
            max_iterations=self.max_iterations, guard=self.guard, before_call=self._before_call,
        )
        self.history = result.messages[1:]
        return result


def _wrapped(tool: Tool):
    def fn(**kwargs):
        out = tool.fn(**kwargs)
        return wrap_external(out if isinstance(out, str) else str(out), tool.name)
    return fn
