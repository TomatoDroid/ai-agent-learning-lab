"""主动工具发现：静态前缀只放核心工具和一个 search_tools 元工具（练习 4.2c）。

对应原书第四章“工具太多怎么办”与实验 4-1。思路：
- 除核心工具外，其余工具全部“延迟”（ToolRegistry.deferred）：已注册，但不进 schemas()，加载前也不能调用；
- Agent 发现能力缺口时，用自然语言调用 search_tools；
- 命中的工具定义作为这次工具调用的**结果**返回：它被追加在轨迹末尾，此后固定在原位置，
  静态前缀（system + tools）一个字都不变，缓存照常命中。

真实 API 已原生支持这件事（OpenAI 的 tool_search / defer_loading、Anthropic 的 tool_reference），
这里用最朴素的方式实现一遍，看清它为什么既省 token 又不破坏缓存。
"""
from __future__ import annotations

import json

from .retrieval import BM25Index
from .tools import Tool, ToolRegistry

NOT_FOUND = "No matching tools. Rephrase the need, or do it with the basic tools."


def add_tool_search(registry: ToolRegistry, core: list[str], k: int = 3, min_score: float = 0.5) -> Tool:
    """把 core 之外的工具全部延迟加载，注册并返回 search_tools 元工具。"""
    deferred = [name for name in registry.tools if name not in core]
    registry.deferred.update(deferred)
    # 名字里的下划线换成空格，"get_stock_price" 才能被 "stock price" 搜到
    index = BM25Index({name: name.replace("_", " ") + " " + registry.tools[name].description for name in deferred})

    def search_tools(query: str) -> str:
        """按需求描述检索工具，返回给模型的文本：

        - 没有得分 >= min_score 的结果：返回 NOT_FOUND（原书：明确返回“未找到”，让 Agent 改写需求或换基础工具）
        - 否则第一行 "Tools found (now callable):"，之后每个命中的工具一行（最多 k 个，按得分顺序）：
            * 已经加载过的："- {name}: already loaded, see its definition earlier"（同一工具不重复注入）
            * 新加载的：json.dumps(工具 schema 的 "function" 部分, ensure_ascii=False)，并把它加入 registry.loaded
        """
        # >>> EXERCISE 4.2c 工具搜索
        # HINT: hits = [name for name, score in index.search(query, k) if score >= min_score]。
        # HINT: 判断“已加载”：name in registry.loaded。工具 schema：registry.tools[name].schema()["function"]。
        hits = [name for name, score in index.search(query, k) if score >= min_score]
        if not hits:
            return NOT_FOUND
        lines = ["Tools found (now callable):"]
        for name in hits:
            if name in registry.loaded:
                lines.append(f"- {name}: already loaded, see its definition earlier")
            else:
                registry.loaded.add(name)
                lines.append(json.dumps(registry.tools[name].schema()["function"], ensure_ascii=False))
        return "\n".join(lines)
        # <<< EXERCISE

    tool = Tool(
        "search_tools",
        "Use this when none of your current tools can do what the task needs. Describe the capability in plain words, "
        "e.g. 'get a stock price' or 'send an email'. Returns up to %d matching tool definitions, which become callable "
        "right away. It only finds existing tools; it cannot run them." % k,
        {"type": "object", "properties": {"query": {"type": "string", "description": "the capability you need, e.g. 'convert a PDF to text'"}},
         "required": ["query"]},
        search_tools,
    )
    return registry.register(tool)
