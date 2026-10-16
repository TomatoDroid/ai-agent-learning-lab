"""异步与事件驱动：事件路由、批量事件的呈现、打断时的占位符（练习 6.1）。

对应原书第六章“异步与事件驱动：当世界主动找上门”。
前五章的 Agent 是回合制的：用户说一句，Agent 想一段、调几个工具、回一句，期间世界被当成静止的。
这里把所有输入（用户消息、工具结果、定时器、外部回调）统一建模为事件，用一个事件循环驱动 Agent：

- 取消式：紧急事件“提前制造一个安全点”，打断当前步骤；
- 队列式：常规事件等到下一个自然的安全点（工具返回）再一起追加；
- 并行式：与主任务无关的轻量查询，另起一个会话立即回答。

EventLoopAgent 用的是“兼容同步接口”的路线：模型看到的始终是配对完好的标准轨迹，
只有打断时才为没跑完的工具插入明确的占位符，真实结果到达后作为带任务 ID 的新事件送回。
"""
from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from typing import Callable

from . import messages as M
from .messages import ToolCall, tool_calls_of
from .tools import ToolRegistry

URGENT_KINDS = {"user.interrupt", "supervisor.instruction", "agent.interrupt"}


@dataclass
class Event:
    """结构化事件：谁（source）、什么类型（kind）、内容、属于哪个任务、紧急程度。

    kind 例子：user.input、user.interrupt（用户点了“停止”）、supervisor.instruction、tool.result、
    timer.trigger、system.alert、email.received。priority：low / normal / urgent。
    independent=True 表示与主任务无关的轻量查询（“今天天气怎么样？”）。
    """
    kind: str
    content: str
    source: str = "user"
    task_id: str | None = None
    priority: str = "normal"
    independent: bool = False


def route(event: Event) -> str:
    """决定一个事件的处理策略，返回 "cancel"、"parallel" 或 "queue"。

    - kind 在 URGENT_KINDS 里，或 priority == "urgent" → "cancel"（取消式）
    - 否则，kind 以 "user." 开头且 independent 为真 → "parallel"（并行式）
    - 其余 → "queue"（队列式）
    """
    # >>> EXERCISE 6.1a 按紧急度路由
    # HINT: 先判断紧急，再判断并行。工具结果、定时器、常规外部事件都走队列。
    if event.kind in URGENT_KINDS or event.priority == "urgent":
        return "cancel"
    if event.kind.startswith("user.") and event.independent:
        return "parallel"
    return "queue"
    # <<< EXERCISE


def llm_router(llm, fallback: Callable[[Event], str] = route) -> Callable[[Event], str]:
    """原书建议：用轻量级的分类 LLM 作为事件路由器。只给它结构化字段，输出不合法时退回规则。"""
    def router(event: Event) -> str:
        payload = json.dumps({"kind": event.kind, "source": event.source, "content": event.content}, ensure_ascii=False)
        reply = llm.complete([
            M.system("You route events for an assistant that may be busy with a long task. Answer with exactly one word: "
                     "cancel (urgent: stop or redirect the current work now), parallel (an unrelated quick question), "
                     "or queue (handle at the next natural pause)."),
            M.user(payload),
        ]).content or ""
        word = reply.strip().lower()
        return word if word in {"cancel", "parallel", "queue"} else fallback(event)
    return router


def format_event(event: Event) -> str:
    """一个事件在轨迹里的样子。来源和任务 ID 都要写清楚，模型才不会把工具结果当成用户指令。"""
    if event.kind == "tool.result":
        head = f"Tool result from {event.source}（任务 {event.task_id}）" if event.task_id else f"Tool result from {event.source}"
    elif event.kind.startswith("user."):
        head = "User"
    elif event.kind.startswith(("timer.", "system.", "supervisor.")):
        head = "系统提醒"
    else:
        head = f"{event.kind} from {event.source}"
    return f"{head}：{event.content}"


_CATEGORIES = [("tool", "个工具结果"), ("user", "条用户消息"), ("system", "个系统提醒"), ("other", "个其他事件")]


def _category(event: Event) -> str:
    if event.kind == "tool.result":
        return "tool"
    if event.kind.startswith("user."):
        return "user"
    if event.kind.startswith(("timer.", "system.", "supervisor.")):
        return "system"
    return "other"


def render_events(events: list[Event]) -> str:
    """把一批事件渲染成一条消息（原书“Agent 状态栏标记”）。

    - 只有一个事件：直接返回 format_event(它)
    - 多个事件：每个一行 "[未处理事件 {i}/{n}] {format_event(e)}"，最后一行汇总：
      "上面有 {n} 个未处理事件，包括 {各类计数}。请确保回应涵盖所有信息。"
      各类计数按 _CATEGORIES 的顺序，只列出现过的类别，用 "、" 连接，例如 "1 个工具结果、2 条用户消息"。
    """
    # >>> EXERCISE 6.1b 批量事件的标记与汇总
    # HINT: 用 _category(e) 给事件分类，计数后按 _CATEGORIES 的顺序拼出 f"{count} {unit}"。
    if len(events) == 1:
        return format_event(events[0])
    n = len(events)
    lines = [f"[未处理事件 {i}/{n}] {format_event(e)}" for i, e in enumerate(events, 1)]
    counts = {key: sum(1 for e in events if _category(e) == key) for key, _ in _CATEGORIES}
    parts = [f"{counts[key]} {unit}" for key, unit in _CATEGORIES if counts[key]]
    lines.append(f"上面有 {n} 个未处理事件，包括 {'、'.join(parts)}。请确保回应涵盖所有信息。")
    return "\n".join(lines)
    # <<< EXERCISE


def placeholder(call_id: str, cancelled: bool) -> str:
    if cancelled:
        return f"[任务 {call_id} 已被用户取消，没有结果]"
    return (f"[任务 {call_id} 仍在后台执行。请先处理新事件；真实结果会作为单独的事件到达，"
            f"在那之前不要假设它的结果]")


def interrupt(messages: list[dict], event_text: str, cancelled: bool = False) -> list[dict]:
    """打断（原书兼容方案的规则 3）：返回新轨迹，不修改传入的列表。

    找到最后一条 assistant 消息里的工具调用，其中在它之后还没有 tool 结果的，
    按调用顺序各补一条 tool 消息，内容为 placeholder(id, cancelled)；然后追加 M.user(event_text)。
    这样从模型的视角看，每个调用都有配对的结果，轨迹格式合法。
    """
    # >>> EXERCISE 6.1c 打断时的占位符
    # HINT: 从后往前找最后一条 role == "assistant" 的消息，它之后的 tool 消息就是已经返回的结果。
    out = list(messages)
    idx = max((i for i, m in enumerate(out) if m["role"] == "assistant"), default=None)
    if idx is not None:
        answered = {m.get("tool_call_id") for m in out[idx + 1:] if m["role"] == "tool"}
        for call in tool_calls_of(out[idx]):
            if call.id not in answered:
                out.append(M.tool_result(call.id, placeholder(call.id, cancelled)))
    out.append(M.user(event_text))
    return out
    # <<< EXERCISE


class EventLoopAgent:
    """一个长期运行的事件循环：取出事件 → 追加到轨迹 → 调用模型 → 执行工具 → 回到开头。

    工具函数可以是普通函数，也可以是 async 函数（耗时的后台任务）。
    post() 投递事件；run() 一直处理，直到队列为空且没有后台任务。
    outbox 是 Agent 对用户说过的话；log 记录每个事件被路由到哪种策略。
    """

    def __init__(self, llm, registry: ToolRegistry, system_prompt: str = "你是一个助理。", router: Callable[[Event], str] = route,
                 max_steps: int = 20):
        self.llm, self.registry, self.router, self.max_steps = llm, registry, router, max_steps
        self.messages: list[dict] = [M.system(system_prompt)]
        self.outbox: list[str] = []
        self.log: list[str] = []
        self.queue: asyncio.Queue[Event] = asyncio.Queue()
        self.background: dict[str, asyncio.Task] = {}   # 打断后仍在后台跑的工具：call_id → task
        self._held: list[Event] = []                    # 等安全点的常规事件

    def post(self, event: Event) -> None:
        self.queue.put_nowait(event)

    async def run(self) -> None:
        while self._held or not self.queue.empty() or self.background:
            batch, self._held = (self._held or [await self.queue.get()]), []
            while not self.queue.empty():
                batch.append(self.queue.get_nowait())
            await self._handle(batch)

    async def _handle(self, batch: list[Event]) -> None:
        for e in batch:   # 空闲时三种策略殊途同归：直接进入主轨迹。路由只在忙碌时（_wait_safe_point）起作用
            if e.kind != "tool.result":
                self._route(e)
        self.messages.append(M.user(render_events(batch)))
        await self._think()

    def _route(self, e: Event) -> str:
        strategy = self.router(e)
        self.log.append(f"{strategy}:{e.kind}")
        return strategy

    async def _think(self) -> None:
        for _ in range(self.max_steps):
            reply = self.llm.complete(self.messages, self.registry.schemas())
            self.messages.append(M.assistant(reply.content, reply.tool_calls or None, reply.reasoning))
            if not reply.tool_calls:
                if reply.content:
                    self.outbox.append(reply.content)
                return
            tasks = {c.id: asyncio.create_task(self._execute(c)) for c in reply.tool_calls}
            urgent, held = await self._wait_safe_point(tasks)
            if urgent is None:      # 自然的安全点：工具全部返回，顺便把排队的事件一起追加（规则 5）
                for c in reply.tool_calls:
                    self.messages.append(M.tool_result(c.id, tasks[c.id].result()))
                if held:
                    self.messages.append(M.user(render_events(held)))
                continue
            stop = urgent.kind == "user.interrupt"
            for c in reply.tool_calls:   # 提前制造的安全点：没跑完的工具要么取消，要么转入后台
                t = tasks[c.id]
                if t.done():
                    continue
                if stop:
                    t.cancel()
                else:
                    self.background[c.id] = t
                    t.add_done_callback(self._late(c))
            done = [c for c in reply.tool_calls if tasks[c.id].done() and not tasks[c.id].cancelled()]
            self.messages = interrupt(self.messages[:], "", stop)[:-1]  # 先补齐占位符
            for c in done:   # 已经返回的结果用真实内容，而不是占位符
                for m in self.messages:
                    if m["role"] == "tool" and m.get("tool_call_id") == c.id:
                        m["content"] = tasks[c.id].result()
            self.messages.append(M.user(render_events(held + [urgent])))
        self.outbox.append("（达到最大步数，停止）")

    async def _wait_safe_point(self, tasks: dict[str, asyncio.Task]) -> tuple[Event | None, list[Event]]:
        held: list[Event] = []
        while not all(t.done() for t in tasks.values()):
            getter = asyncio.ensure_future(self.queue.get())
            await asyncio.wait([*[t for t in tasks.values() if not t.done()], getter], return_when=asyncio.FIRST_COMPLETED)
            if not getter.done():
                getter.cancel()
                continue
            e = getter.result()
            strategy = "queue" if e.kind == "tool.result" else self._route(e)
            if strategy == "cancel":
                return e, held
            held.append(await self._side(e) if strategy == "parallel" else e)
        return None, held

    def _late(self, call: ToolCall):
        def done(task: asyncio.Task) -> None:
            self.background.pop(call.id, None)
            if not task.cancelled():
                self.post(Event("tool.result", task.result(), source=call.name, task_id=call.id))
        return done

    async def _execute(self, call: ToolCall) -> str:
        try:
            tool = self.registry.get(call.name)
            result = tool.fn(**call.arguments)
            if inspect.isawaitable(result):
                result = await result
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 —— 错误变成观察（1.2 课）
            return f"ERROR: {type(exc).__name__}: {exc}"
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

    async def _side(self, e: Event) -> Event:
        """并行式：另起一个会话回答，不碰主轨迹；回答直接给用户，再留一条记录等安全点并入主轨迹。"""
        msgs = [self.messages[0], M.user(e.content)]
        answer = "（并行会话没有给出回答）"
        for _ in range(self.max_steps):
            reply = self.llm.complete(msgs, self.registry.schemas())
            msgs.append(M.assistant(reply.content, reply.tool_calls or None))
            if not reply.tool_calls:
                answer = reply.content or answer
                break
            for c in reply.tool_calls:
                msgs.append(M.tool_result(c.id, await self._execute(c)))
        self.outbox.append(answer)
        return Event("parallel.note", f"用户问“{e.content}”，已在并行会话中回答：{answer}", source="parallel")
