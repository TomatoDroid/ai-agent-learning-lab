"""Agent 状态栏（练习 2.4a）。

对应原书第二章“Agent 状态栏”与实验 2-8、2-9：把散落在轨迹里的隐式状态（打了几次电话、
TODO 进行到哪）由代码提前算好，作为一条消息追加到上下文末尾。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .messages import ToolCall

TODO_STATES = ("pending", "in_progress", "completed", "cancelled")


@dataclass
class StatusTracker:
    limits: dict[str, int] = field(default_factory=dict)   # 工具名 -> 同一目标的调用上限
    target_arg: dict[str, str] = field(default_factory=dict)  # 工具名 -> 用哪个参数区分“目标”
    counts: Counter = field(default_factory=Counter)        # (工具名, 目标) -> 次数；目标为 None 表示不区分
    todos: list[dict] = field(default_factory=list)

    def record_call(self, call: ToolCall) -> None:
        """记录一次工具调用。对 target_arg 里配置过的工具，按目标分别计数。"""
        # >>> EXERCISE 2.4a 计数
        # HINT: key 的目标部分 = call.arguments.get(self.target_arg[call.name])（未配置时为 None）。
        target = call.arguments.get(self.target_arg[call.name]) if call.name in self.target_arg else None
        self.counts[(call.name, target)] += 1
        # <<< EXERCISE

    def set_todo(self, todo_id: str, content: str, status: str = "pending") -> None:
        if status not in TODO_STATES:
            raise ValueError(f"未知的 TODO 状态：{status}")
        for t in self.todos:
            if t["id"] == todo_id:
                t.update(content=content, status=status)
                return
        self.todos.append({"id": todo_id, "content": content, "status": status})

    def render(self, now: str | None = None) -> str:
        """生成状态栏文本。格式（每项一行，没有内容的段落整段省略）：

        <agent_status>
        time: {now}
        calls: phone_call[Xfinity] 3/3 LIMIT REACHED; web_search 2
        todo: [1] 取消套餐 (in_progress); [2] 发邮件确认 (pending)
        </agent_status>

        calls 按 (工具名, 目标) 排序（None 排在最前，用 str 比较即可）；有上限的写 “n/上限”，
        达到或超过上限时追加 “ LIMIT REACHED”；目标为 None 时不写方括号。
        """
        # >>> EXERCISE 2.4a 渲染
        # HINT: 排序可以用 sorted(self.counts.items(), key=lambda kv: (kv[0][0], str(kv[0][1] or "")))。
        lines = ["<agent_status>"]
        if now:
            lines.append(f"time: {now}")
        if self.counts:
            items = []
            for (name, target), n in sorted(self.counts.items(), key=lambda kv: (kv[0][0], str(kv[0][1] or ""))):
                label = f"{name}[{target}]" if target is not None else name
                if name in self.limits:
                    limit = self.limits[name]
                    items.append(f"{label} {n}/{limit}" + (" LIMIT REACHED" if n >= limit else ""))
                else:
                    items.append(f"{label} {n}")
            lines.append("calls: " + "; ".join(items))
        if self.todos:
            lines.append("todo: " + "; ".join(f"[{t['id']}] {t['content']} ({t['status']})" for t in self.todos))
        lines.append("</agent_status>")
        return "\n".join(lines)
        # <<< EXERCISE

    def as_message(self, now: str | None = None) -> dict:
        """状态栏借用 user 角色追加在末尾（书中图 2-15）。内容由框架生成，不是用户说的话。"""
        return {"role": "user", "content": self.render(now)}
