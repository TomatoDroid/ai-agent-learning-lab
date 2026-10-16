"""跨会话的用户记忆（练习 3.1）。

对应原书第三章“用户记忆系统”。这里实现的是简化版 Advanced JSON Cards：
每张卡片除了 key/value，还记录“为谁”（person、relationship）、“为什么”（backstory）、
“何时”（ts）和“从哪来”（source）。

两个设计决定都来自书里：
1. 只追加、不覆盖（Mem0 v3 的思路）：“住在北京”和后来的“搬到上海”两张卡都保留，
   读取时按时间取最新。错误的 UPDATE/DELETE 会不可逆地丢失历史，追加不会。
2. 记忆在会话开始时渲染进系统提示词，整个会话内不变：这是静态前缀的一部分（2.2 课）。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import messages as M

# 绝不写进长期记忆的东西：凭证类信息。（书中的隐私原则：记忆要有选择性。）
SECRET_KEYS = re.compile(r"password|passcode|pin|cvv|otp|密码|验证码", re.IGNORECASE)


@dataclass
class Card:
    key: str                    # 如 "home_city"、"doctor"、"passport.expiry"
    value: str
    person: str = "user"        # 这条信息是关于谁的
    relationship: str = "self"  # 此人与用户的关系：self / father / spouse …
    backstory: str = ""         # 为什么会有这条记忆（获取时的情境）
    ts: str = ""                # ISO 日期或时间，字符串比较即时间先后
    source: str = ""            # 证据来源，如 "session-2025-01-03"


@dataclass
class MemoryStore:
    cards: list[Card] = field(default_factory=list)

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def history(self, key: str, person: str = "user") -> list[Card]:
        return [c for c in self.cards if c.key == key and c.person == person]

    def current(self, key: str, person: str = "user") -> Card | None:
        """返回 (key, person) 的当前值：ts 最大的那张卡；ts 相同时取后加入的。没有则返回 None。"""
        # TODO 练习 3.1a：读取当前值
        # 提示：遍历 self.history(key, person)，用 >= 比较 ts，这样相同 ts 时后加入的会胜出。
        raise NotImplementedError("练习 3.1a 还没有完成：读取当前值")

    def render(self) -> str:
        """把当前记忆渲染成一段放进系统提示词的文本。格式：

        <user_memory>
        - user (self) diet: vegetarian  [2025-01-03; 订机票时说要素食餐]
        - Zhang (dentist) phone: 138…  [2025-02-01]
        </user_memory>

        规则：
        - 每个 (person, key) 只出现一次，取 current() 的值；
        - 先按 person 排序（"user" 永远排第一），同一 person 内按 key 排序，保证字节级稳定；
        - 方括号里是 ts，backstory 非空时加 "; backstory"；
        - 这个 (person, key) 有被取代的旧值时，行尾加 " (updated; was: 旧值)"，旧值取上一张；
        - 没有任何卡片时返回空字符串。
        """
        # TODO 练习 3.1a：渲染
        # 提示：先收集所有 (person, key) 对，排序键可以用 (person != "user", person, key)。
        # 提示：旧值 = 按 ts 排序后 history 的倒数第二张（排序要稳定：sorted 是稳定的）。
        raise NotImplementedError("练习 3.1a 还没有完成：渲染")

    # —— 持久化：JSON Lines，只追加（原始证据层的写法）——
    def save(self, path: str | Path) -> None:
        Path(path).write_text("".join(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in self.cards), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "MemoryStore":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls([Card(**json.loads(line)) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()])


EXTRACT_PROMPT = """You maintain long-term memory about a user. From the conversation below, extract facts that
will still be useful in future sessions. Be selective (skip transient details such as search results),
abstract (turn one-off choices into lasting preferences), and structured.
Reply with ONLY a JSON array of objects with keys: key, value, person, relationship, backstory.
Never extract passwords, PINs or other credentials.

Conversation:
{conversation}"""


def extract_memories(llm, conversation: str, *, ts: str, source: str) -> list[Card]:
    """会话结束后，用一次额外的 LLM 调用把对话提炼成卡片。

    调用 llm.complete([M.user(EXTRACT_PROMPT.format(conversation=conversation))], tools=[])，
    从回复的 content 里解析 JSON 数组，然后：
    1. 模型可能在 JSON 前后加说明文字或 ```json 代码块：取第一个 "[" 到最后一个 "]" 之间的部分解析；
       找不到或解析失败时返回 []（宁可这次不记，也不要写入垃圾）。
    2. 只保留同时有非空字符串 key 和 value 的对象；person 缺省为 "user"，relationship 缺省为 "self"，
       backstory 缺省为 ""。
    3. key 或 value 命中 SECRET_KEYS 的一律丢弃：凭证不进长期记忆。
    4. 每张卡片的 ts、source 用参数填写（来源可追溯）。
    """
    # TODO 练习 3.1b：提取与校验
    # 提示：reply = llm.complete(...)；文本在 reply.content。
    # 提示：start, end = text.find("["), text.rfind("]")；json.loads(text[start:end + 1])。
    raise NotImplementedError("练习 3.1b 还没有完成：提取与校验")


# —— 日志脱敏（实验 3-3 的“正则快速过滤”那一层）——
PII_PATTERNS = [
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("ID", r"(?<!\d)\d{17}[\dXx](?!\d)"),
    ("CARD", r"(?<!\d)\d(?:[ -]?\d){15,18}(?!\d)"),
    ("PHONE", r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ("SECRET", r"(?:密码|password|pin)\s*(?:是|为|:|：|is)?\s*\S+"),
]


def redact(text: str) -> str:
    """按 PII_PATTERNS 的顺序，把命中的片段替换为 [类型]，如 "[EMAIL]"、"[SECRET]"。不区分大小写。

    顺序很重要：身份证号（18 位）要在银行卡号之前替换，否则会被当成卡号。
    这只是第一道快速过滤；书中的做法是再用本地小模型处理正则抓不住的自然语言表达。
    """
    # TODO 练习 3.1c：日志脱敏
    # 提示：for name, pattern in PII_PATTERNS: text = re.sub(pattern, f"[{name}]", text, flags=re.IGNORECASE)
    raise NotImplementedError("练习 3.1c 还没有完成：日志脱敏")
