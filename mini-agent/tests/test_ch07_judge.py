"""检查点 7.2：Rubric 加权与一票否决、交换位置的配对比较与 Elo、前缀回归与第一个错误。运行：pytest tests/test_ch07_judge.py"""
import pytest

from mini_agent import llm as L
from mini_agent import messages as M
from mini_agent.judge import (MEMORY_RUBRIC, PrefixCase, check_prefix, elo_expected, elo_ratings, elo_update, first_error,
                              length_bias, pairwise, parse_grades, rubric_judge, run_prefix_regression, score_rubric)

# ---------- 7.2a Rubric ----------

GOOD = {"事实正确性": 4, "信息完整性": 3, "思考正确性": 4, "幻觉检测": "pass"}


def test_加权平均():
    s = score_rubric(MEMORY_RUBRIC, GOOD)
    # (3×1 + 2×2/3 + 2×1) / 7
    assert s.total == pytest.approx((3 + 4 / 3 + 2) / 7)
    assert s.vetoed == [] and s.per_dimension["信息完整性"] == pytest.approx(2 / 3)
    assert score_rubric(MEMORY_RUBRIC, {**GOOD, "信息完整性": 4}).total == 1.0
    assert score_rubric(MEMORY_RUBRIC, {"事实正确性": 1, "信息完整性": 1, "思考正确性": 1, "幻觉检测": "pass"}).total == 0.0


def test_必要项比重要项更重():
    miss_essential = score_rubric(MEMORY_RUBRIC, {**GOOD, "事实正确性": 1, "信息完整性": 4})
    miss_important = score_rubric(MEMORY_RUBRIC, {**GOOD, "思考正确性": 1, "信息完整性": 4})
    assert miss_essential.total < miss_important.total


def test_一票否决():
    s = score_rubric(MEMORY_RUBRIC, {**GOOD, "信息完整性": 4, "幻觉检测": "fail"})
    assert s.total == 0.0 and s.vetoed == ["幻觉检测"]
    assert s.per_dimension["事实正确性"] == 1.0, "其他维度照常记录"


@pytest.mark.parametrize("bad", [{"事实正确性": 4, "信息完整性": 3, "思考正确性": 4},
                                 {**GOOD, "事实正确性": 5}, {**GOOD, "事实正确性": 0},
                                 {**GOOD, "事实正确性": "4"}, {**GOOD, "幻觉检测": 4}])
def test_评判输出不完整就报错(bad):
    with pytest.raises(ValueError):
        score_rubric(MEMORY_RUBRIC, bad)


def test_rubric_judge端到端():
    reply = '事实正确：答出 Dr. Chen……\n{"事实正确性": 4, "信息完整性": 3, "思考正确性": 4, "幻觉检测": "pass"}'
    judge = L.ScriptedLLM([L.say(reply)])
    s = rubric_judge(judge, MEMORY_RUBRIC, "我女儿的儿科医生是谁？", "是 Dr. Chen。", "会话1：女儿叫 Lily\n会话2：带 Lily 看了 Dr. Chen")
    assert s.total == pytest.approx((3 + 4 / 3 + 2) / 7)
    prompt = judge.calls[0]["messages"][0]["content"]
    assert "幻觉检测" in prompt and "Dr. Chen" in prompt and "长度不是加分项" in prompt
    with pytest.raises(ValueError):
        parse_grades("没有 JSON")


def test_长度偏差审计():
    answers = ["短", "中等长度的回答", "一个非常非常长、什么都写了一点的回答"]
    assert length_bias(answers, [0.2, 0.5, 0.9]) > 0.9
    assert abs(length_bias(answers, [0.5, 0.9, 0.5])) < 0.5


# ---------- 7.2b 配对比较 ----------

def test_两次一致才算赢():
    judge = L.ScriptedLLM([L.say("A"), L.say("B")])  # 第一次 a 在前选 A；第二次 a 在后选 B：都指向 a
    assert pairwise(judge, "问题", "回答甲", "回答乙") == "a"
    first, second = (c["messages"][0]["content"] for c in judge.calls)
    assert first.index("回答甲") < first.index("回答乙") and second.index("回答乙") < second.index("回答甲")
    assert pairwise(L.ScriptedLLM([L.say("B"), L.say("A")]), "q", "x", "y") == "b"


def test_位置偏差记为平局():
    assert pairwise(L.ScriptedLLM([L.say("A"), L.say("A")]), "q", "x", "y") == "tie", "总选排在前面的那个"
    assert pairwise(L.ScriptedLLM([L.say("A"), L.say("平局")]), "q", "x", "y") == "tie"


def test_elo():
    assert elo_expected(1200, 1000) == pytest.approx(0.76, abs=0.01)
    assert elo_expected(1000, 1000) == 0.5
    ra, rb = elo_update(1000, 1000, 1)
    assert (ra, rb) == (1016, 984)
    ra, rb = elo_update(1200, 1000, 1)
    assert ra - 1200 == pytest.approx(32 * (1 - elo_expected(1200, 1000))) and ra + rb == 2200, "强者赢了只涨一点，总分守恒"


def test_elo对比赛顺序敏感():
    games = [("x", "y", 1), ("y", "z", 1), ("z", "x", 1), ("x", "y", 0)]
    assert elo_ratings(games) != elo_ratings(list(reversed(games)))


# ---------- 7.2c 前缀回归与第一个错误 ----------

PREFIX = [M.system("客服"), M.user("我是 lily，A1003 帮我取消")]
CASE = PrefixCase("cancel-check-first", PREFIX, {"tool:get_order", "ask"})


def test_前缀回归_可接受动作集合():
    assert check_prefix(CASE, L.call("get_order", "c", order_id="A1003")).ok
    assert check_prefix(CASE, L.say("请问你要取消的是哪件商品？")).ok
    bad = check_prefix(CASE, L.call("cancel_order", "c", order_id="A1003"))
    assert (bad.ok, bad.actions, bad.reason) == (False, ["tool:cancel_order"], "不在可接受集合：tool:cancel_order")
    assert not check_prefix(CASE, L.say("好的，已经取消了。")).ok


def test_前缀回归_通配与并行调用():
    any_tool = PrefixCase("x", PREFIX, {"tool:*"})
    assert check_prefix(any_tool, L.call("whatever", "c")).ok
    assert not check_prefix(any_tool, L.say("好")).ok
    both = L.calls(M.ToolCall("1", "get_order", {}), M.ToolCall("2", "cancel_order", {}))
    v = check_prefix(CASE, both)
    assert not v.ok and v.actions == ["tool:get_order", "tool:cancel_order"]


def test_前缀回归每个用例只调一次模型():
    llm = L.ScriptedLLM([L.call("get_order", "c", order_id="A1003"), L.say("已取消")])
    verdicts = run_prefix_regression(llm, [CASE, CASE])
    assert [v.ok for v in verdicts] == [True, False] and len(llm.calls) == 2


def test_二分找第一个错误():
    # 原书 AndroidWorld 记账例子：第 8 步之后再怎么补救都救不回来
    asked = []

    def rescuable(i):
        asked.append(i)
        return i < 8

    assert first_error(20, rescuable) == 8
    assert len(asked) <= 5, f"应该二分，实际试了 {asked}"
    assert first_error(1, lambda i: False) == 1
    assert first_error(10, lambda i: i < 10) == 10
