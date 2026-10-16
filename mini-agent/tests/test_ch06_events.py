"""检查点 6.1：事件路由、批量事件标记、打断占位符，以及事件循环 Agent。运行：pytest tests/test_ch06_events.py

事件循环的测试全部是确定性的：后台工具是等待 asyncio.Event 的 async 函数，测试决定它何时返回。
"""
import asyncio

from mini_agent import llm as L
from mini_agent import messages as M
from mini_agent.events import Event, EventLoopAgent, interrupt, llm_router, placeholder, render_events, route
from mini_agent.messages import ToolCall
from mini_agent.tools import Tool, ToolRegistry


async def until(cond, rounds: int = 500):
    for _ in range(rounds):
        if cond():
            return
        await asyncio.sleep(0)
    raise AssertionError("等待的条件一直没有成立")


def gated_tool(name: str, result: str):
    """返回 (tool, gate, state)：工具开始后 state["started"] 为真，gate.set() 后才返回结果。"""
    gate, state = asyncio.Event(), {"started": False, "cancelled": False}

    async def fn(**_):
        state["started"] = True
        try:
            await gate.wait()
        except asyncio.CancelledError:
            state["cancelled"] = True
            raise
        return result
    return Tool(name, name, {"type": "object", "properties": {}}, fn), gate, state


def text_of(llm, i: int) -> str:
    return "\n".join(str(m.get("content")) for m in llm.calls[i]["messages"])


# ---------- 6.1a 路由 ----------

def test_紧急事件走取消式():
    assert route(Event("user.interrupt", "停")) == "cancel"
    assert route(Event("supervisor.instruction", "改用方案 B", source="supervisor")) == "cancel"
    assert route(Event("user.input", "等一下", priority="urgent")) == "cancel"


def test_无关的用户轻量查询走并行式():
    assert route(Event("user.input", "今天天气怎么样？", independent=True)) == "parallel"


def test_其余事件走队列式():
    assert route(Event("user.input", "顺便把附件也带上")) == "queue"
    assert route(Event("tool.result", "...", source="search", task_id="c1")) == "queue"
    assert route(Event("timer.trigger", "该开会了", source="timer")) == "queue"
    assert route(Event("email.received", "新邮件", source="mail", independent=True)) == "queue", "只有用户的查询能并行"


def test_LLM路由器_输出不合法时退回规则():
    assert llm_router(L.ScriptedLLM([L.say("Parallel\n")]))(Event("user.input", "x")) == "parallel"
    assert llm_router(L.ScriptedLLM([L.say("我觉得应该排队")]))(Event("user.interrupt", "停")) == "cancel"


# ---------- 6.1b 批量事件 ----------

def test_单个事件直接呈现_写清来源和任务ID():
    assert render_events([Event("user.input", "你好")]) == "User：你好"
    assert render_events([Event("tool.result", "找到 3 人", source="search_contacts", task_id="c1")]) \
        == "Tool result from search_contacts（任务 c1）：找到 3 人"
    assert render_events([Event("timer.trigger", "该开会了", source="timer")]) == "系统提醒：该开会了"


def test_多个事件_逐条标记并汇总():
    text = render_events([
        Event("tool.result", "找到 3 人", source="search_contacts", task_id="c1"),
        Event("user.input", "附件也带上"),
        Event("user.input", "抄送李四"),
    ])
    assert text.splitlines() == [
        "[未处理事件 1/3] Tool result from search_contacts（任务 c1）：找到 3 人",
        "[未处理事件 2/3] User：附件也带上",
        "[未处理事件 3/3] User：抄送李四",
        "上面有 3 个未处理事件，包括 1 个工具结果、2 条用户消息。请确保回应涵盖所有信息。",
    ]


def test_汇总按固定类别顺序_只列出现过的():
    text = render_events([Event("email.received", "x", source="mail"), Event("timer.trigger", "y"), Event("user.input", "z")])
    assert text.endswith("包括 1 条用户消息、1 个系统提醒、1 个其他事件。请确保回应涵盖所有信息。")


# ---------- 6.1c 打断占位符 ----------

def trajectory():
    return [
        M.system("s"), M.user("查联系人并写邮件"),
        M.assistant(None, [ToolCall("c1", "search_contacts", {}), ToolCall("c2", "read_calendar", {})]),
        M.tool_result("c2", "周五有空"),
    ]


def test_打断_为没返回的调用补占位符_再追加新消息():
    before = trajectory()
    out = interrupt(before, "等一下，先查明天的天气")
    assert len(before) == 4, "不能修改传入的轨迹"
    assert [m["role"] for m in out] == ["system", "user", "assistant", "tool", "tool", "user"]
    assert out[4]["tool_call_id"] == "c1" and out[4]["content"] == placeholder("c1", False)
    assert "后台" in out[4]["content"] and out[5]["content"] == "等一下，先查明天的天气"


def test_取消式打断_占位符说明已取消():
    out = interrupt(trajectory(), "停")
    out_cancel = interrupt(trajectory(), "停", cancelled=True)
    assert out_cancel[4]["content"] == placeholder("c1", True) != out[4]["content"]
    assert "取消" in out_cancel[4]["content"]


def test_没有工具调用时只追加消息():
    out = interrupt([M.system("s"), M.user("hi"), M.assistant("你好")], "再见")
    assert [m["role"] for m in out] == ["system", "user", "assistant", "user"]


# ---------- 事件循环 Agent（提供的代码，检验上面三个练习如何协同） ----------

def test_原书例子_查联系人时用户问天气_结果晚到后继续写邮件():
    async def scenario():
        reg = ToolRegistry()
        tool, gate, state = gated_tool("search_contacts", "张三 <zhang@example.com>")
        reg.register(tool)
        llm = L.ScriptedLLM([
            L.call("search_contacts", "c1", name="张三"),
            L.say("明天晴，最高 22 度。"),
            L.say("草稿：致 zhang@example.com，关于周五的会议……"),
        ])
        agent = EventLoopAgent(llm, reg)
        agent.post(Event("user.input", "给张三写封邮件约周五开会"))
        runner = asyncio.create_task(agent.run())
        await until(lambda: state["started"])
        agent.post(Event("user.input", "等一下，先帮我查一下明天的天气", priority="urgent"))
        await until(lambda: len(agent.outbox) == 1)
        assert agent.outbox == ["明天晴，最高 22 度。"]
        assert "c1" in agent.background, "没跑完的工具转入后台，而不是被丢掉"
        seen = llm.calls[1]["messages"]
        assert seen[-2]["role"] == "tool" and seen[-2]["content"] == placeholder("c1", False)
        assert seen[-1] == M.user("User：等一下，先帮我查一下明天的天气")
        gate.set()
        await runner
        assert "Tool result from search_contacts（任务 c1）：张三 <zhang@example.com>" in text_of(llm, 2)
        assert agent.outbox[-1].startswith("草稿") and not agent.background
        assert agent.log == ["queue:user.input", "cancel:user.input"]
    asyncio.run(scenario())


def test_队列式_常规事件等到工具返回后一起追加_只多一次模型调用():
    async def scenario():
        reg = ToolRegistry()
        tool, gate, state = gated_tool("search_contacts", "张三")
        reg.register(tool)
        llm = L.ScriptedLLM([L.call("search_contacts", "c1"), L.say("已写好，带附件并抄送李四。")])
        agent = EventLoopAgent(llm, reg)
        agent.post(Event("user.input", "给张三写邮件"))
        runner = asyncio.create_task(agent.run())
        await until(lambda: state["started"])
        agent.post(Event("user.input", "附件也带上"))
        agent.post(Event("user.input", "抄送李四"))
        await until(lambda: agent.log.count("queue:user.input") == 3)
        assert len(llm.calls) == 1, "常规事件不打断正在执行的工具"
        gate.set()
        await runner
        assert len(llm.calls) == 2
        seen = llm.calls[1]["messages"]
        assert seen[-2] == M.tool_result("c1", "张三"), "工具结果先配对，轨迹保持合法"
        assert seen[-1]["role"] == "user" and "[未处理事件 2/2] User：抄送李四" in seen[-1]["content"]
        assert "2 条用户消息" in seen[-1]["content"]
    asyncio.run(scenario())


def test_用户点停止_取消工具_不会有迟到的结果():
    async def scenario():
        reg = ToolRegistry()
        tool, gate, state = gated_tool("long_job", "done")
        reg.register(tool)
        llm = L.ScriptedLLM([L.call("long_job", "c1"), L.say("好的，已停止。")])
        agent = EventLoopAgent(llm, reg)
        agent.post(Event("user.input", "跑个长任务"))
        runner = asyncio.create_task(agent.run())
        await until(lambda: state["started"])
        agent.post(Event("user.interrupt", "停止"))
        await runner
        assert state["cancelled"], "工具真的被取消了"
        seen = llm.calls[1]["messages"]
        assert seen[-2]["content"] == placeholder("c1", True)
        assert agent.outbox == ["好的，已停止。"] and not agent.background and len(llm.calls) == 2
    asyncio.run(scenario())


def test_打断时已经返回的并行调用用真实结果():
    async def scenario():
        reg = ToolRegistry()
        slow, gate, state = gated_tool("slow", "slow done")
        reg.register(slow)
        reg.register(Tool("fast", "fast", {"type": "object", "properties": {}}, lambda: "fast done"))
        llm = L.ScriptedLLM([L.calls(ToolCall("a", "slow", {}), ToolCall("b", "fast", {})), L.say("先回答你"), L.say("全部完成")])
        agent = EventLoopAgent(llm, reg)
        agent.post(Event("user.input", "go"))
        runner = asyncio.create_task(agent.run())
        await until(lambda: state["started"])
        await asyncio.sleep(0)
        agent.post(Event("supervisor.instruction", "先汇报进度", source="supervisor"))
        await until(lambda: len(agent.outbox) == 1)
        tools = {m["tool_call_id"]: m["content"] for m in llm.calls[1]["messages"] if m["role"] == "tool"}
        assert tools == {"a": placeholder("a", False), "b": "fast done"}
        assert llm.calls[1]["messages"][-1]["content"] == "系统提醒：先汇报进度"
        gate.set()
        await runner
        assert agent.outbox == ["先回答你", "全部完成"]
    asyncio.run(scenario())


def test_并行式_无关问题立即回答_不碰主轨迹_记录稍后并入():
    async def scenario():
        reg = ToolRegistry()
        tool, gate, state = gated_tool("write_report", "报告已生成")
        reg.register(tool)
        llm = L.ScriptedLLM([L.call("write_report", "c1"), L.say("今天多云。"), L.say("报告写好了。")])
        agent = EventLoopAgent(llm, reg)
        agent.post(Event("user.input", "写季度报告"))
        runner = asyncio.create_task(agent.run())
        await until(lambda: state["started"])
        agent.post(Event("user.input", "今天天气怎么样？", independent=True))
        await until(lambda: agent.outbox == ["今天多云。"])
        side = llm.calls[1]["messages"]
        assert [m["role"] for m in side] == ["system", "user"], "并行会话只带系统提示和这个问题"
        assert not state["cancelled"] and not gate.is_set(), "主任务没有被打断"
        gate.set()
        await runner
        main = llm.calls[2]["messages"]
        assert main[-2] == M.tool_result("c1", "报告已生成")
        assert "已在并行会话中回答：今天多云。" in main[-1]["content"], "安全点时主轨迹得知用户问过什么"
        assert agent.log == ["queue:user.input", "parallel:user.input"]
    asyncio.run(scenario())
