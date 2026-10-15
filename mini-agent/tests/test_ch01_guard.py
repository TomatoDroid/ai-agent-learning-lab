"""检查点 1.3：动态风险评估、人工确认与熔断器。运行：pytest tests/test_ch01_guard.py"""
import pytest

from mini_agent import llm as L
from mini_agent.guard import Guard, assess_risk
from mini_agent.loop import run_agent
from mini_agent.messages import ToolCall
from mini_agent.tools import Tool, ToolRegistry


@pytest.fixture
def reg():
    r = ToolRegistry()
    for name, risk in [("read_file", "low"), ("write_file", "medium"), ("delete_file", "medium"), ("pay", "high")]:
        r.register(Tool(name, name, {"type": "object", "properties": {}}, lambda **kw: "ok", risk))
    r.register(Tool("flaky", "always fails", {"type": "object", "properties": {}}, lambda **kw: 1 / 0))
    return r


@pytest.mark.parametrize("name,args,expected", [
    ("read_file", {"path": "notes.txt"}, "low"),
    ("read_file", {"path": "../secret.txt"}, "medium"),
    ("read_file", {"path": "/home/me/.ssh/id_rsa"}, "medium"),
    ("read_file", {"path": "/etc/passwd"}, "high"),
    ("delete_file", {"path": "tmp/a.log"}, "medium"),
    ("write_file", {"path": "/tmp/leaked.txt"}, "high"),
    ("write_file", {"path": "../../x"}, "high"),
    ("delete_file", {"path": "tmp", "recursive": True}, "high"),
    ("write_file", {"paths": ["a.txt", "/usr/bin/python"]}, "high"),
    ("pay", {"amount": 1}, "high"),
    ("unknown_tool", {}, "high"),
    ("read_file", {"path": "sub/../notes.txt"}, "low"),
    ("read_file", {"path": "/workspace/notes.txt"}, "low"),
    ("read_file", {"path": "/etcetera/x"}, "medium"),
])
def test_动态风险评估(reg, name, args, expected):
    assert assess_risk(ToolCall("c", name, args), reg) == expected


def test_高风险默认拒绝_确认后放行(reg):
    g = Guard(reg)
    assert g.check(ToolCall("c", "pay", {"amount": 5})) == (False, "high risk, not confirmed")
    asked = []
    g2 = Guard(reg, confirm=lambda call, risk: asked.append((call.name, risk)) or True)
    assert g2.check(ToolCall("c", "pay", {})) == (True, "confirmed")
    assert asked == [("pay", "high")]
    assert g2.check(ToolCall("c", "read_file", {"path": "a"})) == (True, "low")


def test_熔断器(reg):
    g = Guard(reg, max_consecutive_failures=2)
    g.record(False)
    assert not g.tripped
    g.record(True)
    g.record(False)
    assert not g.tripped
    g.record(False)
    assert g.tripped


def test_循环中_被拒绝的调用不执行并告诉模型(reg):
    executed = []
    reg.register(Tool("pay", "pay", {"type": "object", "properties": {}}, lambda **kw: executed.append(kw) or "paid", "high"))
    model = L.ScriptedLLM([L.call("pay", "c1", amount=100), L.say("已取消付款")])
    r = run_agent(model, reg, "付钱", guard=Guard(reg))
    assert executed == []
    assert r.messages[3]["content"] == "DENIED: high risk, not confirmed"
    assert r.answer == "已取消付款"


def test_循环中_连续失败触发熔断(reg):
    model = L.ScriptedLLM([L.call("flaky", f"c{i}") for i in range(10)])
    r = run_agent(model, reg, "试试", guard=Guard(reg, max_consecutive_failures=3), max_iterations=10)
    assert r.stop_reason == "circuit_open"
    assert r.iterations == 3
    assert all(m["content"].startswith("ERROR: ZeroDivisionError") for m in r.messages if m["role"] == "tool")
