# 模块 7 · Agent 的评估

对应原书：[第七章 Agent 的评估](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter7.md) · 原书配套实验：[chapter7/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

第二部分“提升”从评估开始，因为**没有评估就没有改进**。前六章的每一条原则，都应该能在评估集上被证明有用或没用。这一模块之后，你对 mini-agent 的每次改动都要附一份评估报告。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 7.1 评估任务的解剖与成功的定义 | §一条评估任务的解剖：τ²-bench；§评估指标：成功的定义 | 实验 7-2：亲手做一遍基准测试任务；理解 Pass@k 与 Pass^k |
| 7.2 评估环境、数据集与自动评判 | §评估环境；§评估数据集的设计；§自动化评估方法；§评估驱动的模型选型 | 为 mini-agent 建 15 条任务的评估集，写验证器和 LLM-as-a-Judge，做一次失败归因 |
| 7.3 统计显著性、可观测性与 AB 测试 | §统计显著性；§可观测性；§从 Benchmark 报告到系统改进；§内部评估基础设施；§仿真环境 | **里程碑 B**：用 bootstrap 或配对检验判断一次改动是否真的有效 |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 7-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/tau2-bench-eval) | 运行 τ²-bench |
| [实验 7-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/experiment-7-2-human-benchmark) | 人肉执行基准测试任务 |
| [实验 7-8](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/elo-leaderboard) | 从配对比较构建排行榜 |
| [实验 7-10](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/agent-cost-analysis) | 端到端成本分析 |

完整实验列表见原书 [chapter7/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter7/README.md)。先预测结果，再运行。

## 读完应该能回答

1. Pass@k 和 Pass^k 分别回答什么问题？生产系统更该看哪个？
2. LLM-as-a-Judge 在什么情况下不可信？怎么校准？
3. 成功率从 62% 涨到 66%，什么时候可以说“真的变好了”？

原书第7章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
