"""前缀缓存模拟器与上下文“体检”（练习 2.2）。

对应原书第二章“KV Cache 友好的上下文设计”与实验 2-3。真实的 Prompt Cache 由服务商实现，
这里用一个足够说明问题的模型：把请求序列化成 token，和上一次请求比较最长公共前缀，
前缀内的 token 算“命中缓存”，其余要重新计算。
"""
from __future__ import annotations

import json
import re

_TOKEN = re.compile(r"[A-Za-z0-9_]+|[一-鿿]|\s+|[^\sA-Za-z0-9_一-鿿]")


def tokenize(text: str) -> list[str]:
    """粗糙但确定的分词：英文按词，中文按字，标点和空白各自成一个 token。"""
    return _TOKEN.findall(text)


def serialize(messages: list[dict], tools: list[dict] | None = None) -> str:
    """按“工具定义在前、消息在后”的顺序把请求变成字符串，模拟服务端看到的前缀顺序。"""
    parts = [json.dumps(t, ensure_ascii=False, sort_keys=True) for t in tools or []]
    parts += [json.dumps(m, ensure_ascii=False, sort_keys=True) for m in messages]
    return "\n".join(parts)


def request_tokens(messages: list[dict], tools: list[dict] | None = None) -> list[str]:
    return tokenize(serialize(messages, tools))


def common_prefix_len(a: list[str], b: list[str]) -> int:
    """两个 token 序列的最长公共前缀长度。"""
    # >>> EXERCISE 2.2 最长公共前缀
    # HINT: 从头逐个比较，遇到第一个不同的位置就停。
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n
    # <<< EXERCISE


class CacheMeter:
    """记录一串连续请求的缓存命中情况。只缓存“上一次请求”，足以暴露所有常见错误。"""

    def __init__(self, cached_price: float = 0.1):
        self.cached_price = cached_price
        self.prev: list[str] | None = None
        self.cached = 0
        self.computed = 0
        self.history: list[dict] = []

    def observe(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """记录一次请求，返回 {"cached": 命中 token 数, "computed": 需计算 token 数, "total": 总数}。"""
        # >>> EXERCISE 2.2 记录一次请求
        # HINT: tokens = request_tokens(messages, tools)；第一次请求全部要计算。
        # HINT: 之后命中数 = 与 self.prev 的公共前缀长度。累加到 self.cached / self.computed，
        # HINT: 把本次结果 append 到 self.history，并更新 self.prev。
        tokens = request_tokens(messages, tools)
        hit = common_prefix_len(self.prev, tokens) if self.prev is not None else 0
        stat = {"cached": hit, "computed": len(tokens) - hit, "total": len(tokens)}
        self.cached += hit
        self.computed += len(tokens) - hit
        self.history.append(stat)
        self.prev = tokens
        return stat
        # <<< EXERCISE

    @property
    def hit_rate(self) -> float:
        total = self.cached + self.computed
        return self.cached / total if total else 0.0

    @property
    def cost(self) -> float:
        """以“计算一个 token = 1”为单位的相对成本。"""
        return self.cached * self.cached_price + self.computed


def diagnose(prev: list[dict], prev_tools: list[dict] | None, cur: list[dict], cur_tools: list[dict] | None) -> list[str]:
    """比较相邻两次请求，找出破坏前缀稳定性的写法。返回问题代码列表（可能为空）：

    - "system_changed"：system 消息内容变了（例如往里写时间戳）
    - "tools_reordered"：工具集合相同但顺序变了
    - "tools_changed"：工具集合本身变了
    - "history_rewritten"：cur 不是 prev 的“只追加”延伸（删除、截断、改写了旧消息）
    """
    # >>> EXERCISE 2.2 上下文体检
    # HINT: system 消息取各自第一条 role == "system" 的 content 比较。
    # HINT: 工具按 function.name 列表比较：列表相等没问题；排序后相等 → reordered；否则 → changed。
    # HINT: 历史：cur 至少和 prev 一样长，且 cur[:len(prev)] 中除 system 外逐条等于 prev。
    problems: list[str] = []
    sys_prev = next((m["content"] for m in prev if m["role"] == "system"), None)
    sys_cur = next((m["content"] for m in cur if m["role"] == "system"), None)
    if sys_prev != sys_cur:
        problems.append("system_changed")
    names_prev = [t["function"]["name"] for t in prev_tools or []]
    names_cur = [t["function"]["name"] for t in cur_tools or []]
    if names_prev != names_cur:
        problems.append("tools_reordered" if sorted(names_prev) == sorted(names_cur) else "tools_changed")
    rest_prev = [m for m in prev if m["role"] != "system"]
    rest_cur = [m for m in cur if m["role"] != "system"]
    if rest_cur[: len(rest_prev)] != rest_prev:
        problems.append("history_rewritten")
    return problems
    # <<< EXERCISE
