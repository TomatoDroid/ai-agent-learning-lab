"""自动评判：Rubric 打分、配对比较与失败归因（练习 7.2）。

对应原书第七章“评估数据集的设计”到“配对比较与 Elo 排名”。

- 开放式回答没有标准答案，只能让评判模型按 Rubric 打分。Rubric 要分档、加权，还要有一票否决项；
- 两个系统谁更好，直接比较往往比各打一个绝对分更稳；但评判模型偏爱某个位置，所以要交换顺序再判一次；
- 失败归因要找“第一个错误”：从哪一步开始，后面再怎么补救也救不回来了。回归测试则可以只回放轨迹前缀，
  看模型下一步的动作是否落在可接受的动作集合里。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from . import messages as M

# ---------- 7.2a Rubric：分档、加权、一票否决 ----------

WEIGHTS = {"essential": 3, "important": 2, "optional": 1}


@dataclass
class Dimension:
    name: str
    weight: str                 # essential / important / optional / veto
    scoring: dict[str, str]     # 档位 → 可验证的判定标准；普通维度用 "4".."1"，否决项用 "pass" / "fail"


@dataclass
class RubricScore:
    total: float                          # 0..1
    vetoed: list[str] = field(default_factory=list)
    per_dimension: dict[str, float] = field(default_factory=dict)  # 每个普通维度归一化到 0..1 的得分


# 原书的例子：“我女儿的儿科医生是谁？”答案要跨两次对话关联（女儿叫 Lily；带 Lily 看了 Dr. Chen）
MEMORY_RUBRIC = [
    Dimension("事实正确性", "essential", {"4": "准确回答 Dr. Chen，且关联到女儿 Lily", "3": "准确回答 Dr. Chen，但未提及是 Lily 的医生",
                                      "2": "给出了正确医生但附带不确定的额外信息", "1": "给出错误医生名，或回答不知道"}),
    Dimension("信息完整性", "important", {"4": "主动补充相关信息（如上次就诊时间）", "3": "回答了核心问题，无遗漏",
                                      "2": "回答了核心问题，但遗漏了可用的关联信息", "1": "关键信息缺失"}),
    Dimension("思考正确性", "important", {"4": "正确关联“女儿=Lily”和“Lily 的医生=Dr. Chen”", "3": "关联正确但思考路径不够清晰",
                                      "2": "部分关联正确", "1": "错误关联（如把用户自己的医生当成女儿的医生）"}),
    Dimension("幻觉检测", "veto", {"pass": "所有信息均可溯源到历史对话记录", "fail": "编造了对话中不存在的信息"}),
]


def score_rubric(rubric: list[Dimension], grades: dict[str, int | str]) -> RubricScore:
    """把评判模型给出的各维度档位汇总成一个 0..1 的总分。

    - 普通维度：档位是 1..4 的整数，归一化为 (g - 1) / 3，按 WEIGHTS 加权平均；
    - 否决项（weight == "veto"）：档位是 "pass" 或 "fail"，不参与加权；任何一个 "fail"，total 直接为 0.0，
      并把它的名字记进 vetoed（per_dimension 照常算，方便看“其他维度其实不错”）；
    - grades 缺了某个维度，或档位不合法（普通维度不在 1..4、否决项不是 pass/fail），抛 ValueError：
      评判输出不完整时宁可报错，也不要悄悄当成 0 分或满分。
    """
    # >>> EXERCISE 7.2a 加权汇总 Rubric 档位，处理一票否决
    # HINT: 先逐个维度校验并计算，最后再看 vetoed 是否为空。
    per: dict[str, float] = {}
    vetoed: list[str] = []
    num = den = 0.0
    for d in rubric:
        if d.name not in grades:
            raise ValueError(f"缺少维度 {d.name} 的评分")
        g = grades[d.name]
        if d.weight == "veto":
            if g not in ("pass", "fail"):
                raise ValueError(f"否决项 {d.name} 的评分必须是 pass/fail，得到 {g!r}")
            if g == "fail":
                vetoed.append(d.name)
            continue
        if not isinstance(g, int) or isinstance(g, bool) or not 1 <= g <= 4:
            raise ValueError(f"维度 {d.name} 的评分必须是 1..4，得到 {g!r}")
        per[d.name] = (g - 1) / 3
        num += WEIGHTS[d.weight] * per[d.name]
        den += WEIGHTS[d.weight]
    total = 0.0 if vetoed or not den else num / den
    return RubricScore(total, vetoed, per)
    # <<< EXERCISE


def rubric_prompt(rubric: list[Dimension], question: str, answer: str, evidence: str) -> str:
    dims = "\n".join(f"- {d.name}（{d.weight}）：" + "；".join(f"{k}={v}" for k, v in d.scoring.items()) for d in rubric)
    keys = ", ".join(json.dumps(d.name, ensure_ascii=False) + (': "pass"' if d.weight == "veto" else ": 3") for d in rubric)
    return (f"你是严格的评审。只根据下面的依据材料判断回答，长度不是加分项。\n\n依据材料：\n{evidence}\n\n问题：{question}\n"
            f"回答：{answer}\n\n评分维度：\n{dims}\n\n先逐项写一句理由，最后单独输出一行 JSON，如 {{{keys}}}。")


def parse_grades(text: str) -> dict:
    """从评判模型的输出里取出最后一个 JSON 对象。取不到抛 ValueError。"""
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text or ""))):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    raise ValueError("评判输出里没有 JSON 评分")


def rubric_judge(llm, rubric: list[Dimension], question: str, answer: str, evidence: str) -> RubricScore:
    reply = llm.complete([M.user(rubric_prompt(rubric, question, answer, evidence))], tools=[])
    return score_rubric(rubric, parse_grades(reply.content))


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def length_bias(answers: list[str], scores: list[float]) -> float:
    """定期审计：评分和回答长度的相关系数。接近 1 说明评判被长度带偏了。"""
    return pearson([len(a) for a in answers], scores)


# ---------- 7.2b 配对比较：交换位置，Elo ----------

PAIR_PROMPT = ("比较两个回答哪个更好地解决了问题。不要因为更长或排在前面而偏向它。\n\n问题：{q}\n\n回答 A：{a}\n\n回答 B：{b}\n\n"
               "只输出一个词：A、B 或 平局。")


def parse_choice(text: str | None) -> str:
    """'A' / 'B' / 'tie'：以 A 或 B 开头算选择，其他都算平局。"""
    t = (text or "").strip().upper()
    return t[0] if t[:1] in ("A", "B") else "tie"


def pairwise(llm, question: str, a: str, b: str) -> str:
    """让评判模型比较 a 和 b，返回 "a"、"b" 或 "tie"。

    评判模型有位置偏差，所以要判两次：
    - 第一次 a 放在“回答 A”、b 放在“回答 B”；
    - 第二次交换：b 放在“回答 A”、a 放在“回答 B”；
    用 PAIR_PROMPT.format(q=…, a=…, b=…) 生成提示，llm.complete([messages.user(提示)], tools=[]) 调用，parse_choice 解析。
    两次都指向同一个回答才算它赢；两次结论矛盾（说明在跟着位置走）或有平局，都返回 "tie"。
    """
    # >>> EXERCISE 7.2b 交换位置判两次，矛盾记为平局
    # HINT: 把两次的 A/B 都翻译成 "a"/"b"（第二次要反过来翻译），再比较。
    first = parse_choice(llm.complete([M.user(PAIR_PROMPT.format(q=question, a=a, b=b))], tools=[]).content)
    second = parse_choice(llm.complete([M.user(PAIR_PROMPT.format(q=question, a=b, b=a))], tools=[]).content)
    one = {"A": "a", "B": "b"}.get(first, "tie")
    two = {"A": "b", "B": "a"}.get(second, "tie")
    return one if one == two else "tie"
    # <<< EXERCISE


def elo_expected(ra: float, rb: float) -> float:
    """A 对 B 的期望胜率：1 / (1 + 10 ** ((rb - ra) / 400))。1200 对 1000 约为 0.76。"""
    # >>> EXERCISE 7.2b 交换位置判两次，矛盾记为平局
    return 1 / (1 + 10 ** ((rb - ra) / 400))
    # <<< EXERCISE


def elo_update(ra: float, rb: float, score_a: float, k: float = 32) -> tuple[float, float]:
    """一场比赛后更新两边的分数。score_a：A 赢 1、平 0.5、输 0。A 涨多少，B 就跌多少。"""
    # >>> EXERCISE 7.2b 交换位置判两次，矛盾记为平局
    delta = k * (score_a - elo_expected(ra, rb))
    return ra + delta, rb - delta
    # <<< EXERCISE


def elo_ratings(matches: list[tuple[str, str, float]], k: float = 32, start: float = 1000) -> dict[str, float]:
    """按顺序回放比赛 (a, b, score_a)。注意：同一批比赛换个顺序，Elo 的结果就会变。"""
    r: dict[str, float] = {}
    for a, b, s in matches:
        r[a], r[b] = elo_update(r.get(a, start), r.get(b, start), s, k)
    return r


# ---------- 7.2c 前缀回归与第一个错误 ----------

@dataclass
class PrefixCase:
    """轨迹前缀回归用例：给定到某一步为止的消息，下一步可接受的动作集合。

    动作标签："tool:<名字>" 表示调用该工具，"tool:*" 表示任意工具；"ask" 表示向用户提问；"say" 表示直接回答。
    """
    id: str
    messages: list[dict]
    allowed: set[str]
    note: str = ""


@dataclass
class PrefixVerdict:
    ok: bool
    actions: list[str]
    reason: str = ""


def action_labels(reply) -> list[str]:
    """把模型的一次回复翻译成动作标签：有工具调用时每个调用一个 "tool:名字"；否则文本里有问号算 "ask"，没有算 "say"。"""
    if reply.tool_calls:
        return [f"tool:{c.name}" for c in reply.tool_calls]
    text = reply.content or ""
    return ["ask"] if ("?" in text or "？" in text) else ["say"]


def check_prefix(case: PrefixCase, reply) -> PrefixVerdict:
    """判断模型在这个前缀之后的下一步是否可以接受。

    每个动作标签都必须被 allowed 允许："tool:x" 被 "tool:x" 或 "tool:*" 允许，"ask"/"say" 只被同名标签允许。
    全部允许时 ok=True、reason=""；否则 ok=False，reason 写 "不在可接受集合：tool:refund_order"（第一个不允许的标签）。
    """
    # >>> EXERCISE 7.2c 前缀回归：下一步是否落在可接受动作集合里
    # HINT: 先用 action_labels(reply) 得到标签。
    labels = action_labels(reply)
    for label in labels:
        if label in case.allowed or (label.startswith("tool:") and "tool:*" in case.allowed):
            continue
        return PrefixVerdict(False, labels, f"不在可接受集合：{label}")
    return PrefixVerdict(True, labels)
    # <<< EXERCISE


def run_prefix_regression(llm, cases: list[PrefixCase], tools: list[dict] | None = None) -> list[PrefixVerdict]:
    """每个用例只调一次模型：比端到端重跑便宜得多，也不受前面步骤随机性的影响。"""
    return [check_prefix(c, llm.complete(c.messages, tools=tools or [])) for c in cases]


def first_error(n: int, rescuable: Callable[[int], bool]) -> int:
    """找轨迹里的第一个错误步骤（1..n）。

    rescuable(i)：保留前 i 步、从第 i+1 步起换成正确做法，任务还能不能成功。约定 rescuable(0) 为 True、rescuable(n) 为 False，
    并且一旦救不回来，之后也救不回来（单调）。返回最小的 i 使 rescuable(i) 为 False——第 i 步就是第一个错误。
    每次 rescuable 都要重放一段轨迹，代价很高，所以用二分查找，只调用约 log2(n) 次。
    """
    # >>> EXERCISE 7.2c 前缀回归：下一步是否落在可接受动作集合里
    # HINT: 维持 lo（可救）和 hi（不可救），每次试中点。
    lo, hi = 0, n
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if rescuable(mid):
            lo = mid
        else:
            hi = mid
    return hi
    # <<< EXERCISE
