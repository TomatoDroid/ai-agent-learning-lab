# 模块 7 · Agent 的评估

对应原书：[第七章 Agent 的评估](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter7.md) · 原书配套实验：[chapter7/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7)

第二部分“提升”从评估开始，因为**没有评估就没有改进**。这一章回答一个问题：怎样判断 Agent 变好了还是变差了。它由四个环节构成：什么算成功、任务从何而来、由谁验证、分数如何转化为决策。学完这一模块，mini-agent 会多出一个评估框架（任务、分层验证器、多次试验）、一套评判工具（Rubric、配对比较、前缀回归、首错定位）和统计检验，你会用它们完成**里程碑 B**：证明一次改动真的有效。从这里开始，你对 mini-agent 的每次改动都要附一份评估报告。

| 课 | 精读 | 动手 | 时长 |
| --- | --- | --- | --- |
| [7.1 评估任务的解剖与成功的定义](7.1-task-and-success.md) | 开头 至 §评估环境 | 练习 7.1：Pass@k 与 Pass^k、分层验证器、每次重置环境 | 约 100 分钟 |
| [7.2 数据集、自动评判与失败归因](7.2-datasets-judges-attribution.md) | §评估数据集的设计 至 §配对比较与模型排名 | 练习 7.2：Rubric 加权与否决、配对比较与 Elo、前缀回归与首错 | 约 120 分钟 |
| [7.3 选型、显著性与持续改进](7.3-selection-significance-iteration.md) | §评估驱动的模型选型 至章末 | 练习 7.3：置信区间、配对检验、AB 决策；**里程碑 B** | 约 120 分钟 |

学完后你应该能：

- 把“成功”写成机器能检查的条件：终态、关键动作、必须告知的信息，并说清哪几层计分；
- 区分 Pass@k 和 Pass^k，用有限次试验估计它们，并按业务选择报告哪个；
- 说出评估环境的五个要素，以及为什么环境必须可重置；
- 为开放式任务设计 Rubric（加权、一票否决、可验证的分档），并防范评判模型的长度偏差和位置偏差；
- 对一条失败轨迹找出第一个错误、区分根因与后果，并把它变成前缀回归用例；
- 用置信区间和配对检验判断一次分差是不是噪声；
- 用机制、目标、护栏三类指标设计 AB 测试，并按“一轮证据只支持相称的下一步”推进改进。

## 原书配套实验（推荐）

| 实验 | 内容 | 在哪一课 |
| --- | --- | --- |
| [实验 7-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/tau2-bench-eval) | 运行 τ²-bench telecom 双控任务：先预测再看结果 | 7.1 |
| [实验 7-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/experiment-7-2-human-benchmark) | 亲手做六个基准的简单、中等、困难任务 | 7.2 |
| [实验 7-3](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/user-memory-evaluation)、[7-4](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/user-memory-system-evaluation) | 基于 Rubric 的用户记忆评估；JSON Cards、RAG 与混合系统对比 | 7.2 |
| [实验 7-6](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/android-world/failure-attribution)、[7-7](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/user-memory-policy-eval) | AndroidWorld 失败归因；轨迹前缀边界评估 | 7.2 |
| [实验 7-8](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/elo-leaderboard) | 从配对比较数据构建排行榜 | 7.2 |
| [实验 7-9](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/model-action-threshold)、[7-10](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/agent-cost-analysis) | 模型的行动阈值；端到端成本分析 | 7.3 |
| [实验 7-13](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/android-world) | AndroidWorld 的评估和改进（H1、H5、H5C 与完整复测） | 7.3 |

实验 7-5（TTS 质量评估）、7-11（多维度模型基准，原书尚无验收证据）、7-12（用户记忆全矩阵选型）、7-14（OpenVLA 与 RoboTwin2）需要较多 API 预算或 GPU，适合 Researcher。完整实验列表见原书 [chapter7/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/README.md)，正式结果与负结论记录在 [EXPERIMENT_LEDGER.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/EXPERIMENT_LEDGER.md)。
