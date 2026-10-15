# 模块 1 · Agent 入门

对应原书：[第一章 AI Agent 入门](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter1.md) · 原书配套实验：[chapter1/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter1)

作者说这一章是全书的“概念地图”：快速引入核心公式、运行循环、工程框架和设计模式，后面每一章展开其中一个方面。
所以这一模块的目标不是记住所有名词，而是**建立一套坐标系**，并亲手写出 Agent 的心脏：ReAct 循环。

| 课 | 精读 | 动手 | 时长 |
| --- | --- | --- | --- |
| [1.1 三要素与观察/动作空间](1.1-three-parts.md) | §现代 Agent = LLM + 上下文 + 工具（前四小节）、实验 1-1 | 用三栏分析一个 AI 产品 | 约 70 分钟 |
| [1.2 ReAct 循环](1.2-react.md) | §ReAct 循环、实验 1-2/1-3 | mini-agent 练习 1.2：核心循环 | 约 90 分钟 |
| [1.3 Harness 工程、编排与护栏](1.3-harness.md) | §Harness 工程 全节 | mini-agent 练习 1.3：动态风险、确认、熔断 | 约 100 分钟 |

学完后你应该能：

- 指出一个 Agent 的观察空间和动作空间，并用“扩展接口”的思路分析它的能力边界；
- 不看资料写出 ReAct 循环，并解释每一行为什么存在；
- 说清 Harness 的五个职责，以及为什么生产系统的大部分代码在“约束、验证、纠正”；
- 为一个具体场景在工作流和自主 Agent 之间做选择；
- 按三层护栏分析一次攻击会在哪一层被拦下。
