"""检查点 5.1：错误分类与退避、重复调用检测、轨迹修复与跨厂商接管。运行：pytest tests/test_ch05_recovery.py"""
import urllib.error

import pytest

from mini_agent import llm as L
from mini_agent import messages as M
from mini_agent.agent import Agent
from mini_agent.messages import ToolCall
from mini_agent.recovery import (MISSING_RESULT, ApiError, RepeatGuard, RetryingLLM, backoff_delay, classify, fingerprint,
                                 handoff, repair_pairs)
from mini_agent.tools import Tool, ToolRegistry


def test_先分类_再决定要不要重试():
    assert classify(ApiError(429)) == "retry"
    assert classify(ApiError(529, "overloaded")) == "retry"
    assert classify(ApiError(400, "invalid tool schema")) == "fatal"
    assert classify(ApiError(401)) == "fatal"
    assert classify(urllib.error.HTTPError("u", 503, "x", {}, None)) == "retry"
    assert classify(urllib.error.HTTPError("u", 404, "x", {}, None)) == "fatal", "HTTPError 是 URLError 的子类，先看状态码"
    assert classify(urllib.error.URLError("dns")) == "retry"
    assert classify(TimeoutError()) == "retry"
    assert classify(ValueError("bad")) == "fatal"


def test_指数退避_抖动_尊重服务端提示():
    assert backoff_delay(0, 1, 30, 0.0) == 0.5
    assert backoff_delay(3, 1, 30, 0.999999) == pytest.approx(8, abs=1e-4)
    assert backoff_delay(10, 1, 30, 0.0) == 15, "封顶 30 秒，再乘抖动"
    assert backoff_delay(0, 1, 30, 0.0, retry_after=7) == 7


class Flaky:
    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return L.say("ok")


def test_静默重试_限流两次后成功():
    slept = []
    llm = RetryingLLM(Flaky([ApiError(429, retry_after=2), ApiError(503)]), sleep=slept.append, rand=lambda: 0.0)
    assert llm.complete([M.user("hi")]).content == "ok"
    assert slept == [2, 1.0] and len(llm.log) == 2


def test_不可重试的错误立即抛出_不浪费配额():
    inner = Flaky([ApiError(400, "bad request")])
    with pytest.raises(ApiError):
        RetryingLLM(inner, sleep=lambda s: None).complete([])
    assert inner.calls == 1


def test_重试有上限():
    inner = Flaky([ApiError(529)] * 10)
    with pytest.raises(ApiError):
        RetryingLLM(inner, max_retries=3, sleep=lambda s: None).complete([])
    assert inner.calls == 4


def test_指纹与参数顺序无关():
    assert fingerprint(ToolCall("a", "grep", {"pattern": "x", "glob": "*.py"})) == fingerprint(ToolCall("b", "grep", {"glob": "*.py", "pattern": "x"}))
    assert fingerprint(ToolCall("a", "grep", {"pattern": "x"})) != fingerprint(ToolCall("a", "grep", {"pattern": "y"}))


def test_同一个调用第三次被拦下_模型被迫换思路():
    reg = ToolRegistry()
    reg.register(Tool("read_file", "d", {"type": "object", "properties": {"path": {"type": "string"}}}, lambda path: "ERROR: locked"))
    model = L.ScriptedLLM([L.call("read_file", f"c{i}", path="a.txt") for i in range(3)] + [L.say("文件被锁住了，我换个办法。")])
    guard = RepeatGuard(limit=3)
    result = Agent(model, reg, guard=guard).run("读 a.txt")
    outs = [m["content"] for m in result.messages if m["role"] == "tool"]
    assert outs[:2] == ["ERROR: locked", "ERROR: locked"]
    assert outs[2] == "DENIED: repeated identical call 3 times without progress; change the approach instead of retrying"
    assert guard.log == ["read_file x3"]


def _broken():
    return [
        M.system("s"), M.user("u"),
        M.assistant(None, [ToolCall("t1", "a", {}), ToolCall("t2", "b", {})]),
        M.tool_result("t1", "A"),
        M.tool_result("zzz", "orphan"),
        M.user("继续"),
        M.assistant(None, [ToolCall("t3", "c", {})]),
    ]


def test_修复配对_缺的补占位_孤儿结果删掉():
    msgs = _broken()
    fixed = repair_pairs(msgs)
    assert [(m["role"], m.get("tool_call_id")) for m in fixed] == [
        ("system", None), ("user", None), ("assistant", None), ("tool", "t1"), ("tool", "t2"), ("user", None), ("assistant", None), ("tool", "t3")]
    assert fixed[4]["content"] == MISSING_RESULT and fixed[-1]["content"] == MISSING_RESULT
    assert len(msgs) == 7, "不修改传入的列表"


def test_跨厂商接管_带走文字_丢掉凭证_重新生成标识符():
    a = M.assistant("我先查天气。", [ToolCall("call_XyZ", "get_weather", {"city": "温哥华"})], reasoning="用户要温哥华的天气。")
    a["reasoning_signature"] = "EqQBCkgIARABGAIiQ..."
    msgs = [M.user("温哥华天气？"), a, M.tool_result("call_XyZ", "多云 12℃")]
    out = handoff(msgs)
    assert out[1]["content"] == "[earlier reasoning] 用户要温哥华的天气。\n我先查天气。"
    assert "reasoning_content" not in out[1] and "reasoning_signature" not in out[1]
    assert out[1]["tool_calls"][0]["id"] == "h1" and out[2]["tool_call_id"] == "h1"
    assert msgs[1]["tool_calls"][0]["id"] == "call_XyZ" and "reasoning_signature" in msgs[1], "原轨迹不变"
    b = handoff([M.assistant(None, [ToolCall("x", "t", {})], reasoning="想一想")])
    assert b[0]["content"] == "[earlier reasoning] 想一想"
