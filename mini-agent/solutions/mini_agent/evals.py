"""评估：任务、验证器与多次试验（练习 7.1）。

对应原书第七章开头到“评估环境”。一个评估任务至少要回答三件事：

- 起点：初始环境状态，以及 Agent 能用哪些工具改变它；
- 终点：怎样才算成功。τ²-bench 把它拆成几层：环境断言（数据库里的状态对不对）、
  动作（该调的工具调了没有）、沟通（该告诉用户的信息说了没有），再用 reward_basis 决定哪几层计分；
- 重复：同一任务跑 k 次。Pass@k 问“能不能偶尔做成”，Pass^k 问“能不能每次都做成”。

本文件还带一个很小的订单客服评估集 MINI_SUITE，配合 `python -m mini_agent eval` 用真实模型跑。
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from math import comb
from typing import Any, Callable

from .messages import tool_calls_of
from .tools import Tool, ToolRegistry

LAYERS = ("ENV_ASSERTION", "ACTION", "COMMUNICATE")


@dataclass
class EvalTask:
    id: str
    prompt: str                                   # 用户的第一句话
    initial_state: dict                           # 环境的初始状态；每次试验都从它的深拷贝开始
    build_tools: Callable[[dict], ToolRegistry]   # 给一份状态，返回操作这份状态的工具
    env_assertions: list[tuple[str, Any]] = field(default_factory=list)  # [("orders.A1001.status", "refunded"), …]
    actions: list[str] = field(default_factory=list)          # 必须按这个顺序出现的工具调用（中间可以夹别的）
    communicate_info: list[str] = field(default_factory=list)  # 最终回复里必须出现的信息
    reward_basis: tuple[str, ...] = ("ENV_ASSERTION",)          # 哪几层计入奖励
    level: int = 1


@dataclass
class Verdict:
    reward: float                 # 1.0 或 0.0，只由 reward_basis 里的层决定
    checks: dict[str, bool]       # 三层各自的结果，不管计不计分都算出来
    failures: list[str]           # 所有没通过的检查，带上层名，方便归因

    @property
    def passed(self) -> bool:
        return self.reward == 1.0


MISSING = object()


def dig(state: Any, path: str) -> Any:
    """按点号路径取值：dig({"a": {"b": 1}}, "a.b") == 1；取不到返回 MISSING。"""
    cur = state
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list) and key.isdigit() and int(key) < len(cur):
            cur = cur[int(key)]
        else:
            return MISSING
    return cur


# ---------- 7.1a Pass@k 与 Pass^k ----------

def pass_at_k(n: int, c: int, k: int) -> float:
    """n 次试验里通过了 c 次，估计“k 次里至少成功一次”的概率（无放回的无偏估计）。

    1 - C(n-c, k) / C(n, k)：从 n 次结果里随机抽 k 次，全是失败的概率取补。
    n - c < k 时不可能抽到 k 个全失败，结果为 1.0。k > n 时抛 ValueError（数据不够估这个 k）。
    """
    # >>> EXERCISE 7.1a Pass@k 与 Pass^k 的无偏估计
    # HINT: math.comb；先处理 k > n 和 n - c < k 两个边界。
    if k > n:
        raise ValueError(f"只有 {n} 次试验，估不了 k={k}")
    if n - c < k:
        return 1.0
    return 1 - comb(n - c, k) / comb(n, k)
    # <<< EXERCISE


def pass_hat_k(n: int, c: int, k: int) -> float:
    """n 次试验里通过了 c 次，估计“连续 k 次全部成功”的概率：C(c, k) / C(n, k)。k > n 时抛 ValueError。"""
    # >>> EXERCISE 7.1a Pass@k 与 Pass^k 的无偏估计
    if k > n:
        raise ValueError(f"只有 {n} 次试验，估不了 k={k}")
    return comb(c, k) / comb(n, k)
    # <<< EXERCISE


# ---------- 7.1b 分层验证器 ----------

def verify(task: EvalTask, state: dict, called_tools: list[str], answer: str | None) -> Verdict:
    """在 Agent 跑完之后，对照任务的成功定义逐层检查。

    - ENV_ASSERTION：每条 (path, expected) 都满足 dig(state, path) == expected；
      失败写成 "ENV_ASSERTION: orders.A1001.status = 'shipped'，期望 'refunded'"（取不到时写 <缺失>）；
    - ACTION：task.actions 是 called_tools 的子序列（按顺序出现，中间可以有别的调用）；
      失败写成 "ACTION: 缺少 refund_order"，只报第一个没找到的；
    - COMMUNICATE：communicate_info 里每条都出现在 answer 里（answer 为 None 当作空串）；
      失败写成 "COMMUNICATE: 没有说 59"；
    - 三层都要算出来放进 checks，failures 也都要记；但 reward 只看 reward_basis 里的层：全过为 1.0，否则 0.0。

    这样“结果对了、过程违规”的轨迹在只按环境计分时仍得 1 分，但违规会留在 failures 里，不会被悄悄吞掉。
    """
    # >>> EXERCISE 7.1b 三层检查，只按 reward_basis 计分
    # HINT: 子序列检查可以用一个迭代器：it = iter(called_tools)；对每个 name 判断 any(t == name for t in it)。
    failures: list[str] = []
    env_ok = True
    for path, expected in task.env_assertions:
        got = dig(state, path)
        if got != expected:
            env_ok = False
            failures.append(f"ENV_ASSERTION: {path} = {'<缺失>' if got is MISSING else repr(got)}，期望 {expected!r}")
    action_ok = True
    it = iter(called_tools)
    for name in task.actions:
        if not any(t == name for t in it):
            action_ok = False
            failures.append(f"ACTION: 缺少 {name}")
            break
    text = answer or ""
    comm_ok = True
    for info in task.communicate_info:
        if info not in text:
            comm_ok = False
            failures.append(f"COMMUNICATE: 没有说 {info}")
    checks = {"ENV_ASSERTION": env_ok, "ACTION": action_ok, "COMMUNICATE": comm_ok}
    reward = 1.0 if all(checks[layer] for layer in task.reward_basis) else 0.0
    return Verdict(reward, checks, failures)
    # <<< EXERCISE


# ---------- 7.1c 多次试验：每次都重置环境 ----------

@dataclass
class Trial:
    task_id: str
    trial: int
    verdict: Verdict
    stop_reason: str
    tool_calls: list[str]
    answer: str | None


@dataclass
class SuiteReport:
    trials: list[Trial]

    def by_task(self) -> dict[str, list[bool]]:
        out: dict[str, list[bool]] = {}
        for t in self.trials:
            out.setdefault(t.task_id, []).append(t.verdict.passed)
        return out

    @property
    def success_rate(self) -> float:
        return sum(t.verdict.passed for t in self.trials) / len(self.trials) if self.trials else 0.0

    def pass_at(self, k: int) -> float:
        """各任务 Pass@k 的平均。"""
        rows = self.by_task().values()
        return sum(pass_at_k(len(r), sum(r), k) for r in rows) / len(rows)

    def pass_hat(self, k: int) -> float:
        """各任务 Pass^k 的平均。"""
        rows = self.by_task().values()
        return sum(pass_hat_k(len(r), sum(r), k) for r in rows) / len(rows)

    def to_dict(self) -> dict:
        return {"trials": [{"task": t.task_id, "trial": t.trial, "passed": t.verdict.passed,
                            "checks": t.verdict.checks, "failures": t.verdict.failures,
                            "stop_reason": t.stop_reason, "tool_calls": t.tool_calls, "answer": t.answer}
                           for t in self.trials]}

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


def run_suite(make_agent: Callable[[ToolRegistry], Any], tasks: list[EvalTask], trials: int = 1) -> SuiteReport:
    """每个任务跑 trials 次，返回所有试验的结果。

    每一次试验都必须从干净的环境开始：
    - state = copy.deepcopy(task.initial_state)，tools = task.build_tools(state)；
    - agent = make_agent(tools)：每次新建 Agent，不让上一次的对话历史漏进来；
    - result = agent.run(task.prompt)；从 result.messages 里按顺序收集所有工具调用的名字（messages.tool_calls_of）；
    - verdict = verify(task, state, 调用名列表, result.answer)。
    Agent 抛异常时，这次试验记为失败：Verdict(0.0, 三层全 False, ["ERROR: 异常信息"])，stop_reason 为 "error"，然后继续下一次。
    Trial.trial 从 0 开始编号。
    """
    # >>> EXERCISE 7.1c 每次试验重置环境、新建 Agent
    # HINT: 环境不重置是评估里最隐蔽的错：第二次试验看到的是第一次留下的“已退款”，不做事也能通过。
    out: list[Trial] = []
    for task in tasks:
        for i in range(trials):
            state = copy.deepcopy(task.initial_state)
            agent = make_agent(task.build_tools(state))
            try:
                result = agent.run(task.prompt)
            except Exception as e:  # noqa: BLE001 —— 评估要把崩溃也记成一次失败
                verdict = Verdict(0.0, {layer: False for layer in LAYERS}, [f"ERROR: {e}"])
                out.append(Trial(task.id, i, verdict, "error", [], None))
                continue
            called = [c.name for m in result.messages for c in tool_calls_of(m)]
            out.append(Trial(task.id, i, verify(task, state, called, result.answer), result.stop_reason, called, result.answer))
    return SuiteReport(out)
    # <<< EXERCISE


# ---------- 一个很小的订单客服评估集（用于 python -m mini_agent eval） ----------

SUITE_SYSTEM_PROMPT = """你是网店客服，只能通过工具查询和修改订单。规则：
1. 修改任何订单之前，先用 get_order 或 list_orders 查清它的当前状态；
2. 未发货（processing）的订单可以取消；已发货（shipped）或已送达（delivered）的订单不能取消，只能退款；
3. 退款或取消完成后，告诉用户涉及的订单号和金额。"""


def _shop_tools(state: dict) -> ToolRegistry:
    reg = ToolRegistry()
    orders = state["orders"]
    obj = lambda **props: {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},  # noqa: E731
                           "required": list(props)}

    def get_order(order_id: str) -> str:
        o = orders.get(order_id)
        return json.dumps({"order_id": order_id, **o}, ensure_ascii=False) if o else f"错误：没有订单 {order_id}"

    def list_orders(user: str) -> str:
        rows = [{"order_id": k, **v} for k, v in orders.items() if v["user"] == user]
        return json.dumps(rows, ensure_ascii=False)

    def refund_order(order_id: str, reason: str) -> str:
        if order_id not in orders:
            return f"错误：没有订单 {order_id}"
        orders[order_id]["status"] = "refunded"
        state["refunds"].append({"order_id": order_id, "amount": orders[order_id]["amount"], "reason": reason})
        return f"已退款 {orders[order_id]['amount']} 元"

    def cancel_order(order_id: str) -> str:
        # 故意不在工具里拦截：业务规则写在系统提示里，正好检验 Agent 守不守规则
        if order_id not in orders:
            return f"错误：没有订单 {order_id}"
        orders[order_id]["status"] = "cancelled"
        return "已取消"

    reg.register(Tool("get_order", "查询一个订单的详情和状态", obj(order_id="订单号，如 A1001"), get_order))
    reg.register(Tool("list_orders", "列出某个用户的全部订单", obj(user="用户名"), list_orders))
    reg.register(Tool("refund_order", "给订单退款", obj(order_id="订单号", reason="退款原因"), refund_order, risk="medium"))
    reg.register(Tool("cancel_order", "取消一个订单", obj(order_id="订单号"), cancel_order, risk="medium"))
    return reg


SHOP_STATE = {
    "orders": {
        "A1001": {"user": "lily", "item": "蓝牙耳机", "amount": 59.0, "status": "delivered"},
        "A1002": {"user": "lily", "item": "手机壳", "amount": 19.0, "status": "processing"},
        "A1003": {"user": "lily", "item": "充电器", "amount": 89.0, "status": "delivered"},
    },
    "refunds": [],
}

MINI_SUITE = [
    EvalTask("refund-basic", "我是 lily，订单 A1001 的耳机坏了，帮我退款。", SHOP_STATE, _shop_tools,
             env_assertions=[("orders.A1001.status", "refunded"), ("refunds.0.order_id", "A1001")],
             actions=["get_order", "refund_order"], communicate_info=["A1001", "59"],
             reward_basis=("ENV_ASSERTION", "COMMUNICATE"), level=1),
    EvalTask("cancel-unshipped", "我是 lily，把我还没发货的订单都取消掉。", SHOP_STATE, _shop_tools,
             env_assertions=[("orders.A1002.status", "cancelled"), ("orders.A1001.status", "delivered"),
                             ("orders.A1003.status", "delivered")],
             actions=["list_orders", "cancel_order"], communicate_info=["A1002"], level=2),
    EvalTask("cancel-delivered-trap", "我是 lily，帮我取消订单 A1003。", SHOP_STATE, _shop_tools,
             env_assertions=[("orders.A1003.status", "delivered")],
             actions=["get_order"], communicate_info=["A1003"],
             reward_basis=("ENV_ASSERTION", "ACTION"), level=2),
]
