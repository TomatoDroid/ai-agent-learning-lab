# 模块 6 · 交互：观察与动作空间的扩展

对应原书：[第六章 交互：观察与动作空间的扩展](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter6.md) · 原书配套实验：[chapter6/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

第一章说 Agent 的能力边界由观察空间和动作空间决定。这一章把两者往外推：从“用户问一句答一句”到事件驱动和异步，从文字到语音，从 API 到 GUI 和机器人。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 6.1 异步与事件驱动 | §模态与触发时机的扩展；§异步与事件驱动 | 用 asyncio 给 mini-agent 加事件队列、运行中打断与取消（对照实验 6-2） |
| 6.2 语音交互 | §语音：最自然的人机接口 | 级联、Omni 与全双工的对比；认知时序中的快慢路径（以读和看实验为主） |
| 6.3 Computer Use 与机器人 | §Computer Use；§机器人操作 | 以读和看实验证据为主；Researcher 选做实验 6-9（browser-use） |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 6-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/agent-with-event-trigger) | 事件驱动的邮件处理 Agent |
| [实验 6-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/async-agent) | 并行执行与打断 |
| [实验 6-3](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/astra-async-steering) | 模型原生异步与回合中途引导 |
| [实验 6-8](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/computer-use-open-model) | 运行 Computer Use（开放模型路径） |

完整实验列表见原书 [chapter6/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 事件驱动的 Agent 怎样处理“上一件事还没做完，新事件来了”？
2. 语音 Agent 的延迟预算花在哪里？快慢路径怎么分工？
3. GUI 自动化与 API 调用相比，多了哪些不确定性？

原书第6章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
