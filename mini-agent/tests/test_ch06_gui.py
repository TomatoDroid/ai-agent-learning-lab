"""检查点 6.3：坐标缩放、结构化元素索引、机器人逐步检查闭环。运行：pytest tests/test_ch06_gui.py"""
import pytest

from mini_agent import llm as L
from mini_agent.agent import Agent
from mini_agent.gui import (TIDY_GOAL, TIDY_PLAN, FakeBrowser, Scaler, TabletopSim, index_elements, run_closed_loop,
                            run_open_loop)


# ---------- 6.3a 坐标缩放 ----------

def test_原书例子_2560x1440选FWXGA_坐标双向映射():
    s = Scaler.for_screen(2560, 1440)
    assert (s.name, s.target) == ("FWXGA", (1366, 768))
    assert s.to_screen(683, 384) == (1280, 720)
    assert s.to_model(1280, 720) == (683, 384)


@pytest.mark.parametrize("screen, name", [((2048, 1536), "XGA"), ((1920, 1200), "WXGA"), ((1920, 1080), "FWXGA"),
                                          ((1024, 768), "XGA")])
def test_按宽高比选_不按像素数选(screen, name):
    assert Scaler.for_screen(*screen).name == name


def test_硬拉进4比3会系统性偏移():
    good, bad = Scaler.for_screen(2560, 1440), Scaler((2560, 1440), "XGA", (1024, 768))
    # 同一个真实按钮 (2400, 100)：两种缩放下模型看到的位置不同；用错比例时，模型按“正常比例”估出的坐标会偏
    x, y = good.to_screen(*good.to_model(2400, 100))
    assert abs(x - 2400) <= 2 and abs(y - 100) <= 2, "往返只有取整误差"
    assert bad.to_model(2400, 100) != good.to_model(2400, 100)


# ---------- 6.3b 结构化元素索引 ----------

NODES = [
    {"tag": "div", "attrs": {"class": "logo"}, "box": (0, 0, 200, 80)},
    {"tag": "input", "attrs": {"type": "text", "placeholder": "Search", "aria-label": "Search", "class": "x"}, "box": (100, 200, 400, 40)},
    {"tag": "button", "attrs": {"id": "submit-btn", "aria-label": "Submit form"}, "box": (520, 200, 80, 40)},
    {"tag": "button", "attrs": {"id": "hidden"}, "box": (0, 0, 10, 10), "visible": False},
    {"tag": "button", "attrs": {"disabled": ""}, "box": (0, 0, 10, 10)},
    {"tag": "a", "attrs": {"href": "/zero"}, "box": (0, 0, 0, 20)},
    {"tag": "div", "attrs": {"role": "button"}, "box": (10, 300, 100, 30), "text": "更多"},
    {"tag": "span", "attrs": {"onclick": "go()"}, "box": (10, 400, 50, 20)},
    {"tag": "a", "attrs": {"href": "/docs", "aria-label": "Documentation"}, "box": (10, 500, 100, 20)},
]


def test_只列可交互且可见可用的元素_编号连续():
    els = index_elements(NODES)
    assert [e.line for e in els] == [
        '[1] <input type="text" placeholder="Search" aria-label="Search" />',
        '[2] <button id="submit-btn" aria-label="Submit form" />',
        '[3] <div role="button">更多</div>',
        '[4] <span />',
        '[5] <a href="/docs" aria-label="Documentation" />',
    ]
    assert [e.id for e in els] == [1, 2, 3, 4, 5]


def test_编号对应元素中心坐标():
    els = index_elements(NODES)
    assert els[0].center == (300, 220) and els[1].center == (560, 220)


PAGES = {
    "home": {"nodes": [
        {"tag": "input", "attrs": {"type": "text", "aria-label": "Search"}, "box": (100, 200, 400, 40)},
        {"tag": "button", "attrs": {"id": "go"}, "box": (520, 200, 80, 40), "text": "搜索", "submit": 0, "goto": "results"},
    ], "text": "Search the web"},
    "results": {"nodes": [
        {"tag": "a", "attrs": {"href": "/"}, "box": (0, 0, 60, 20), "text": "首页", "goto": "home"},
    ], "text": "{query}：70°F，晴"},
}


def test_假浏览器_页面变化后旧编号作废():
    b = FakeBrowser(PAGES, "home")
    with pytest.raises(LookupError, match="observe"):
        b.click(1)
    assert "[2] <button id=\"go\">搜索</button>" in b.observe()
    b.type_text(1, "San Francisco weather")
    assert "page changed" in b.click(2)
    with pytest.raises(LookupError, match="no longer exists"):
        b.click(2)
    assert "San Francisco weather：70°F，晴" in b.observe()
    assert b.actions[-1] == "click 2 at (560, 220)"


def test_Agent用编号完成一次搜索():
    b = FakeBrowser(PAGES, "home")
    llm = L.ScriptedLLM([
        L.call("observe", "o1"),
        L.call("type_text", "t1", element=1, text="San Francisco weather"),
        L.call("click", "c1", element=2),
        L.call("click", "c2", element=2),        # 页面已变，旧编号：拿到错误后重新观察
        L.call("observe", "o2"),
        L.say("旧金山现在 70°F，晴。"),
    ])
    result = Agent(llm, b.tools()).run("查一下旧金山天气")
    assert result.answer == "旧金山现在 70°F，晴。"
    stale = [m for m in result.messages if m["role"] == "tool" and m.get("tool_call_id") == "c2"][0]
    assert "no longer exists" in stale["content"]
    assert "70°F" in [m for m in result.messages if m.get("tool_call_id") == "o2"][0]["content"]


# ---------- 6.3c 机器人闭环 ----------

def test_执行器只说已尝试_只有观察说真话():
    sim = TabletopSim(failures=[True])
    assert sim.pick("red_cup") == "attempted"
    assert sim.observe()["red_cup"] == "table"


def test_开环_一次失败带到末尾_却仍然自认为完成():
    r = run_open_loop(TabletopSim(failures=[True]), TIDY_PLAN, TIDY_GOAL)
    assert r.claimed and not r.success and r.calls == 4


def test_开环_没有失败时也能成功():
    assert run_open_loop(TabletopSim(), TIDY_PLAN, TIDY_GOAL).success


def test_逐步检查_只重试当前技能():
    sim = TabletopSim(failures=[True, False, False, False, True])   # 第一次抓杯子失败；第一次放废纸失败
    r = run_closed_loop(sim, TIDY_PLAN, TIDY_GOAL)
    assert r.success and r.claimed and r.recoveries == 2
    assert r.log == ["retry pick(red_cup)", "retry place(yellow_paper)"]
    assert sim.calls == [
        "pick(red_cup)", "observe()", "pick(red_cup)", "observe()",
        "place(red_cup,tray)", "observe()",
        "pick(yellow_paper)", "observe()",
        "place(yellow_paper,bin)", "observe()", "place(yellow_paper,bin)", "observe()",
        "observe()",
    ]
    assert r.calls == 13


def test_逐步检查_没有失败时_代价是多出的观察():
    r = run_closed_loop(TabletopSim(), TIDY_PLAN, TIDY_GOAL)
    assert r.success and r.calls == 9 and r.recoveries == 0


def test_重试用完_停下来_不声称完成():
    sim = TabletopSim(failures=[True, True, True])
    r = run_closed_loop(sim, TIDY_PLAN, TIDY_GOAL, max_retries=2)
    assert not r.success and not r.claimed
    assert r.log[-1] == "stop at pick(red_cup)" and "place(red_cup,tray)" not in sim.calls


def test_最终目标由新观察确认():
    class Liar(TabletopSim):
        """后置条件都满足，但收尾时有人把杯子拿走了。"""
        def observe(self):
            state = super().observe()
            if len(self.calls) > 8:
                state["red_cup"] = "table"
            return state
    r = run_closed_loop(Liar(), TIDY_PLAN, TIDY_GOAL)
    assert not r.success and not r.claimed
