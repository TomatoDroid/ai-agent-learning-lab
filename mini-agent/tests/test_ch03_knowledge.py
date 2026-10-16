"""检查点 3.3：上下文感知检索、检索层过滤与 Agentic RAG。运行：pytest tests/test_ch03_knowledge.py"""
from mini_agent import llm as L
from mini_agent.agent import Agent
from mini_agent.knowledge import Entry, KnowledgeBase, add_search_tool, contextualize, rag_answer
from mini_agent.retrieval import BM25Index
from mini_agent.tools import ToolRegistry


def test_上下文前缀让孤立的块重新可检索():
    doc = "ACME 公司 2025 年第二季度财报……"
    chunks = ["该公司第二季度收入增长了 3%。", "研发投入保持稳定。"]
    out = contextualize(doc, chunks, lambda d, c: "节选自 ACME 公司 2025 年 Q2 财报" if "收入" in c else "")
    assert out == ["[节选自 ACME 公司 2025 年 Q2 财报] 该公司第二季度收入增长了 3%。", "研发投入保持稳定。"]
    plain = BM25Index({"acme": chunks[0], "other": "BETA 公司收入增长 5%。"})
    ctx = BM25Index({"acme": out[0], "other": "BETA 公司收入增长 5%。"})
    assert plain.search("ACME 收入增长")[0][0] == "other", "没有前缀时，“该公司”是谁无从得知，反而是别家公司排第一"
    assert ctx.search("ACME 收入增长")[0][0] == "acme"


def _kb():
    kb = KnowledgeBase()
    kb.add(Entry("p-old", "退货政策：签收后 15 天内可退货。", valid_until="2025-06-30"))
    kb.add(Entry("p-new", "退货政策：签收后 7 天内可退货，需提供订单号。"))
    kb.add(Entry("hr-salary", "薪酬调整方案：退货部门绩效奖金上调。", audience={"hr"}))
    kb.add(Entry("vip", "VIP 客户退货可延长到 30 天。", audience={"support", "hr"}))
    return kb


def test_失效条目和越权条目在检索前就被过滤():
    kb = _kb()
    ids = [e.id for e in kb.visible(now="2025-07-01", groups={"support"})]
    assert ids == ["p-new", "vip"]
    assert [e.id for e in kb.visible(now="2025-06-30", groups={"hr"})] == ["hr-salary", "p-new", "p-old", "vip"], "失效当天仍有效"
    hits = [e.id for e in kb.search("退货", 5, now="2025-07-01", groups=set())]
    assert hits == ["p-new"]


def test_检索工具_权限在注册时绑定():
    reg = ToolRegistry()
    tool = add_search_tool(reg, _kb(), now="2025-07-01", groups={"support"})
    assert reg.get("search_knowledge") is tool and tool.untrusted_output
    assert tool.parameters["required"] == ["query"]
    out = tool.fn(query="退货 天")
    assert "[p-new]" in out and "[vip]" in out and "p-old" not in out and "hr-salary" not in out
    assert tool.fn(query="火星殖民") == "No results. Try different keywords."


def test_非智能体化RAG只有一次检索机会():
    model = L.ScriptedLLM([L.say("7 天")])
    assert rag_answer(model, _kb(), "退货期限", now="2025-07-01", groups=set()) == "7 天"
    prompt = model.calls[0]["messages"][1]["content"]
    assert "[p-new]" in prompt and "p-old" not in prompt


def test_AgenticRAG_第一次只找到本田_模型再搜一次特斯拉():
    mem = KnowledgeBase()
    mem.add(Entry("call-03-12", "用户为本田 Accord 预约了周五的保养。用户提到家里还有一辆特斯拉。"))
    mem.add(Entry("call-04-02", "用户咨询特斯拉 Model 3 的轮胎更换，尚未预约。"))
    mem.add(Entry("call-01-20", "用户更新了邮寄地址。"))
    reg = ToolRegistry()
    add_search_tool(reg, mem, now="2025-05-01", groups=set(), name="search_user_memory", k=1)
    model = L.ScriptedLLM([
        L.call("search_user_memory", "c1", query="车 保养 预约"),
        L.call("search_user_memory", "c2", query="特斯拉"),
        L.say("你是指已预约周五保养的本田 Accord，还是尚未预约的特斯拉 Model 3？"),
    ])
    r = Agent(model, reg).run("我需要为我的车预约服务")
    tool_msgs = [m["content"] for m in r.messages if m["role"] == "tool"]
    assert "call-03-12" in tool_msgs[0] and tool_msgs[0].startswith('<external_content source="search_user_memory">')
    assert "call-04-02" in tool_msgs[1]
    assert "特斯拉" in r.answer and r.stop_reason == "done"
