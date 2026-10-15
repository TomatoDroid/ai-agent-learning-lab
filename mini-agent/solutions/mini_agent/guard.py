"""执行层护栏：动态风险评估、人工确认、熔断器（练习 1.3）。

对应原书第一章“护栏与安全性”与思考题 7：同一个工具在不同参数下风险可能完全不同。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Callable

from .messages import ToolCall
from .tools import ToolRegistry, UnknownToolError

RISK_ORDER = ["low", "medium", "high"]
SYSTEM_DIRS = ("/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc", "/var/lib")


def _max_risk(a: str, b: str) -> str:
    return a if RISK_ORDER.index(a) >= RISK_ORDER.index(b) else b


def path_escapes_workspace(path: str, workspace: str) -> bool:
    """path 是否跳出了工作目录（绝对路径、.. 越界都算）。只做字符串层面的规范化，不访问磁盘。"""
    ws = PurePosixPath(workspace)
    p = PurePosixPath(path)
    full = p if p.is_absolute() else ws / p
    parts: list[str] = []
    for part in full.parts:
        if part == "..":
            if len(parts) > 1:
                parts.pop()
        elif part != ".":
            parts.append(part)
    normalized = PurePosixPath(*parts) if parts else PurePosixPath("/")
    return normalized != ws and ws not in normalized.parents


def assess_risk(call: ToolCall, registry: ToolRegistry, workspace: str = "/workspace") -> str:
    """返回这次调用的风险等级 low / medium / high。

    规则（只升不降）：
    1. 起点是工具注册时声明的静态风险；未知工具按 high 处理（故障安全默认值）。
    2. 任何名为 path / paths 的参数指向工作目录之外：只读工具（静态风险 low）至少 medium；
       会改变世界的工具（静态风险 medium 及以上）直接 high。
    3. 指向系统目录（SYSTEM_DIRS）：high。
    4. 参数里 recursive=True 或 force=True：再升一级。
    """
    # >>> EXERCISE 1.3a 动态风险评估
    # HINT: 用 registry.get(call.name).risk 作为起点；捕获 UnknownToolError 时直接返回 "high"。
    # HINT: 收集 call.arguments 里的 path / paths（paths 可能是列表），逐个判断：
    # HINT: 以 SYSTEM_DIRS 中某一项开头（等于它或以 "它/" 开头）→ high；
    # HINT: 否则 path_escapes_workspace(...) 为真时，按静态风险是否为 low 决定升到 medium 还是 high。
    # HINT: 最后看 recursive / force，用 RISK_ORDER 升一级（high 封顶）。用 _max_risk 合并。
    try:
        base = registry.get(call.name).risk
    except UnknownToolError:
        return "high"
    risk = base
    raw = call.arguments.get("paths", call.arguments.get("path"))
    paths = raw if isinstance(raw, list) else [raw] if raw else []
    for p in paths:
        p = str(p)
        if any(p == d or p.startswith(d + "/") for d in SYSTEM_DIRS):
            risk = "high"
        elif path_escapes_workspace(p, workspace):
            risk = _max_risk(risk, "medium" if base == "low" else "high")
    if call.arguments.get("recursive") or call.arguments.get("force"):
        risk = RISK_ORDER[min(RISK_ORDER.index(risk) + 1, 2)]
    return risk
    # <<< EXERCISE


@dataclass
class Guard:
    registry: ToolRegistry
    confirm: Callable[[ToolCall, str], bool] = lambda call, risk: False  # 默认拒绝：故障安全
    workspace: str = "/workspace"
    max_consecutive_failures: int = 3
    consecutive_failures: int = 0
    log: list[str] = field(default_factory=list)

    @property
    def tripped(self) -> bool:
        return self.consecutive_failures >= self.max_consecutive_failures

    def check(self, call: ToolCall) -> tuple[bool, str]:
        """返回 (是否放行, 原因)。high 风险必须经 confirm 回调（上下文之外的人或审查进程）同意。"""
        # >>> EXERCISE 1.3a 放行规则
        # HINT: risk = assess_risk(call, self.registry, self.workspace)。
        # HINT: high：调用 self.confirm(call, risk)，同意则放行，原因写 "confirmed"；不同意原因写 "high risk, not confirmed"。
        # HINT: low / medium：直接放行，原因写风险等级。每次决定都往 self.log 记一行。
        risk = assess_risk(call, self.registry, self.workspace)
        if risk == "high":
            ok = bool(self.confirm(call, risk))
            reason = "confirmed" if ok else "high risk, not confirmed"
        else:
            ok, reason = True, risk
        self.log.append(f"{call.name} {risk} -> {'allow' if ok else 'deny'}")
        return ok, reason
        # <<< EXERCISE

    def record(self, success: bool) -> None:
        """熔断器：连续失败计数，成功一次就清零。"""
        # >>> EXERCISE 1.3a 熔断器
        # HINT: 失败加一，成功清零。tripped 属性已经帮你写好了。
        self.consecutive_failures = 0 if success else self.consecutive_failures + 1
        # <<< EXERCISE
