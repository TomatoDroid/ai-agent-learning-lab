"""检查点 5.3：代码作为思考工具、业务规则守门员、声明式生成界面。运行：pytest tests/test_ch05_meta.py"""
from datetime import datetime, timedelta

import pytest

from mini_agent import llm as L
from mini_agent.agent import Agent
from mini_agent.meta import (AirlineDB, Reservation, add_airline_tools, add_code_interpreter, cancel_reservation, render_form, run_python,
                             solve_knights)
from mini_agent.tools import ToolRegistry

NOW = datetime(2026, 5, 1, 12, 0)


def test_骑士与无赖_枚举所有可能():
    # A：“B 是无赖。” B：“A 和 C 是同一类人。” C 不说话。
    sols = solve_knights(["A", "B", "C"], {
        "A": lambda w: not w["B"],
        "B": lambda w: w["A"] == w["C"],
    })
    assert sols == [{"A": True, "B": False, "C": False}, {"A": False, "B": True, "C": False}]
    # A：“我们俩都是无赖。” 只有一个解：A 是无赖，B 是骑士
    assert solve_knights(["A", "B"], {"A": lambda w: not w["A"] and not w["B"]}) == [{"A": False, "B": True}]
    assert solve_knights(["A"], {"A": lambda w: not w["A"]}) == [], "“我是无赖”这句话谁也说不出口"


def test_代码解释器_精确计算_超时有结构化错误():
    assert run_python("print(40*45//100 - 40*25//100)") == "8"
    assert run_python("1/0").endswith("ZeroDivisionError: division by zero\n[exit code 1]")
    assert run_python("while True: pass", timeout=1) == "ERROR: killed after 1s timeout (infinite loop?)"


def test_模型把算术交给代码():
    reg = ToolRegistry()
    add_code_interpreter(reg)
    model = L.ScriptedLLM([L.call("python", "c1", code="students=40\nphysics=students*45//100\nboth=students*25//100\nprint(physics-both)"),
                           L.say("只选物理的有 8 人。")])
    result = Agent(model, reg).run("40 个学生，45% 选物理，25% 物理化学都选，只选物理的有几人？")
    assert [m["content"] for m in result.messages if m["role"] == "tool"] == ["8"]


def _db():
    return AirlineDB(reservations={
        "R1": Reservation("R1", "economy", False, NOW - timedelta(days=3)),
        "R2": Reservation("R2", "economy", True, NOW - timedelta(days=3)),
        "R3": Reservation("R3", "basic_economy", False, NOW - timedelta(hours=5)),
        "R4": Reservation("R4", "business", False, NOW - timedelta(days=9)),
        "R5": Reservation("R5", "business", True, NOW - timedelta(days=9), any_segment_used=True),
        "R6": Reservation("R6", "basic_economy", False, NOW - timedelta(days=2), flight_status="cancelled_by_airline"),
        "R7": Reservation("R7", "economy", True, NOW + timedelta(days=1)),
        "R8": Reservation("R8", "premium", True, NOW - timedelta(days=4)),
    })


@pytest.mark.parametrize("rid, ok, reason", [
    ("R1", False, "economy requires insurance"),
    ("R2", True, "economy with insurance"),
    ("R3", True, "Cancelled within 24-hour window"),
    ("R4", True, "Business class cancellation"),
    ("R5", False, "Cannot cancel with used segments"),
    ("R6", True, "Airline cancelled flight"),
    ("R7", False, "Booking time is in the future"),
    ("R8", False, "Does not meet cancellation policy"),
    ("R9", False, "Reservation not found"),
])
def test_取消政策_按数据库真值裁决(rid, ok, reason):
    db = _db()
    assert cancel_reservation(db, rid, "change_of_plan", now=NOW) == {"success": ok, "reason": reason}
    assert db.cancelled == ([rid] if ok else [])


def test_模型自报的参数不算数_但要记下来():
    db = _db()
    out = cancel_reservation(db, "R1", "change_of_plan", expected_cabin_class="business", expected_has_insurance=True, now=NOW)
    assert out == {"success": False, "reason": "economy requires insurance"}, "模型说有保险也没用"
    assert db.mismatches == [("R1", "cabin_class", "business", "economy"), ("R1", "has_insurance", True, False)]
    cancel_reservation(db, "R2", "change_of_plan", expected_cabin_class="economy", expected_has_insurance=True, now=NOW)
    assert len(db.mismatches) == 2, "自报一致时不记录"


def test_时钟在服务端_模型改不了现在几点():
    db = _db()
    reg = ToolRegistry()
    add_airline_tools(reg, db, clock=lambda: NOW)
    assert "now" not in reg.get("cancel_reservation").parameters["properties"]
    model = L.ScriptedLLM([
        L.call("get_reservation", "c1", reservation_id="R1"),
        L.call("cancel_reservation", "c2", reservation_id="R1", cancellation_reason="change_of_plan", expected_has_insurance=True),
        L.say("抱歉，这张经济舱没有买保险，按政策不能取消。可以帮您改签。"),
    ])
    result = Agent(model, reg, validate_args=True).run("取消 R1，我买了保险的。")
    outs = [m["content"] for m in result.messages if m["role"] == "tool"]
    assert '"has_insurance": false' in outs[0]
    assert '"success": false' in outs[1] and db.cancelled == []
    assert db.mismatches == [("R1", "has_insurance", True, False)]


SPEC = {"title": "报销申请", "fields": [
    {"id": "amount", "type": "number", "label": "金额（元）"},
    {"id": "kind", "type": "select", "label": "类别", "options": ["差旅", "餐饮", "其他"]},
    {"id": "note", "type": "text", "label": "说明", "show_if": {"field": "kind", "equals": "其他"}},
    {"id": "agree", "type": "checkbox", "label": "我确认信息属实"},
]}


def test_声明式表单_只用组件目录渲染():
    assert render_form(SPEC) == "\n".join([
        '<form class="gen-form">',
        "<h3>报销申请</h3>",
        '<div class="field"><label for="amount">金额（元）</label><input id="amount" name="amount" type="number"></div>',
        '<div class="field"><label for="kind">类别</label><select id="kind" name="kind"><option value="差旅">差旅</option>'
        '<option value="餐饮">餐饮</option><option value="其他">其他</option></select></div>',
        '<div class="field" data-show-if="kind=其他" hidden><label for="note">说明</label><input id="note" name="note" type="text"></div>',
        '<div class="field"><label><input id="agree" name="agree" type="checkbox"> 我确认信息属实</label></div>',
        '<button type="submit">提交</button>',
        "</form>",
    ])


def test_模型写的文字一律转义():
    out = render_form({"title": "<script>alert(1)</script>", "fields": [
        {"id": "a", "type": "select", "label": '"><img src=x onerror=alert(1)>', "options": ["<b>"]}]})
    assert "<script>" not in out and "<img" not in out and "<b>" not in out
    assert "&lt;script&gt;" in out and "&quot;&gt;&lt;img" in out


@pytest.mark.parametrize("fields, msg", [
    ([{"id": "x", "type": "iframe", "label": "x"}], "component not in catalog: iframe"),
    ([{"id": "Bad Id", "type": "text", "label": "x"}], "bad field id: Bad Id"),
    ([{"id": "a", "type": "text", "label": "x"}, {"id": "a", "type": "text", "label": "y"}], "bad field id: a"),
    ([{"id": "k", "type": "select", "label": "x", "options": []}], "select needs options: k"),
    ([{"id": "n", "type": "text", "label": "x", "show_if": {"field": "k", "equals": "1"}},
      {"id": "k", "type": "text", "label": "y"}], "show_if must refer to an earlier field: n"),
])
def test_不在目录里的组件和坏描述被拒绝(fields, msg):
    with pytest.raises(ValueError, match=msg):
        render_form({"title": "t", "fields": fields})
