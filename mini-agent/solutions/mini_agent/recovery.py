"""故障与错误恢复：先分类再重试、重复调用检测、轨迹修复与跨厂商接管（练习 5.1）。

对应原书第五章“故障与错误恢复”与实验 5-1。三条原则：
- 捕获故障后先问“值不值得重试”：限流、过载、网络抖动重试才有意义，参数错误重试一万次也一样；
- 除了单次错误，还要检测模式：同一个“工具名 + 参数”指纹反复出现，就是没有进展；
- 每条恢复路径都要有上限。
"""
from __future__ import annotations

import hashlib
import json
import random
import time
import urllib.error
from dataclasses import dataclass, field
from typing import Callable

from .messages import ToolCall, tool_calls_of

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
MISSING_RESULT = "ERROR: tool result missing (the call was interrupted before it returned)"


class ApiError(Exception):
    """模型 API 返回的错误。retry_after：服务端建议的等待秒数（来自 Retry-After 头），没有则为 None。"""

    def __init__(self, status: int, message: str = "", retry_after: float | None = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status, self.retry_after = status, retry_after


def classify(exc: BaseException) -> str:
    """把异常分成 "retry"（可重试的基础设施噪声）或 "fatal"（原样重试没有意义）。

    - ApiError：status 在 RETRYABLE_STATUS 里 → retry，否则 fatal（400 参数错、401 鉴权、404……）
    - urllib.error.HTTPError：按它的 code 同样判断
    - TimeoutError、ConnectionError、urllib.error.URLError（网络层）→ retry
    - 其他一切 → fatal
    注意 HTTPError 是 URLError 的子类，要先判断它。
    """
    # >>> EXERCISE 5.1a 错误分类
    # HINT: isinstance 的顺序很重要：ApiError → HTTPError → (TimeoutError, ConnectionError, URLError)。
    if isinstance(exc, ApiError):
        return "retry" if exc.status in RETRYABLE_STATUS else "fatal"
    if isinstance(exc, urllib.error.HTTPError):
        return "retry" if exc.code in RETRYABLE_STATUS else "fatal"
    if isinstance(exc, (TimeoutError, ConnectionError, urllib.error.URLError)):
        return "retry"
    return "fatal"
    # <<< EXERCISE


def backoff_delay(attempt: int, base: float, cap: float, rand: float, retry_after: float | None = None) -> float:
    """第 attempt 次重试（从 0 开始）前等多久：指数退避 + 随机抖动，并尊重服务端的等待提示。

    delay = min(cap, base * 2 ** attempt) * (0.5 + rand / 2)   # rand ∈ [0, 1)：等待时间落在 [50%, 100%) 之间
    有 retry_after 时，取 max(delay, retry_after)。
    """
    # >>> EXERCISE 5.1a 指数退避与抖动
    # HINT: 抖动让大量客户端不会在同一时刻一起重试，造成二次拥塞。
    delay = min(cap, base * 2 ** attempt) * (0.5 + rand / 2)
    return max(delay, retry_after) if retry_after is not None else delay
    # <<< EXERCISE


@dataclass
class RetryingLLM:
    """给任何 llm 套上“静默重试”：可重试的错误按退避重试，不可重试的立即抛出，超过上限也抛出。"""
    llm: object
    max_retries: int = 4
    base: float = 1.0
    cap: float = 30.0
    sleep: Callable[[float], None] = time.sleep
    rand: Callable[[], float] = random.random
    log: list[str] = field(default_factory=list)

    def complete(self, messages, tools=None):
        for attempt in range(self.max_retries + 1):
            try:
                return self.llm.complete(messages, tools)
            except Exception as exc:  # noqa: BLE001
                if classify(exc) == "fatal" or attempt == self.max_retries:
                    raise
                d = backoff_delay(attempt, self.base, self.cap, self.rand(), getattr(exc, "retry_after", None))
                self.log.append(f"retry {attempt + 1} after {d:.2f}s: {exc}")
                self.sleep(d)


def fingerprint(call: ToolCall) -> str:
    """“工具名 + 参数”指纹：参数按键排序后序列化，{"b":1,"a":2} 和 {"a":2,"b":1} 指纹相同。"""
    raw = call.name + json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class RepeatGuard:
    """无进展循环检测。接口与 1.3 的 Guard 相同，可以直接传给 Agent(guard=...)。"""
    limit: int = 3
    seen: dict[str, int] = field(default_factory=dict)
    consecutive_failures: int = 0
    max_consecutive_failures: int = 5
    log: list[str] = field(default_factory=list)

    @property
    def tripped(self) -> bool:
        return self.consecutive_failures >= self.max_consecutive_failures

    def check(self, call: ToolCall) -> tuple[bool, str]:
        """同一个指纹第 limit 次出现时拒绝执行（之后每次都拒绝），返回：
        (False, "repeated identical call {n} times without progress; change the approach instead of retrying")
        其余情况返回 (True, "ok")。每次拒绝往 self.log 记一行 "{工具名} x{n}"。
        """
        # >>> EXERCISE 5.1b 重复调用指纹
        # HINT: n = self.seen.get(fp, 0) + 1，写回 self.seen；n >= self.limit 时拒绝。
        fp = fingerprint(call)
        n = self.seen.get(fp, 0) + 1
        self.seen[fp] = n
        if n >= self.limit:
            self.log.append(f"{call.name} x{n}")
            return False, f"repeated identical call {n} times without progress; change the approach instead of retrying"
        return True, "ok"
        # <<< EXERCISE

    def record(self, success: bool) -> None:
        self.consecutive_failures = 0 if success else self.consecutive_failures + 1


def repair_pairs(messages: list[dict]) -> list[dict]:
    """完整性修复：返回新列表，保证每个工具调用都有配对的结果，每个结果都有对应的调用。

    - assistant 消息里的某个 tool_call，在它之后、下一条 assistant 消息之前没有同 id 的 tool 消息：
      在这组结果的末尾（即下一条非 tool 消息之前）补一条 {"role": "tool", "tool_call_id": id, "content": MISSING_RESULT}
    - tool 消息的 tool_call_id 不对应前面任何调用：删掉
    其余消息原样保留、顺序不变。不修改传入的列表。
    """
    # >>> EXERCISE 5.1c 修复轨迹配对
    # HINT: 遍历时维护 pending：上一条 assistant 发出、尚未收到结果的 id 列表（保持顺序）。
    # HINT: 遇到非 tool 消息（或遍历结束）时，先为 pending 里剩下的 id 补占位结果，再处理这条消息。
    out: list[dict] = []
    pending: list[str] = []
    known: set[str] = set()

    def flush():
        out.extend({"role": "tool", "tool_call_id": cid, "content": MISSING_RESULT} for cid in pending)
        pending.clear()

    for m in messages:
        if m["role"] == "tool":
            if m.get("tool_call_id") in known:
                out.append(m)
                if m["tool_call_id"] in pending:
                    pending.remove(m["tool_call_id"])
            continue
        flush()
        out.append(m)
        if m["role"] == "assistant":
            ids = [c.id for c in tool_calls_of(m)]
            pending.extend(ids)
            known.update(ids)
    flush()
    return out
    # <<< EXERCISE


def handoff(messages: list[dict], id_prefix: str = "h") -> list[dict]:
    """跨厂商接管：把一条轨迹改写成另一家模型能接着跑的样子（原书实验 5-1 的“中立”做法）。

    - 带走文字，丢掉凭证：assistant 的 reasoning_content 不再放在思考字段里，而是作为普通内容带入：
      content 变成 "[earlier reasoning] {reasoning}\\n{原 content}"（原 content 为空时不要第二行）；
      删除 reasoning_content 和 reasoning_signature 两个字段。
    - 标识符重新生成：工具调用 id 按出现顺序改成 f"{id_prefix}{序号}"（从 1 开始），
      对应 tool 消息的 tool_call_id 一起改，配对关系不变。
    - 其余字段原样保留。返回新列表，不修改传入的消息。
    """
    # >>> EXERCISE 5.1c 跨厂商接管
    # HINT: 先 copy.deepcopy 一份；tool_calls 里的 id 在 m["tool_calls"][i]["id"]。
    import copy
    out = copy.deepcopy(messages)
    mapping: dict[str, str] = {}
    for m in out:
        if m["role"] == "assistant":
            reasoning = m.pop("reasoning_content", None)
            m.pop("reasoning_signature", None)
            if reasoning:
                m["content"] = f"[earlier reasoning] {reasoning}" + (f"\n{m['content']}" if m.get("content") else "")
            for c in m.get("tool_calls") or []:
                mapping[c["id"]] = f"{id_prefix}{len(mapping) + 1}"
                c["id"] = mapping[c["id"]]
        elif m["role"] == "tool" and m.get("tool_call_id") in mapping:
            m["tool_call_id"] = mapping[m["tool_call_id"]]
    return out
    # <<< EXERCISE
