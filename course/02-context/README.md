# 模块 2 · 上下文工程

对应原书：[第二章 上下文工程](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter2.md) · 原书配套实验：[chapter2/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter2)

作者称这是**全书最关键的一章**。第一章说上下文是 Agent 的“眼睛”，这一章回答：眼睛里的东西以什么形式送进模型、怎样放才便宜、写什么、怎么防被劫持、怎么按需加载、怎么做减法。

全章其实只在回答一个问题：**怎样以更低成本，向模型提供一个信息充分的上下文？**

| 课 | 精读 | 动手 | 时长 |
| --- | --- | --- | --- |
| [2.1 API 消息结构与 Chat Template](2.1-api-and-template.md) | §上下文：决定 Agent 能力上限的关键；§Agent 如何调用大模型；§Chat Template | 练习 2.1：写一个简化版 Qwen3 模板 | 约 80 分钟 |
| [2.2 KV Cache 友好的上下文](2.2-kv-cache.md) | §KV Cache 友好的上下文设计（全节） | 练习 2.2：前缀缓存计量与上下文体检 | 约 100 分钟 |
| [2.3 提示工程与提示注入](2.3-prompt-and-injection.md) | §提示工程：优化系统提示词（全节） | 练习 2.3：来源标记与注入扫描 | 约 90 分钟 |
| [2.4 Skills、状态栏与上下文压缩](2.4-skills-status-compression.md) | §动态提示词与 Agent Skills；§Agent 状态栏；§上下文压缩策略 | 练习 2.4a/b/c | 约 120 分钟 |

学完后你应该能：

- 画出一次 API 请求的完整结构，并说明它如何被 Chat Template 变成 token 流；
- 背出 KV Cache 的三条核心结论，并在代码评审中指出破坏缓存的写法；
- 写出流程驱动、结构清晰的系统提示词，并按层次设计注入防御；
- 解释 Skills 的三层渐进式披露、状态栏的两种更新方式和压缩的三个动机；
- 在“压缩”和“子 Agent 隔离”之间做出选择。
