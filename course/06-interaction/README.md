# 模块 6 · 交互：观察与动作空间的扩展

对应原书：[第六章 交互：观察与动作空间的扩展](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter6.md) · 原书配套实验：[chapter6/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6)

前五章的 Agent 是回合制的：用户说一句，Agent 想一段、调几个工具、回一句，期间世界被默认为静止的。这一章挑战的正是这个前提。它沿着两根轴扩展观察与动作空间：**模态**（文字之外的声音、屏幕、物理传感器）和**触发时机**（世界主动推来，动作跨回合、可打断、可抢占），时间尺度从“秒到天”一路压到毫秒。学完这一模块，mini-agent 会多出一个事件循环：能在工具运行时被打断、排队或并行回答，还有语音分段、GUI 定位和机器人闭环三块可以测试的核心逻辑。

| 课 | 精读 | 动手 | 时长 |
| --- | --- | --- | --- |
| [6.1 异步与事件驱动](6.1-async-events.md) | 开头 至 §从“能接收异步消息”到“可靠处理异步任务” | 练习 6.1：事件路由、批量事件标记、打断占位符 | 约 110 分钟 |
| [6.2 语音：最自然的人机接口](6.2-voice.md) | §语音 | 练习 6.2：流式分段、首音延迟、快慢思考 | 约 90 分钟 |
| [6.3 Computer Use 与机器人](6.3-computer-use-robotics.md) | §Computer Use 至章末 | 练习 6.3：坐标缩放、结构化元素索引、逐步检查闭环 | 约 110 分钟 |

学完后你应该能：

- 说出“回合制是交互约定”的含义，以及模态和触发时机两个扩展方向；
- 为一个事件选择取消式、队列式或并行式处理，并讲清“安全点”在其中的作用；
- 在不支持原生异步的接口上用占位符处理打断，说出它的语义风险和防范办法；
- 比较级联、Omni 和全双工三种语音范式，算出一次回答的首音延迟花在哪里；
- 说出快慢思考三种方案的取舍，以及“端到端”的两种含义；
- 为 Computer Use 选择视觉定位路线，正确地做坐标双向缩放；
- 用“只选有边界的技能、每步观察、最终由新观察确认”设计一个机器人闭环。

## 原书配套实验（推荐）

| 实验 | 内容 | 在哪一课 |
| --- | --- | --- |
| [实验 6-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/agent-with-event-trigger)、[6-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/async-agent) | 事件驱动的邮件 Agent；并行执行、打断与取消 | 6.1 |
| [实验 6-3](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/astra-async-steering) | 模型原生异步与回合中途引导：先预测再看结果 | 6.1 |
| [实验 6-5](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/streaming-speech)、[6-6](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/end-to-end-speech)、[6-7](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/controllable-tts) | 流式感知、端到端与自级联、控制标记 TTS：三个都有负结果或部分复现 | 6.2 |
| [实验 6-8](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/claude-computer-use-native)、[6-9](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/computer-use-open-model) | Computer Use 的两条路径：查询旧金山天气 | 6.3 |
| [实验 6-13](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/gemini-xlerobot-navigation)、[6-14](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/rgb-sim2real-grasping) | 开环、逐步检查与预测式闭环；RGB 跨环境测试 | 6.3 |

实验 6-4（级联语音基线）、6-10、6-12（XLeRobot 真机）需要麦克风、GPU 或机械臂，适合 Researcher。完整实验列表见原书 [chapter6/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/README.md)，正式结果与负结论记录在 [EXPERIMENT_LEDGER.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter6/EXPERIMENT_LEDGER.md)。
