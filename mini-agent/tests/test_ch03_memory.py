"""检查点 3.1：用户记忆。运行：pytest tests/test_ch03_memory.py"""
from mini_agent import llm as L
from mini_agent.agent import Agent
from mini_agent.memory import Card, MemoryStore, extract_memories, redact
from mini_agent.tools import ToolRegistry


def _store():
    s = MemoryStore()
    s.add(Card("home_city", "北京", ts="2025-01-03", source="s1"))
    s.add(Card("diet", "vegetarian", backstory="订机票时要素食餐", ts="2025-01-03", source="s1"))
    s.add(Card("home_city", "上海", backstory="说自己刚搬家", ts="2025-03-10", source="s2"))
    s.add(Card("doctor", "张医生（牙科）", person="user", ts="2025-02-01", source="s3"))
    s.add(Card("doctor", "张医生（心脏科）", person="Father", relationship="father", ts="2025-02-01", source="s3"))
    return s


def test_只追加_按时间取当前值_历史仍在():
    s = _store()
    assert s.current("home_city").value == "上海"
    assert [c.value for c in s.history("home_city")] == ["北京", "上海"], "旧值不能被删掉：错误的 UPDATE 会不可逆地丢历史"
    assert s.current("nope") is None


def test_同一时间戳时后加入的胜出():
    s = MemoryStore()
    s.add(Card("seat", "aisle", ts="2025-01-01"))
    s.add(Card("seat", "window", ts="2025-01-01"))
    assert s.current("seat").value == "window"


def test_同名实体靠person区分():
    s = _store()
    assert s.current("doctor").value == "张医生（牙科）"
    assert s.current("doctor", person="Father").value == "张医生（心脏科）"


def test_渲染格式稳定():
    s = _store()
    assert s.render() == (
        "<user_memory>\n"
        "- user (self) diet: vegetarian  [2025-01-03; 订机票时要素食餐]\n"
        "- user (self) doctor: 张医生（牙科）  [2025-02-01]\n"
        "- user (self) home_city: 上海  [2025-03-10; 说自己刚搬家] (updated; was: 北京)\n"
        "- Father (father) doctor: 张医生（心脏科）  [2025-02-01]\n"
        "</user_memory>"
    )
    assert MemoryStore().render() == ""


def test_渲染与加入顺序无关_字节级稳定():
    a, b = _store(), MemoryStore()
    for c in reversed(a.cards):
        b.add(c)
    assert a.render() == b.render()


def test_保存与读取(tmp_path):
    s = _store()
    s.save(tmp_path / "m.jsonl")
    assert MemoryStore.load(tmp_path / "m.jsonl").render() == s.render()
    assert MemoryStore.load(tmp_path / "missing.jsonl").cards == []


def test_提取_容忍说明文字和代码块():
    reply = 'Here you go:\n```json\n[{"key": "seat", "value": "window", "backstory": "订东京机票"},' \
            ' {"key": "diet", "value": "vegetarian", "person": "", "relationship": null}]\n```'
    model = L.ScriptedLLM([L.say(reply)])
    cards = extract_memories(model, "User: 我要靠窗，我吃素", ts="2025-01-03", source="s1")
    assert [(c.key, c.value, c.person, c.relationship) for c in cards] == [
        ("seat", "window", "user", "self"), ("diet", "vegetarian", "user", "self")]
    assert all(c.ts == "2025-01-03" and c.source == "s1" for c in cards)
    assert model.calls[0]["tools"] == [] and "我要靠窗" in model.calls[0]["messages"][0]["content"]


def test_提取_坏输出宁可不记():
    for bad in ["没有值得记的", "[{broken json", '{"key": "a", "value": "b"}']:
        assert extract_memories(L.ScriptedLLM([L.say(bad)]), "x", ts="t", source="s") == []


def test_提取_丢弃不完整的条目和凭证():
    reply = '[{"key": "", "value": "x"}, {"key": "a"}, {"key": "bank_password", "value": "abc123"},' \
            ' {"key": "note", "value": "密码是 abc123"}, "oops", {"key": "loyalty", "value": "MileagePlus 12345678"}]'
    cards = extract_memories(L.ScriptedLLM([L.say(reply)]), "x", ts="t", source="s")
    assert [c.key for c in cards] == ["loyalty"]


def test_日志脱敏():
    log = "用户 john.doe@example.com 手机 13812345678，身份证 11010519491231002X，卡号 6222 0212 3456 7890 123，密码是 abc123"
    assert redact(log) == "用户 [EMAIL] 手机 [PHONE]，身份证 [ID]，卡号 [CARD]，[SECRET]"
    assert redact("PASSWORD: hunter2 ok") == "[SECRET] ok"
    assert redact("订单 20250103 已发货") == "订单 20250103 已发货", "普通数字不该被误伤"


def test_装配后_记忆进入系统提示词且整个会话不变():
    s = _store()
    model = L.ScriptedLLM([L.say("好的"), L.say("还是上海")])
    agent = Agent(model, ToolRegistry(), memory=s)
    agent.run("帮我订机票")
    agent.run("我住哪？")
    sys1 = model.calls[0]["messages"][0]["content"]
    assert s.render() in sys1
    assert model.calls[1]["messages"][0]["content"] == sys1, "记忆是静态前缀的一部分，会话中途不能改"
