"""一个简化的 Qwen3 风格 Chat Template（练习 2.1）。

对应原书第二章“从 API 消息到模型 Token：Chat Template”。真实模板是 Jinja，
这里用 Python 写出它的核心规则，帮你看清两件事：
1. 结构化消息如何变成线性 token 流；
2. 为什么把工具结果伪装成 user 消息，会让模型丢掉之前的思考。
"""
from __future__ import annotations

import json

START, END = "<|im_start|>", "<|im_end|>"


def last_query_index(messages: list[dict]) -> int:
    """最后一条“真实用户提问”的下标；没有则返回 -1。

    在本模板里，工具结果的 role 是 "tool"，所以 role == "user" 的都算真实提问。
    （Qwen3 的真实模板还会排除以 <tool_response> 开头的 user 消息，效果相同。）
    """
    # >>> EXERCISE 2.1 找到最后一条真实提问
    # HINT: 从后往前找第一条 role == "user" 的消息。
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            return i
    return -1
    # <<< EXERCISE


def render(messages: list[dict], tools: list[dict] | None = None, add_generation_prompt: bool = True) -> str:
    """把消息列表渲染成模型实际读入的字符串。规则：

    - 每条消息：<|im_start|>{role}\\n{内容}<|im_end|>\\n
    - tools 不为空：在 system 内容后追加 "\\n\\n<tools>\\n" + 每个工具的 function 部分（json.dumps，ensure_ascii=False，每行一个）+ "\\n</tools>"；
      没有 system 消息时，新建一条只含 <tools> 段（不带开头空行）的 system 消息放在最前面。
    - assistant：如果它位于最后一条真实提问之后且有 reasoning_content，先写 "<think>\\n{reasoning}\\n</think>\\n\\n"；
      然后写 content（None 当作空串）；每个工具调用再写 "\\n<tool_call>\\n{"name": …, "arguments": …}\\n</tool_call>"，
      arguments 写成对象而不是字符串。
    - 连续的 tool 消息合并进同一个 user 块，每条写成 "<tool_response>\\n{content}\\n</tool_response>"，之间用 "\\n" 连接。
    - add_generation_prompt 为真时，末尾追加 "<|im_start|>assistant\\n"。
    """
    # >>> EXERCISE 2.1 实现模板
    # HINT: 先处理 tools 合并进 system；再用 last_query_index 决定哪些 assistant 保留思考；
    # HINT: 遍历消息时，遇到 tool 就把连续的 tool 收集起来一起输出。
    # HINT: 工具调用的 arguments 在消息里是 JSON 字符串，用 json.loads 还原后再 json.dumps。
    msgs = list(messages)
    if tools:
        block = "<tools>\n" + "\n".join(json.dumps(t["function"], ensure_ascii=False) for t in tools) + "\n</tools>"
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + "\n\n" + block}
        else:
            msgs.insert(0, {"role": "system", "content": block})

    last = last_query_index(msgs)
    out: list[str] = []
    i = 0
    while i < len(msgs):
        m = msgs[i]
        role = m["role"]
        if role == "tool":
            parts = []
            while i < len(msgs) and msgs[i]["role"] == "tool":
                parts.append(f"<tool_response>\n{msgs[i]['content']}\n</tool_response>")
                i += 1
            out.append(f"{START}user\n" + "\n".join(parts) + f"{END}\n")
            continue
        if role == "assistant":
            body = ""
            if i > last and m.get("reasoning_content"):
                body += f"<think>\n{m['reasoning_content']}\n</think>\n\n"
            body += m.get("content") or ""
            for c in m.get("tool_calls") or []:
                fn = c["function"]
                args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                body += "\n<tool_call>\n" + json.dumps({"name": fn["name"], "arguments": args}, ensure_ascii=False) + "\n</tool_call>"
            out.append(f"{START}assistant\n{body}{END}\n")
        else:
            out.append(f"{START}{role}\n{m['content']}{END}\n")
        i += 1
    if add_generation_prompt:
        out.append(f"{START}assistant\n")
    return "".join(out)
    # <<< EXERCISE
