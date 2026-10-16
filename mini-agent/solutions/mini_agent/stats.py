"""统计显著性与 AB 决策（练习 7.3）。

对应原书第七章“评估驱动的模型选型”到章末。100 道题上 70% 对 73%，是真的变好了，还是噪声？

- 先看置信区间：成功率的标准误是 sqrt(p(1-p)/n)，100 道题、70% 时 95% 区间约为 ±9 个百分点；
- 两个版本跑的是同一批题，就该做配对检验：只有“一个对、一个错”的题（不一致对）携带差异信息；
- 上线决策要同时看目标指标和护栏指标：护栏越线就停，目标指标的区间整体大于 0 才上线。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

Z95 = 1.96

# ---------- 7.3a 置信区间与样本量 ----------


def ci95(successes: int, n: int) -> tuple[float, float, float]:
    """成功率的 95% 置信区间（正态近似）：返回 (p, lo, hi)，lo、hi 截断到 [0, 1]。n 为 0 时抛 ValueError。"""
    # >>> EXERCISE 7.3a 置信区间与所需样本量
    # HINT: se = sqrt(p * (1 - p) / n)，区间是 p ± 1.96 * se。
    if n <= 0:
        raise ValueError("样本量必须大于 0")
    p = successes / n
    half = Z95 * math.sqrt(p * (1 - p) / n)
    return p, max(0.0, p - half), min(1.0, p + half)
    # <<< EXERCISE


def n_for_margin(p: float, margin: float) -> int:
    """要让 95% 区间的半宽不超过 margin，至少需要多少道题（向上取整）。70% 想要 ±3 个点，需要约 897 道。"""
    # >>> EXERCISE 7.3a 置信区间与所需样本量
    return math.ceil(Z95 ** 2 * p * (1 - p) / margin ** 2)
    # <<< EXERCISE


# ---------- 7.3b 配对检验 ----------


@dataclass
class McNemar:
    b_only: int     # A 错、B 对的题数
    a_only: int     # A 对、B 错的题数
    p_value: float


def mcnemar(a: list[bool], b: list[bool]) -> McNemar:
    """精确 McNemar 检验：同一批题上 A、B 两个版本的通过情况（一一对应）。

    - 两边都对或都错的题不提供“谁更好”的信息，只数不一致对：b_only、a_only，n = 二者之和；
    - 原假设下每个不一致对偏向哪边是抛硬币，双侧 p 值 = min(1, 2 * Σ_{i=0..min(b_only, a_only)} C(n, i) / 2**n)；
    - n 为 0 时 p 值为 1.0；a、b 长度不同时抛 ValueError。
    """
    # >>> EXERCISE 7.3b 只看不一致对的精确配对检验
    # HINT: math.comb；sum(1 for x, y in zip(a, b) if …) 数不一致对。
    if len(a) != len(b):
        raise ValueError("配对检验要求两组结果一一对应")
    b_only = sum(1 for x, y in zip(a, b) if not x and y)
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    n = a_only + b_only
    if n == 0:
        return McNemar(b_only, a_only, 1.0)
    tail = sum(math.comb(n, i) for i in range(min(a_only, b_only) + 1)) / 2 ** n
    return McNemar(b_only, a_only, min(1.0, 2 * tail))
    # <<< EXERCISE


def paired_bootstrap(a: list[float], b: list[float], iters: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """配对自助法：按题重采样，估计 mean(b) - mean(a) 及其 95% 区间。返回 (diff, lo, hi)。"""
    if len(a) != len(b) or not a:
        raise ValueError("配对自助法要求两组非空且一一对应")
    rng = random.Random(seed)
    n = len(a)
    d = [y - x for x, y in zip(a, b)]
    diffs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return sum(d) / n, diffs[int(0.025 * iters)], diffs[min(iters - 1, int(0.975 * iters))]


# ---------- 7.3c AB 决策：先看护栏，再看目标 ----------


def ab_decide(goal: tuple[float, float, float], guardrails: dict[str, float], limits: dict[str, float]) -> str:
    """根据 AB 实验的结果给出决策。

    - goal：目标指标 B - A 的 (diff, lo, hi)，越大越好；
    - guardrails：护栏指标的变化 B - A，越大越差（投诉率、p95 延迟、单次成本……）；limits：每个护栏最多允许变差多少；
    - 先按 guardrails 的顺序检查：有一个超过对应 limit，就返回 "stop:<名字>"——护栏越线，目标再好也要停；
      guardrails 里出现 limits 没有的名字，抛 KeyError（没有阈值的护栏等于没有护栏）；
    - 护栏都没越线：lo > 0 返回 "ship"，hi < 0 返回 "reject"，区间跨过 0 返回 "inconclusive"（继续收集数据，而不是凭点估计上线）。
    机制指标（比如记忆命中率）上升本身不是上线理由，所以它不出现在参数里。
    """
    # >>> EXERCISE 7.3c 护栏优先的上线决策
    for name, change in guardrails.items():
        if change > limits[name]:
            return f"stop:{name}"
    _, lo, hi = goal
    if lo > 0:
        return "ship"
    if hi < 0:
        return "reject"
    return "inconclusive"
    # <<< EXERCISE
