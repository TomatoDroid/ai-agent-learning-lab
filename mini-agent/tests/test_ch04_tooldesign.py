"""检查点 4.1：工具描述、参数校验、忠实的编辑工具。运行：pytest tests/test_ch04_tooldesign.py"""
import pytest

from mini_agent import llm as L
from mini_agent.agent import Agent
from mini_agent.builtin import add_workspace, basic_registry
from mini_agent.tooldesign import ArgumentError, EditError, apply_edit, lint_description, strict, validate_arguments
from mini_agent.tools import Tool, ToolRegistry


def test_只说能做什么的描述_几乎每一项都不合格():
    bad = Tool("search_files", "搜索文件", {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q", "path"]}, lambda q: q)
    assert lint_description(bad) == ["too_short", "no_when_to_use", "no_boundary", "no_example", "no_returns",
                                      "param_undocumented:q", "required_unknown:path"]


def test_写清何时用_边界_示例_返回值():
    good = Tool(
        "search_files",
        "Use this when you know part of a file NAME and need its path. Matches file names only; it cannot search inside "
        "files (use grep for that). Returns up to 20 paths, one per line.",
        {"type": "object", "properties": {"pattern": {"type": "string", "description": "glob pattern, e.g. '*.md' or 'src/**/test_*.py'"}},
         "required": ["pattern"]},
        lambda pattern: pattern)
    assert lint_description(good) == []


def test_工作目录工具的描述全部合格():
    reg = ToolRegistry()
    add_workspace(reg, "/tmp/mini-agent-lint")
    assert {name: lint_description(t) for name, t in reg.tools.items()} == {name: [] for name in reg.tools}


def test_参数校验_缺失_多余_类型_枚举():
    schema = {"type": "object", "properties": {
        "city": {"type": "string"}, "days": {"type": "integer"}, "unit": {"type": "string", "enum": ["C", "F"]}},
        "required": ["city"]}
    assert validate_arguments(schema, {"city": "温哥华", "days": 3, "unit": "C"}) == []
    assert validate_arguments(schema, {"days": "3", "unit": "K", "lang": "zh"}) == [
        "missing required argument 'city'",
        "argument 'days' should be integer, got string '3'",
        "argument 'unit' must be one of ['C', 'F'], got 'K'",
        "unexpected argument 'lang'",
    ]


def test_True不是整数_整数是合法的number():
    schema = {"type": "object", "properties": {"n": {"type": "integer"}, "x": {"type": "number"}}}
    assert validate_arguments(schema, {"n": True}) == ["argument 'n' should be integer, got boolean True"]
    assert validate_arguments(schema, {"x": 3}) == []


def test_模型给了不合法的JSON():
    assert validate_arguments({"type": "object", "properties": {}}, {"__raw__": '{"city": "温哥华"'}) == [
        'arguments are not valid JSON: {"city": "温哥华"']


def test_校验失败_工具根本不会执行():
    ran = []
    tool = strict(Tool("pay", "d", {"type": "object", "properties": {"amount": {"type": "number"}}, "required": ["amount"]},
                       lambda amount: ran.append(amount) or "paid"))
    with pytest.raises(ArgumentError, match="should be number, got string '100'"):
        tool.fn(amount="100")
    assert ran == [], "不做“智能转换”：字符串 '100' 不会被悄悄当成数字 100"
    assert tool.fn(amount=100) == "paid"


def test_Agent打开参数校验_错误信息让模型第二次就改对():
    model = L.ScriptedLLM([
        L.call("convert_currency", "c1", amount="2100000", from_currency="EUR"),
        L.call("convert_currency", "c2", amount=2100000, from_currency="EUR"),
        L.say("约 228 万美元"),
    ])
    result = Agent(model, basic_registry(), validate_args=True).run("2.1M 欧元是多少美元？")
    tool_msgs = [m["content"] for m in result.messages if m["role"] == "tool"]
    assert tool_msgs[0].startswith("ERROR: ArgumentError: argument 'amount' should be number, got string '2100000'")
    assert tool_msgs[1] == "EUR->USD: 2282608.70"


QUOTED = "标题：“深入理解 AI Agent”\n作者：李博杰\n"


def test_精确替换_一个字符都不改():
    text, n = apply_edit(QUOTED, "“深入理解 AI Agent”", "“深入理解 AI Agent（第二版）”")
    assert n == 1 and text == "标题：“深入理解 AI Agent（第二版）”\n作者：李博杰\n"


def test_弯引号被换成直引号时_错误信息指出差在哪一个字符():
    with pytest.raises(EditError) as e:
        apply_edit(QUOTED, '标题："深入理解 AI Agent"', "x")
    assert str(e.value) == (
        "old_string not found. Closest line 1: '标题：“深入理解 AI Agent”'. "
        "First difference at column 4: you sent '\"' (U+0022), the file has '“' (U+201C).")


def test_找不到相近的行():
    with pytest.raises(EditError, match="No similar line in the file"):
        apply_edit(QUOTED, "完全无关的内容 xyz", "x")


def test_多处匹配必须消歧():
    with pytest.raises(EditError, match="matches 2 times"):
        apply_edit("a = 1\nb = 1\n", "= 1", "= 2")
    assert apply_edit("a = 1\nb = 1\n", "= 1", "= 2", replace_all=True) == ("a = 2\nb = 2\n", 2)


def test_空字符串与无变化():
    with pytest.raises(EditError, match="empty"):
        apply_edit("abc", "", "x")
    with pytest.raises(EditError, match="identical"):
        apply_edit("abc", "b", "b")


def test_edit_file工具_改完自动做语法检查(tmp_path):
    reg = ToolRegistry()
    add_workspace(reg, tmp_path)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    out = reg.get("edit_file").fn(path="calc.py", old_string="return a + b", new_string="return a +")
    assert out == "replaced 1 occurrence(s) in calc.py; syntax error at line 2: invalid syntax"
    assert reg.get("write_file").fn(path="ok.py", content="x = 1\n") == "wrote 6 chars to ok.py; syntax OK"
