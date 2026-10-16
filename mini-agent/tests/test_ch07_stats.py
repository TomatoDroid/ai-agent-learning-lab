"""检查点 7.3：置信区间、配对检验、护栏优先的 AB 决策。运行：pytest tests/test_ch07_stats.py"""
import pytest

from mini_agent.stats import ab_decide, ci95, mcnemar, n_for_margin, paired_bootstrap

# ---------- 7.3a ----------


def test_原书例子_100道题70分_区间约正负9():
    p, lo, hi = ci95(70, 100)
    assert p == 0.7
    assert hi - p == pytest.approx(0.0898, abs=0.001) and p - lo == pytest.approx(0.0898, abs=0.001)
    assert lo < 0.73 < hi, "73% 落在 70% 的区间里：单看这两个数分不出好坏"


def test_区间截断到0到1():
    assert ci95(0, 10) == (0.0, 0.0, 0.0)
    assert ci95(10, 10)[2] == 1.0
    _, lo, hi = ci95(1, 10)
    assert lo == 0.0 and hi < 1
    with pytest.raises(ValueError):
        ci95(0, 0)


def test_所需样本量():
    assert n_for_margin(0.7, 0.09) == 100
    assert n_for_margin(0.7, 0.03) == 897
    assert n_for_margin(0.5, 0.05) == 385


# ---------- 7.3b ----------

def runs(both_pass, a_only, b_only, both_fail):
    a = [True] * both_pass + [True] * a_only + [False] * b_only + [False] * both_fail
    b = [True] * both_pass + [False] * a_only + [True] * b_only + [False] * both_fail
    return a, b


def test_同样提升3个点_不一致对的结构决定是否显著():
    # 两种情况都是 70% → 73%
    a, b = runs(70, 0, 3, 27)
    r = mcnemar(a, b)
    assert (r.b_only, r.a_only) == (3, 0) and r.p_value == pytest.approx(0.25)
    a, b = runs(57, 13, 16, 14)
    assert sum(a) == 70 and sum(b) == 73
    assert mcnemar(a, b).p_value > 0.5, "B 多对了 16 道、又多错了 13 道：基本是抛硬币"


def test_一边倒的不一致对才显著():
    a, b = runs(60, 0, 10, 30)
    assert mcnemar(a, b).p_value == pytest.approx(2 / 1024)
    assert mcnemar([True, False], [True, False]).p_value == 1.0
    assert mcnemar(*runs(0, 5, 5, 0)).p_value == 1.0
    with pytest.raises(ValueError):
        mcnemar([True], [True, False])


def test_配对自助法():
    a, b = runs(60, 0, 10, 30)
    diff, lo, hi = paired_bootstrap([float(x) for x in a], [float(x) for x in b], seed=1)
    assert diff == pytest.approx(0.1) and 0 < lo < diff < hi
    a, b = runs(57, 13, 16, 14)
    _, lo, hi = paired_bootstrap([float(x) for x in a], [float(x) for x in b])
    assert lo < 0 < hi
    assert paired_bootstrap([0.0, 1.0], [1.0, 1.0], seed=3) == paired_bootstrap([0.0, 1.0], [1.0, 1.0], seed=3), "同一个种子可复现"


# ---------- 7.3c ----------

LIMITS = {"投诉率": 0.002, "p95延迟秒": 0.5}


def test_护栏越线就停_目标再好也不行():
    assert ab_decide((0.05, 0.03, 0.07), {"投诉率": 0.004, "p95延迟秒": 0.1}, LIMITS) == "stop:投诉率"
    assert ab_decide((0.05, 0.03, 0.07), {"投诉率": 0.0, "p95延迟秒": 0.8}, LIMITS) == "stop:p95延迟秒"


def test_目标指标看区间():
    ok = {"投诉率": 0.001, "p95延迟秒": 0.2}
    assert ab_decide((0.02, 0.005, 0.035), ok, LIMITS) == "ship"
    assert ab_decide((-0.02, -0.035, -0.005), ok, LIMITS) == "reject"
    assert ab_decide((0.01, -0.004, 0.024), ok, LIMITS) == "inconclusive", "点估计为正但区间跨 0，不能上线"
    assert ab_decide((0.01, 0.001, 0.02), {}, LIMITS) == "ship"


def test_没有阈值的护栏报错():
    with pytest.raises(KeyError):
        ab_decide((0.01, 0.001, 0.02), {"成本": 0.1}, LIMITS)
