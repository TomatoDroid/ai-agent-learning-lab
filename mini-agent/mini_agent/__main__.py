"""命令行入口。

  python -m mini_agent demo        离线演示：原书第一章的多币种汇总轨迹（不需要 API Key）
  python -m mini_agent chat        用真实模型对话（需要 MINI_AGENT_BASE_URL / _API_KEY / _MODEL）
  python -m mini_agent mcp         把工作目录工具作为 MCP 服务器（stdio）暴露给其他客户端
  python -m mini_agent eval        用真实模型跑内置的订单客服评估集，可保存结果（7.1 课）
  python -m mini_agent compare A B 对两次 eval 的结果做配对比较（7.3 课，里程碑 B）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from . import llm as L
from .agent import Agent
from .builtin import add_clock, add_workspace, basic_registry
from .coding import add_coding_tools
from .evals import MINI_SUITE, SUITE_SYSTEM_PROMPT, run_suite
from .guard import Guard
from .mcp import McpServer, serve_stdio
from .memory import MemoryStore, extract_memories
from .messages import ToolCall, tool_calls_of
from .recovery import ApiError, RetryingLLM, classify
from .stats import ci95, mcnemar, paired_bootstrap
from .status import StatusTracker


def print_trace(messages: list[dict], start: int = 0) -> None:
    colors = {"system": "35", "user": "34", "assistant": "32", "tool": "33"}
    tty = sys.stdout.isatty()
    for m in messages[start:]:
        role = m["role"]
        head = f"\033[{colors[role]}m{role:>9}\033[0m" if tty else f"{role:>9}"
        lines = []
        if m.get("reasoning_content"):
            lines.append(f"(思考) {m['reasoning_content']}")
        if m.get("content"):
            lines.append(m["content"])
        lines += [f"→ {c.name}({json.dumps(c.arguments, ensure_ascii=False)})" for c in tool_calls_of(m)]
        print(f"{head}  " + f"\n{'':>11}".join(lines))


def demo() -> None:
    script = [
        L.calls(ToolCall("call_1", "convert_currency", {"amount": 2100000, "from_currency": "EUR"}),
                ToolCall("call_2", "convert_currency", {"amount": 1800000, "from_currency": "GBP"}),
                ToolCall("call_3", "convert_currency", {"amount": 380000000, "from_currency": "JPY"}),
                reasoning="需要先把非美元币种换算成 USD，三次换算互不依赖，可以并行。"),
        L.calls(ToolCall("call_4", "calculator", {"expression": "(2500000 + 2282608.70 + 2278481.01 + 2541806.02)"}),
                reasoning="已拿到换算结果，汇总计算。"),
        L.say("FINAL ANSWER：年度总收入 $9,602,895.73，季度平均 $2,400,723.93。", reasoning="所有计算完成，总结结果。"),
    ]
    model = L.ScriptedLLM(script)
    agent = Agent(model, basic_registry(), "你是财务助理。需要真实数据时调用工具。")
    result = agent.run("根据公司季度收入：Q1 2.5M 美元，Q2 2.1M 欧元，Q3 1.8M 英镑，Q4 380M 日元，计算年度总收入和季度平均收入")
    print_trace(result.messages)
    print(f"\n停止原因：{result.stop_reason}；模型调用 {result.iterations} 次；工具调用 {result.tool_calls} 次")
    print("每次调用模型时读入的消息条数：", [len(c["messages"]) for c in model.calls])


def chat(workspace: str, memory_path: str | None = None, coding: bool = False) -> None:
    reg = basic_registry()
    add_clock(reg)
    root = add_workspace(reg, workspace)
    if coding:
        add_coding_tools(reg, root)  # 5.2：glob、grep、bash，凑齐 Coding Agent 的核心工具

    def confirm(call: ToolCall, risk: str) -> bool:
        answer = input(f"\n⚠ 高风险操作 {call.name}({call.arguments})，允许吗？[y/N] ")
        return answer.strip().lower() == "y"

    llm = L.OpenAICompatLLM.from_env()
    try:
        classify(ApiError(429))
        llm = RetryingLLM(llm)  # 5.1：限流、过载静默重试；还没做练习 5.1a 时跳过
    except NotImplementedError:
        pass
    store = MemoryStore.load(memory_path) if memory_path else None
    agent = Agent(llm, reg,
                  f"你是一个助手，可以在工作目录 {root} 中读写文件。需要真实数据时调用工具。",
                  guard=Guard(reg, confirm=confirm, workspace=str(root)), status=StatusTracker(), budget=60000, memory=store, validate_args=True)
    print(f"工作目录：{root}。输入 exit 退出。")
    while True:
        try:
            text = input("\n你> ").strip()
        except EOFError:
            break
        if text in {"exit", "quit"}:
            break
        if not text:
            continue
        before = len(agent.history) + 1
        result = agent.run(text)
        print_trace(result.messages, before)
        if result.stop_reason != "done":
            print(f"（停止原因：{result.stop_reason}）")
    if store is not None and agent.history:
        # 3.1：会话结束后，用一次额外的 LLM 调用提炼记忆，只追加写回
        talk = "\n".join(f"{m['role']}: {m['content']}" for m in agent.history
                         if m["role"] in ("user", "assistant") and m.get("content"))
        cards = extract_memories(llm, talk, ts=datetime.now().isoformat(timespec="seconds"), source="chat")
        for c in cards:
            store.add(c)
        store.save(memory_path)
        print(f"记住了 {len(cards)} 条新信息，写入 {memory_path}。")


def mcp(workspace: str) -> None:
    # 4.2：同一组工具，换一种协议暴露出去。只暴露读写工具，不带 delete_file：服务器端也要守最小权限
    reg = basic_registry()
    add_workspace(reg, workspace)
    del reg.tools["delete_file"]
    serve_stdio(McpServer(reg))


def evaluate(trials: int, save: str | None) -> None:
    llm = L.OpenAICompatLLM.from_env()
    report = run_suite(lambda reg: Agent(llm, reg, SUITE_SYSTEM_PROMPT, validate_args=True), MINI_SUITE, trials)
    for t in report.trials:
        mark = "✓" if t.verdict.passed else "✗"
        print(f"{mark} {t.task_id:<24} #{t.trial}  调用 {' → '.join(t.tool_calls) or '（无）'}")
        for f in t.verdict.failures:
            print(f"{'':>6}{f}")
    n = len(report.trials)
    p, lo, hi = ci95(sum(t.verdict.passed for t in report.trials), n)
    print(f"\n成功率 {p:.0%}（95% 区间 {lo:.0%}–{hi:.0%}，共 {n} 次试验）")
    for k in sorted({1, trials}):
        print(f"Pass@{k} = {report.pass_at(k):.0%}    Pass^{k} = {report.pass_hat(k):.0%}")
    if save:
        report.save(save)
        print(f"结果已写入 {save}")


def compare(path_a: str, path_b: str) -> None:
    def load(path):
        with open(path, encoding="utf-8") as f:
            return {(t["task"], t["trial"]): t["passed"] for t in json.load(f)["trials"]}

    a, b = load(path_a), load(path_b)
    keys = sorted(a.keys() & b.keys())
    if not keys:
        sys.exit("两份结果没有共同的 (任务, 试验) 可以配对")
    xa, xb = [a[k] for k in keys], [b[k] for k in keys]
    for name, xs in (("A", xa), ("B", xb)):
        p, lo, hi = ci95(sum(xs), len(xs))
        print(f"{name}：{p:.0%}（95% 区间 {lo:.0%}–{hi:.0%}）")
    r = mcnemar(xa, xb)
    diff, lo, hi = paired_bootstrap([float(x) for x in xa], [float(x) for x in xb])
    print(f"配对 {len(keys)} 次：B 对 A 错 {r.b_only}，A 对 B 错 {r.a_only}，McNemar p = {r.p_value:.3f}")
    print(f"B - A = {diff:+.1%}（自助法 95% 区间 {lo:+.1%} 到 {hi:+.1%}）")
    print("结论：" + ("差异显著" if r.p_value < 0.05 else "还分不出好坏，需要更多题或更多次试验"))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mini_agent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="离线演示 ReAct 轨迹")
    p = sub.add_parser("chat", help="接入真实模型对话")
    p.add_argument("--workspace", default="workspace")
    p.add_argument("--memory", help="用户记忆文件（JSON Lines），会话结束时追加新记忆")
    p.add_argument("--coding", action="store_true", help="加上 glob、grep、bash，作为 Coding Agent 使用（5.2 课）")
    m = sub.add_parser("mcp", help="以 MCP 服务器（stdio）暴露工具")
    m.add_argument("--workspace", default="workspace")
    e = sub.add_parser("eval", help="用真实模型跑内置评估集")
    e.add_argument("--trials", type=int, default=3, help="每个任务跑几次（默认 3）")
    e.add_argument("--save", help="把每次试验的结果写入 JSON 文件")
    c = sub.add_parser("compare", help="配对比较两次 eval 的结果")
    c.add_argument("a")
    c.add_argument("b")
    args = parser.parse_args()
    if args.cmd == "demo":
        demo()
    elif args.cmd == "mcp":
        mcp(args.workspace)
    elif args.cmd == "eval":
        evaluate(args.trials, args.save)
    elif args.cmd == "compare":
        compare(args.a, args.b)
    else:
        chat(args.workspace, args.memory, args.coding)


if __name__ == "__main__":
    main()
