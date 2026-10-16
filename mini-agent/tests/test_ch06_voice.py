"""检查点 6.2：流式分段、控制标记、首音延迟、快慢思考。运行：pytest tests/test_ch06_voice.py"""
import pytest

from mini_agent import llm as L
from mini_agent.voice import FastSlowVoice, Turn, first_audio_ms, parse_control_tags, split_for_tts


# ---------- 6.2a 流式分段 ----------

def test_第一段遇到逗号就切_之后只在句末切():
    chunks = ["好的，", "明天上海", "多云，最高", "22 度。出门", "记得带伞，", "可能有阵雨。"]
    assert list(split_for_tts(chunks, min_chars=3)) == ["好的，", "明天上海多云，最高22 度。", "出门记得带伞，可能有阵雨。"]


def test_太短的片段不单独切():
    assert list(split_for_tts(["嗯。", "我想一下这个问题。"], min_chars=6)) == ["嗯。我想一下这个问题。"]


def test_一个块里有多句_逐句产出_剩余在结束时产出():
    out = list(split_for_tts(["第一句话很长。第二句话也很长！没说完"], min_chars=4))
    assert out == ["第一句话很长。", "第二句话也很长！", "没说完"]


def test_流式_切出一段就能拿到_不等整段结束():
    gen = split_for_tts(iter(["你好，", "今天"]), min_chars=2)
    assert next(gen) == "你好，"


def test_空白不产出():
    assert list(split_for_tts(["  ", "\n"])) == []


# ---------- 控制标记（提供的代码） ----------

def test_控制标记_不念出来_状态延续():
    acts = parse_control_tags("[EMO:happy]太好了！[THINKING]让我想想，[SPEED:0.8x]这个方案[FOO]可以。")
    assert acts == [
        {"say": "太好了！", "emotion": "happy", "speed": 1.0},
        {"pause": True},
        {"say": "让我想想，", "emotion": "happy", "speed": 1.0},
        {"say": "这个方案", "emotion": "happy", "speed": 0.8},
        {"say": "可以。", "emotion": "happy", "speed": 0.8},
    ]
    assert all("[" not in a.get("say", "") for a in acts)


# ---------- 6.2b 首音延迟 ----------

def test_串行_默认值等于原书图6_7的最优情况():
    assert first_audio_ms(Turn(), "serial") == (950, 1)


def test_流式感知_只等确认和首段():
    assert first_audio_ms(Turn(end_ms=1000), "streaming") == (1000 + 500 + 20 + 100 + 30 + 200, 1)


def test_推测执行_猜对了_LLM在静音期间就已开工():
    turn = Turn(end_ms=1000, partials=[(400, "明天"), (800, "明天天气"), (1000, "明天天气怎么样")], final="明天天气怎么样")
    ms, calls = first_audio_ms(turn, "speculative")
    assert ms == max(1000 + 500 + 20, 1000 + 100 + 30) + 200 == 1720
    assert calls == 3, "每个不同的临时转录都调了一次 LLM：用算力换延迟"
    assert ms < first_audio_ms(turn, "streaming")[0]


def test_推测执行_猜错了_延迟回到流式_还多花一次调用():
    turn = Turn(end_ms=1000, partials=[(600, "帮我订"), (600, "帮我订"), (1000, "帮我订明天")], final="帮我订明天的票")
    assert first_audio_ms(turn, "speculative") == (first_audio_ms(turn, "streaming")[0], 3)


def test_推测执行_LLM比静音还慢时_由LLM决定():
    turn = Turn(end_ms=1000, llm_ttft_ms=800, partials=[(1000, "你好")], final="你好")
    assert first_audio_ms(turn, "speculative")[0] == 1000 + 800 + 30 + 200


def test_没有临时转录时等同流式():
    assert first_audio_ms(Turn(), "speculative") == first_audio_ms(Turn(), "streaming")


def test_未知模式报错():
    with pytest.raises(ValueError):
        first_audio_ms(Turn(), "telepathy")


# ---------- 6.2c 快慢思考 ----------

def test_方案一_两个模型各自独立回答_可能前后矛盾():
    voice = FastSlowVoice(L.ScriptedLLM([L.say("这个套餐挺好，建议买。")]),
                          L.ScriptedLLM([L.say("不建议：它不支持国际漫游。")]), scheme="respond")
    said = voice.ask("这个套餐值得买吗？我经常出国。")
    assert said == [("fast", "这个套餐挺好，建议买。"), ("slow", "不建议：它不支持国际漫游。")]
    assert voice.slow_calls == 1


def test_方案二_简单问题快模型直接答_慢模型不参与():
    fast = L.ScriptedLLM([L.say("你好！有什么可以帮你？")])
    voice = FastSlowVoice(fast, L.ScriptedLLM([]))
    assert voice.ask("你好") == [("fast", "你好！有什么可以帮你？")]
    assert voice.slow_calls == 0 and fast.calls[0]["tools"][0]["function"]["name"] == "think_deeply"


def test_方案二_复杂问题_先说过渡语_慢模型建议由快模型表达():
    filler = L.call("think_deeply", "t1", question="套餐是否适合经常出国的人")
    filler.content = "我帮你对比一下，稍等。"
    fast = L.ScriptedLLM([filler, L.say("仔细看了下，这个套餐不支持国际漫游，你经常出国的话不太合适。")])
    slow = L.ScriptedLLM([L.say("不适合：缺少国际漫游。")])
    voice = FastSlowVoice(fast, slow)
    said = voice.ask("这个套餐值得买吗？我经常出国。")
    assert said == [("fast", "我帮你对比一下，稍等。"), ("fast", "仔细看了下，这个套餐不支持国际漫游，你经常出国的话不太合适。")]
    assert all(who == "fast" for who, _ in said), "方案二只有一个声音"
    assert slow.calls[0]["messages"][-1]["content"] == "套餐是否适合经常出国的人"
    seen = fast.calls[1]["messages"]
    assert seen[-1]["role"] == "tool" and seen[-1]["content"] == "[后台建议] 不适合：缺少国际漫游。"
    assert voice.history[-1]["role"] == "assistant" and voice.slow_calls == 1


def test_方案二_多轮对话保留历史():
    fast = L.ScriptedLLM([L.say("在的。"), L.say("刚才你说了你好。")])
    voice = FastSlowVoice(fast, L.ScriptedLLM([]))
    voice.ask("你好")
    voice.ask("我刚才说了什么？")
    assert [m["role"] for m in fast.calls[1]["messages"]] == ["system", "user", "assistant", "user"]
