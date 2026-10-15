"""检查点 2.2：前缀缓存与上下文体检。运行：pytest tests/test_ch02_cache.py"""
from mini_agent import messages as M
from mini_agent.builtin import basic_registry
from mini_agent.context import CacheMeter, common_prefix_len, diagnose

TOOLS = basic_registry().schemas()


def test_最长公共前缀():
    assert common_prefix_len([], ["a"]) == 0
    assert common_prefix_len(list("abcd"), list("abxd")) == 2
    assert common_prefix_len(list("abc"), list("abcdef")) == 3


def conversation(system_prompt_for_turn):
    """模拟 4 轮请求，每轮追加一对 assistant/tool。system_prompt_for_turn(i) 决定第 i 轮的系统提示词。"""
    trajectory = [M.user("帮我把这些金额都换算成美元")]
    meter = CacheMeter()
    for i in range(4):
        meter.observe([M.system(system_prompt_for_turn(i)), *trajectory], TOOLS)
        trajectory += [M.assistant(f"第 {i} 轮的思考与调用"), M.tool_result(f"c{i}", f"第 {i} 轮工具返回的一大段结果 " * 5)]
    return meter


def test_只追加时后续请求几乎全部命中():
    meter = conversation(lambda i: "你是财务助理。")
    first, *rest = meter.history
    assert first["cached"] == 0 and first["computed"] == first["total"]
    for prev, cur in zip(meter.history, rest):
        assert cur["cached"] == prev["total"], "只追加时，上一次请求整个都应该命中"
    assert meter.hit_rate > 0.6


def test_系统提示词里写时间戳会让缓存大面积失效():
    good = conversation(lambda i: "你是财务助理。")
    bad = conversation(lambda i: f"你是财务助理。当前时间 10:30:0{i}")
    hits = [h["cached"] for h in bad.history[1:]]
    computed = [h["computed"] for h in bad.history[1:]]
    assert len(set(hits)) == 1, "命中量停在时间戳之前，不再随对话增长"
    assert computed == sorted(computed) and computed[0] < computed[-1], "时间戳之后的整段历史每轮都要重算，越来越多"
    assert bad.cost > good.cost * 1.4


def test_体检_发现常见错误():
    sys_a, sys_b = M.system("A"), M.system("B")
    t = [M.user("q"), M.assistant("a"), M.tool_result("c", "r")]
    rev = list(reversed(TOOLS))
    assert diagnose([sys_a, *t], TOOLS, [sys_a, *t, M.user("q2")], TOOLS) == []
    assert diagnose([sys_a, *t], TOOLS, [sys_b, *t], TOOLS) == ["system_changed"]
    assert diagnose([sys_a, *t], TOOLS, [sys_a, *t], rev) == ["tools_reordered"]
    assert diagnose([sys_a, *t], TOOLS, [sys_a, *t], TOOLS[:1]) == ["tools_changed"]
    assert diagnose([sys_a, *t], TOOLS, [sys_a, *t[1:], M.user("q2")], TOOLS) == ["history_rewritten"], "滑动窗口丢掉了最早的消息"
    edited = [M.user("q"), M.assistant("a"), M.tool_result("c", "r（截短）")]
    assert diagnose([sys_a, *t], TOOLS, [sys_a, *edited], TOOLS) == ["history_rewritten"], "原地截短旧工具结果也算改写历史"
