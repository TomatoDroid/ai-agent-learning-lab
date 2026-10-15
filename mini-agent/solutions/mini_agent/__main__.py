"""命令行入口。

  python -m mini_agent demo        离线演示：原书第一章的多币种汇总轨迹（不需要 API Key）
  python -m mini_agent chat        用真实模型对话（需要 MINI_AGENT_BASE_URL / _API_KEY / _MODEL）
"""
from __future__ import annotations

import argparse
import json
import sys

from . import llm as L
from .agent import Agent
from .builtin import add_clock, add_workspace, basic_registry
from .guard import Guard
from .messages import ToolCall, tool_calls_of
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


def chat(workspace: str) -> None:
    reg = basic_registry()
    add_clock(reg)
    root = add_workspace(reg, workspace)

    def confirm(call: ToolCall, risk: str) -> bool:
        answer = input(f"\n⚠ 高风险操作 {call.name}({call.arguments})，允许吗？[y/N] ")
        return answer.strip().lower() == "y"

    agent = Agent(L.OpenAICompatLLM.from_env(), reg,
                  f"你是一个助手，可以在工作目录 {root} 中读写文件。需要真实数据时调用工具。",
                  guard=Guard(reg, confirm=confirm, workspace=str(root)), status=StatusTracker(), budget=60000)
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mini_agent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="离线演示 ReAct 轨迹")
    p = sub.add_parser("chat", help="接入真实模型对话")
    p.add_argument("--workspace", default="workspace")
    args = parser.parse_args()
    if args.cmd == "demo":
        demo()
    else:
        chat(args.workspace)


if __name__ == "__main__":
    main()
