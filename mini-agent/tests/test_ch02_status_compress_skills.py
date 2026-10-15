"""检查点 2.4：状态栏、阈值压缩、Skills。运行：pytest tests/test_ch02_status_compress_skills.py"""
import pytest

from mini_agent import llm as L
from mini_agent import messages as M
from mini_agent.agent import Agent
from mini_agent.compress import MARKER, compress_if_needed
from mini_agent.messages import ToolCall
from mini_agent.skills import activation_message, catalog_text, load_skills, parse_skill_md
from mini_agent.status import StatusTracker
from mini_agent.tools import Tool, ToolRegistry


# ── 状态栏 ──
def test_状态栏按目标计数并提示上限():
    s = StatusTracker(limits={"phone_call": 3}, target_arg={"phone_call": "company"})
    for c in ["Xfinity", "Xfinity", "Comcast", "Xfinity"]:
        s.record_call(ToolCall("c", "phone_call", {"company": c}))
    s.record_call(ToolCall("c", "web_search", {"q": "a"}))
    s.record_call(ToolCall("c", "web_search", {"q": "b"}))
    s.set_todo("1", "取消套餐", "in_progress")
    s.set_todo("2", "发邮件确认")
    assert s.render("2025-09-14 10:30") == (
        "<agent_status>\n"
        "time: 2025-09-14 10:30\n"
        "calls: phone_call[Comcast] 1/3; phone_call[Xfinity] 3/3 LIMIT REACHED; web_search 2\n"
        "todo: [1] 取消套餐 (in_progress); [2] 发邮件确认 (pending)\n"
        "</agent_status>"
    )


def test_空状态栏只有外壳():
    assert StatusTracker().render() == "<agent_status>\n</agent_status>"


def test_装配后_状态栏追加在末尾且旧状态不被改写():
    reg = ToolRegistry()
    reg.register(Tool("phone_call", "call", {"type": "object", "properties": {}}, lambda company: "占线"))
    model = L.ScriptedLLM([L.call("phone_call", "c1", company="Xfinity"), L.say("稍后再试")])
    agent = Agent(model, reg, status=StatusTracker(limits={"phone_call": 3}, target_arg={"phone_call": "company"}))
    agent.run("帮我取消 Xfinity")
    first, second = (c["messages"] for c in model.calls)
    assert first[-1]["content"] == "<agent_status>\n</agent_status>"
    assert "phone_call[Xfinity] 1/3" in second[-1]["content"]
    assert second[: len(first)] == first, "持久追加：上一次的状态消息原样保留，前缀不变"


# ── 压缩 ──
def big(n):
    return "很长的搜索结果。" * n


def test_没超过阈值时什么都不做():
    msgs = [M.system("s"), M.user("u"), M.tool_result("c", big(10))]
    out, n = compress_if_needed(msgs, budget=10_000, summarize=lambda t: "摘要")
    assert out is msgs and n == 0


def test_超过阈值时批量压缩所有未压缩的工具结果():
    msgs = [M.system("s" * 300), M.user("u" * 300), M.assistant("a" * 300),
            M.tool_result("c1", big(40)), M.tool_result("c2", "短结果"), M.tool_result("c3", big(40))]
    snapshot = [dict(m) for m in msgs]
    out, n = compress_if_needed(msgs, budget=500, summarize=lambda t: f"摘要({len(t)})", min_chars=50)
    assert n == 2
    assert out[3]["content"] == f"{MARKER} 摘要({len(big(40))})"
    assert out[3]["tool_call_id"] == "c1"
    assert out[4]["content"] == "短结果", "太短的不压缩"
    assert [m["content"] for m in out[:3]] == [m["content"] for m in msgs[:3]], "system/user/assistant 不动"
    assert msgs == snapshot, "不能原地修改传入的消息"


def test_已压缩的不会被再压一次():
    msgs = [M.user("u"), M.tool_result("c1", f"{MARKER} 旧摘要" + "x" * 500)]
    out, n = compress_if_needed(msgs, budget=10, summarize=lambda t: "新摘要", min_chars=1)
    assert n == 0 and out[1]["content"].startswith(f"{MARKER} 旧摘要")


# ── Skills ──
SKILL = """---
name: weekly-report
description: "写周报时使用。不用于日报或会议纪要。"
---

# 周报写法
1. 先写结论。
"""


def test_解析SKILL_md():
    meta, body = parse_skill_md(SKILL)
    assert meta == {"name": "weekly-report", "description": "写周报时使用。不用于日报或会议纪要。"}
    assert body == "# 周报写法\n1. 先写结论。"
    with pytest.raises(ValueError):
        parse_skill_md("# 没有 frontmatter")


@pytest.fixture
def skills_dir(tmp_path):
    for name, desc in [("weekly-report", "写周报时使用。"), ("pptx", "创建或编辑 PowerPoint 时使用。")]:
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n{name} 的正文", encoding="utf-8")
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("---\nname: broken\n---\n缺 description", encoding="utf-8")
    return tmp_path


def test_目录只含元数据且顺序固定(skills_dir):
    skills = load_skills(skills_dir)
    assert list(skills) == ["pptx", "weekly-report"]
    assert catalog_text(skills) == ("Available skills (call load_skill to read one):\n"
                                    "- pptx: 创建或编辑 PowerPoint 时使用。\n"
                                    "- weekly-report: 写周报时使用。")
    assert activation_message(skills["pptx"]) == {"role": "user", "content": '<skill name="pptx">\npptx 的正文\n</skill>'}


def test_装配后_正文按需追加且不改动前缀(skills_dir):
    model = L.ScriptedLLM([L.call("load_skill", "c1", name="weekly-report"), L.say("好的，按周报格式写")])
    agent = Agent(model, ToolRegistry(), "你是助手。", skills_dir=str(skills_dir))
    agent.run("帮我写本周周报")
    first, second = (c["messages"] for c in model.calls)
    assert "weekly-report 的正文" not in first[0]["content"], "正文不能常驻系统提示词"
    assert "- weekly-report: 写周报时使用。" in first[0]["content"]
    assert second[: len(first)] == first
    assert second[-1]["content"].startswith('<skill name="weekly-report">')
