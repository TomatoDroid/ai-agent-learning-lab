"""检查点 7.1：Pass@k 与 Pass^k、分层验证器、每次重置环境的多次试验。运行：pytest tests/test_ch07_evals.py"""
import pytest

from mini_agent import llm as L
from mini_agent.agent import Agent
from mini_agent.evals import MINI_SUITE, SUITE_SYSTEM_PROMPT, EvalTask, pass_at_k, pass_hat_k, run_suite, verify

# ---------- 7.1a Pass@k 与 Pass^k ----------


def test_原书例子_单次成功率60_k等于5():
    # 理论值：Pass@5 = 1 - 0.4^5 ≈ 99.0%，Pass^5 = 0.6^5 ≈ 7.8%。用很大的 n 逼近
    n, c = 1000, 600
    assert pass_at_k(n, c, 5) == pytest.approx(1 - 0.4 ** 5, abs=0.002)
    assert pass_hat_k(n, c, 5) == pytest.approx(0.6 ** 5, abs=0.002)


def test_无偏估计的精确值():
    # 5 次里过 3 次：随机抽 2 次全失败的概率 C(2,2)/C(5,2) = 1/10；全成功的概率 C(3,2)/C(5,2) = 3/10
    assert pass_at_k(5, 3, 2) == pytest.approx(0.9)
    assert pass_hat_k(5, 3, 2) == pytest.approx(0.3)
    assert pass_at_k(5, 3, 1) == pytest.approx(0.6) == pass_hat_k(5, 3, 1)


def test_边界():
    assert pass_at_k(5, 4, 2) == 1.0, "只有 1 次失败，抽 2 次不可能全是失败"
    assert pass_at_k(5, 0, 3) == 0.0 and pass_hat_k(5, 5, 3) == 1.0
    with pytest.raises(ValueError):
        pass_at_k(3, 1, 4)
    with pytest.raises(ValueError):
        pass_hat_k(3, 1, 4)


# ---------- 7.1b 分层验证器 ----------

TASK = EvalTask("t", "退款", {}, lambda s: None,
                env_assertions=[("orders.A1.status", "refunded")], actions=["get_order", "refund_order"],
                communicate_info=["A1", "59"])


def test_全部通过():
    v = verify(TASK, {"orders": {"A1": {"status": "refunded"}}}, ["get_order", "refund_order"], "A1 已退款 59 元")
    assert v.passed and v.reward == 1.0 and v.failures == []
    assert v.checks == {"ENV_ASSERTION": True, "ACTION": True, "COMMUNICATE": True}


def test_结果对过程违规_只按环境计分时仍得分但违规被记录():
    # 原书 τ²-bench 例子：reward_basis 只有 ENV_ASSERTION，一次并发调用两个工具的违规没有被扣分
    v = verify(TASK, {"orders": {"A1": {"status": "refunded"}}}, ["refund_order"], "A1 已退款 59 元")
    assert v.reward == 1.0
    assert v.checks["ACTION"] is False and v.failures == ["ACTION: 缺少 get_order"]


def test_把过程加入reward_basis就会扣分():
    strict = EvalTask(**{**TASK.__dict__, "reward_basis": ("ENV_ASSERTION", "ACTION")})
    v = verify(strict, {"orders": {"A1": {"status": "refunded"}}}, ["refund_order", "get_order"], "A1 59")
    assert v.reward == 0.0, "顺序反了：先退款后查询，同样算违规"
    assert v.failures == ["ACTION: 缺少 refund_order"]


def test_动作是子序列_中间可以夹别的调用():
    v = verify(TASK, {"orders": {"A1": {"status": "refunded"}}}, ["list_orders", "get_order", "get_order", "refund_order"], "A1 59")
    assert v.checks["ACTION"]


def test_环境断言的失败信息():
    v = verify(TASK, {"orders": {"A1": {"status": "shipped"}}}, ["get_order", "refund_order"], None)
    assert v.reward == 0.0
    assert v.failures == ["ENV_ASSERTION: orders.A1.status = 'shipped'，期望 'refunded'",
                          "COMMUNICATE: 没有说 A1", "COMMUNICATE: 没有说 59"]
    v = verify(TASK, {"orders": {}}, [], "")
    assert v.failures[0] == "ENV_ASSERTION: orders.A1.status = <缺失>，期望 'refunded'"


# ---------- 7.1c 多次试验 ----------

def scripted_agents(*scripts):
    it = iter(scripts)
    return lambda reg: Agent(L.ScriptedLLM(list(next(it))), reg, SUITE_SYSTEM_PROMPT)


GOOD = [L.call("get_order", "c1", order_id="A1001"), L.call("refund_order", "c2", order_id="A1001", reason="坏了"),
        L.say("订单 A1001 已退款 59.0 元。")]
LAZY = [L.say("订单 A1001 已退款 59.0 元。")]  # 只嘴上说做了


def test_每次试验都从干净的环境开始():
    refund = MINI_SUITE[0]
    report = run_suite(scripted_agents(GOOD, LAZY), [refund], trials=2)
    assert [t.verdict.passed for t in report.trials] == [True, False], "第二次什么都没做，不能沾第一次的光"
    assert refund.initial_state["orders"]["A1001"]["status"] == "delivered", "任务定义本身不能被改"
    assert report.trials[1].verdict.failures[0].startswith("ENV_ASSERTION: orders.A1001.status = 'delivered'")
    assert report.trials[0].tool_calls == ["get_order", "refund_order"] and report.trials[0].trial == 0


def test_每次试验都是新的Agent():
    seen = []

    def make(reg):
        agent = Agent(L.ScriptedLLM(list(LAZY)), reg, SUITE_SYSTEM_PROMPT)
        seen.append(agent)
        return agent

    run_suite(make, [MINI_SUITE[0]], trials=3)
    assert len({id(a) for a in seen}) == 3
    assert all(len(a.history) <= 3 for a in seen), "历史里不应该有上一次试验的对话"


def test_崩溃记为失败并继续():
    report = run_suite(scripted_agents([], GOOD), [MINI_SUITE[0]], trials=2)  # 第一个剧本是空的：模型调用会抛异常
    first, second = report.trials
    assert (first.stop_reason, first.verdict.reward) == ("error", 0.0)
    assert first.verdict.failures[0].startswith("ERROR:")
    assert set(first.verdict.checks.values()) == {False}
    assert second.verdict.passed


def test_报告汇总Pass_at_k与Pass_hat_k():
    report = run_suite(scripted_agents(GOOD, LAZY, GOOD, GOOD), [MINI_SUITE[0]], trials=4)
    assert report.by_task() == {"refund-basic": [True, False, True, True]}
    assert report.success_rate == 0.75
    assert report.pass_at(2) == 1.0
    assert report.pass_hat(2) == pytest.approx(3 / 6)


def test_陷阱题_已送达的订单不能取消():
    trap = MINI_SUITE[2]
    obey = [L.call("get_order", "c1", order_id="A1003"), L.say("订单 A1003 已送达，不能取消，可以为你办理退款。")]
    break_rule = [L.call("get_order", "c1", order_id="A1003"), L.call("cancel_order", "c2", order_id="A1003"), L.say("A1003 已取消")]
    report = run_suite(scripted_agents(obey, break_rule), [trap], trials=2)
    assert [t.verdict.passed for t in report.trials] == [True, False]


def test_结果可以保存给compare用(tmp_path):
    import json
    report = run_suite(scripted_agents(GOOD), [MINI_SUITE[0]], trials=1)
    path = tmp_path / "runs" / "a.json"
    report.save(str(path))
    row = json.loads(path.read_text(encoding="utf-8"))["trials"][0]
    assert (row["task"], row["trial"], row["passed"]) == ("refund-basic", 0, True)
