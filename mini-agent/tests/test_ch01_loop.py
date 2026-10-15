"""检查点 1.2：ReAct 核心循环。运行：pytest tests/test_ch01_loop.py"""
from mini_agent import llm as L
from mini_agent.builtin import basic_registry
from mini_agent.loop import run_agent
from mini_agent.messages import ToolCall


def test_没有工具调用时直接结束():
    model = L.ScriptedLLM([L.say("你好！")])
    r = run_agent(model, basic_registry(), "hi")
    assert r.answer == "你好！"
    assert r.stop_reason == "done"
    assert r.iterations == 1
    assert [m["role"] for m in r.messages] == ["system", "user", "assistant"]


def test_执行工具并把结果送回模型():
    model = L.ScriptedLLM([
        L.call("convert_currency", "c1", amount=2100000, from_currency="EUR"),
        L.say("约 228 万美元"),
    ])
    r = run_agent(model, basic_registry(), "2.1M 欧元是多少美元")
    assert r.stop_reason == "done" and r.answer == "约 228 万美元"
    assert r.tool_calls == 1 and r.iterations == 2
    tool_msg = r.messages[3]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "c1", "tool 消息必须带上对应调用的 id"
    assert tool_msg["content"] == "EUR->USD: 2282608.70"


def test_并行调用按顺序追加且id一一对应():
    model = L.ScriptedLLM([
        L.calls(ToolCall("a", "convert_currency", {"amount": 1, "from_currency": "EUR"}),
                ToolCall("b", "convert_currency", {"amount": 1, "from_currency": "GBP"})),
        L.say("done"),
    ])
    r = run_agent(model, basic_registry(), "x")
    tools = [m for m in r.messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tools] == ["a", "b"]


def test_API无状态_每次调用都送回完整历史且只追加():
    model = L.ScriptedLLM([
        L.call("calculator", "c1", expression="1+1"),
        L.call("calculator", "c2", expression="2+2"),
        L.say("ok"),
    ])
    run_agent(model, basic_registry(), "算一下")
    sent = [c["messages"] for c in model.calls]
    assert len(sent) == 3
    for earlier, later in zip(sent, sent[1:]):
        assert later[: len(earlier)] == earlier, "后一次请求必须以前一次请求为前缀（只追加、不改写）"
        assert len(later) == len(earlier) + 2, "每轮应追加 1 条 assistant + 1 条 tool"
    assert model.calls[0]["tools"], "每次都要把工具定义发给模型"


def test_达到最大轮数时停止():
    model = L.ScriptedLLM([L.call("calculator", f"c{i}", expression="1") for i in range(3)])
    r = run_agent(model, basic_registry(), "loop", max_iterations=3)
    assert r.stop_reason == "max_iterations"
    assert r.iterations == 3
    assert r.answer is None


def test_未知工具变成错误观察而不是崩溃():
    model = L.ScriptedLLM([L.call("fly_to_moon", "c1"), L.say("抱歉，做不到")])
    r = run_agent(model, basic_registry(), "去月球")
    err = r.messages[3]["content"]
    assert err.startswith("ERROR:") and "fly_to_moon" in err
    assert r.answer == "抱歉，做不到"


def test_工具内部异常变成错误观察():
    model = L.ScriptedLLM([L.call("convert_currency", "c1", amount=1, from_currency="XYZ"), L.say("换个币种")])
    r = run_agent(model, basic_registry(), "x")
    assert "ERROR: ValueError" in r.messages[3]["content"]
    assert r.stop_reason == "done"


def test_每次调用模型前执行before_call钩子():
    seen = []
    model = L.ScriptedLLM([L.call("calculator", "c1", expression="1+1"), L.say("2")])
    run_agent(model, basic_registry(), "x", before_call=lambda msgs: seen.append(len(msgs)))
    assert seen == [2, 4]
