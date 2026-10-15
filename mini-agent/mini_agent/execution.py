"""感知与执行工具的工程细节：显式截断、Sidecar 门控、超时后的安全重试（练习 4.3）。

对应原书第四章“感知工具”“执行工具”：
- 读取类工具要支持 offset/limit，截断必须说出来；长输出只留头尾，全文落盘；
- Sidecar：一个只看结构化工具调用的旁路分类器，门控每一次工具调用；连续拒绝时转交人类；
- 执行工具超时后，副作用可能已经发生：先查询，再决定是否重试。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from .messages import ToolCall

DANGEROUS = [
    r"\brm\s+-[a-zA-Z]*(r[a-zA-Z]*f|f[a-zA-Z]*r)", r"\bdd\s+if=", r"curl[^|]*\|\s*(ba|z)?sh\b",
    r"\bmkfs\b", r">\s*/dev/sd", r"chmod\s+-R\s+777\s+/", r":\(\)\s*\{",
]

SIDECAR_PROMPT = (
    "You are a security classifier for an AI agent's tool calls. You see one tool call as JSON and nothing else. "
    "Reply ALLOW if it is safe to run, or DENY: <short reason> if it could destroy data, leak secrets, "
    "or affect systems outside the workspace."
)


def read_window(text: str, offset: int = 1, limit: int = 200) -> str:
    """读取类工具的 offset/limit：返回第 offset 行起的至多 limit 行，每行前加 "{行号}\\t"。

    - 空文本：返回 "[empty file]"
    - offset 超过总行数：返回 "[offset {offset} is past the end; the file has {total} lines]"
    - 只要没有显示全部内容（offset > 1，或后面还有行），在末尾另起一行写明：
      "[showing lines {a}-{b} of {total}; call again with offset={b + 1} to continue]"
      若已经到达末尾，则写 "[showing lines {a}-{b} of {total}; this is the end of the file]"
    行号从 1 开始；offset 小于 1 按 1 处理。永远不要静默截断。
    """
    # TODO 练习 4.3a：显式截断
    # 提示：lines = text.splitlines()；a = max(offset, 1)；b = min(a + limit - 1, total)。
    raise NotImplementedError("练习 4.3a 还没有完成：显式截断")


def clip_output(text: str, save: Callable[[str], str], max_lines: int = 200, head: int = 50, tail: int = 50) -> str:
    """执行类工具的长输出：不超过 max_lines 行原样返回；否则调用 save(text) 把全文落盘（返回路径），
    只保留前 head 行和后 tail 行，中间换成一行：
      "... [{省略行数} lines omitted; full output saved to {path}; use read_file to see it] ..."
    """
    # TODO 练习 4.3a：头尾保留 + 持久化
    # 提示：头部是错误上下文，尾部通常是最终的报错或成功标志，两头都要留。
    raise NotImplementedError("练习 4.3a 还没有完成：头尾保留 + 持久化")


def verify_python(content: str) -> str:
    """“执行-验证-反馈”闭环的最小例子：写入 .py 文件后立刻做语法检查，把结果作为工具返回值的一部分。"""
    try:
        compile(content, "<file>", "exec")
    except SyntaxError as exc:
        return f"syntax error at line {exc.lineno}: {exc.msg}"
    return "syntax OK"


# ───────────────────────── Sidecar ─────────────────────────

def sidecar_payload(call: ToolCall) -> dict:
    """Sidecar 只看结构化字段：工具名和参数。不看对话、不看主模型的思考，话术就进不来。"""
    return {"tool": call.name, "arguments": call.arguments}


def rule_classifier(payload: dict) -> tuple[str, str]:
    """最便宜的 Sidecar：正则。返回 ("allow", "") 或 ("deny", 原因)。"""
    text = json.dumps(payload, ensure_ascii=False)
    for p in DANGEROUS:
        if re.search(p, text):
            return "deny", f"matches dangerous pattern {p}"
    return "allow", ""


def llm_classifier(llm) -> Callable[[dict], tuple[str, str]]:
    """轻量模型做 Sidecar：一次独立调用，只送 SIDECAR_PROMPT 和这次调用的 JSON。"""
    def classify(payload: dict) -> tuple[str, str]:
        msgs = [{"role": "system", "content": SIDECAR_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
        reply = (llm.complete(msgs, None).content or "").strip()
        if reply.upper().startswith("ALLOW"):
            return "allow", ""
        return "deny", reply.partition(":")[2].strip() or reply or "no verdict"  # 看不懂的回复按拒绝处理
    return classify


@dataclass
class SidecarGuard:
    """与 1.3 的 Guard 接口相同（check / record / tripped），可以直接传给 run_agent 或 Agent。"""
    classifier: Callable[[dict], tuple[str, str]] = rule_classifier
    confirm: Callable[[ToolCall, str], bool] = lambda call, reason: False
    max_denials: int = 3
    max_consecutive_failures: int = 3
    consecutive_denials: int = 0
    consecutive_failures: int = 0
    log: list[str] = field(default_factory=list)

    @property
    def tripped(self) -> bool:
        return self.consecutive_failures >= self.max_consecutive_failures

    def check(self, call: ToolCall) -> tuple[bool, str]:
        """门控一次工具调用，返回 (是否放行, 原因)。

        1. verdict, reason = self.classifier(sidecar_payload(call))
        2. allow：连续拒绝计数清零，返回 (True, "sidecar: allow")
        3. deny：连续拒绝计数加一。
           - 还没到 max_denials：返回 (False, "sidecar denied: {reason}")，Agent 会把它当成一次失败的观察
           - 达到 max_denials（拒绝熔断器）：不再让 Agent 自己绕，转交人类 self.confirm(call, reason)：
             同意 → 计数清零，返回 (True, "human approved")；不同意 → 返回 (False, "human rejected: {reason}")
        每次决定往 self.log 记一行 "{工具名} -> {放行与否}: {原因}"。
        """
        # TODO 练习 4.3b：Sidecar 门控与拒绝熔断器
        # 提示：不同意时计数不清零：下一次拒绝仍然直接问人，Agent 没法靠反复重试磨过去。
        raise NotImplementedError("练习 4.3b 还没有完成：Sidecar 门控与拒绝熔断器")

    def record(self, success: bool) -> None:
        self.consecutive_failures = 0 if success else self.consecutive_failures + 1


# ───────────────────────── 超时与重试 ─────────────────────────

def retry_safely(action: Callable[[], str], check: Callable[[], str | None], attempts: int = 3) -> str:
    """执行一个有副作用的操作。超时意味着“结果未知”，不能盲目重试：先查询，再决定。

    - action() 正常返回：返回它的结果
    - action() 抛 TimeoutError：调用 check()。
        * 返回值不是 None：操作其实已经生效，返回 "{check 的返回值} (confirmed after timeout)"
        * 返回 None：确认没有生效，可以重试
    - action() 抛其他异常：原样抛出（失败是明确的，交给 Agent 重新规划，而不是在这里重试）
    - 共尝试 attempts 次仍然超时且未生效：抛 TimeoutError(f"gave up after {attempts} attempts")
    """
    # TODO 练习 4.3c：先查询，后重试
    # 提示：for _ in range(attempts): try: return action() except TimeoutError: done = check(); ...
    raise NotImplementedError("练习 4.3c 还没有完成：先查询，后重试")
