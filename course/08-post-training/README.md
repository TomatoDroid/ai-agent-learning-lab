# 模块 8 · 模型后训练

对应原书：[第八章 模型后训练](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter8.md) · 原书配套实验：[chapter8/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter8)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

上下文工程改变的是模型看到什么，后训练改变的是模型本身。这是全书数学最多的一章，课程提供“可选阅读”路线：先建立四阶段的全景和选择框架，算法细节按需深入。GPU 实验全部为 Researcher 选做。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 8.1 四阶段全景 | §从预训练到 RL：四阶段全景；§Mid-training；§SFT；§何时选择 Mid-training、SFT 与 RL（标注“可选阅读”的两节可跳过） | 实验 8-1、8-2：Q-learning 与 LLM Agent 对比（CPU 可跑） |
| 8.2 RL：算法、环境、奖励与蒸馏 | §单轮强化学习；§RL 算法；§RL 环境；§从单轮到多轮；§奖励设计；§蒸馏 | 读懂“16 次 rollout 到一次参数更新”；比较结果奖励与过程奖励（RLVP） |
| 8.3 从 bad case 到后训练 | §从问题案例到后训练；§后训练实践要点 | 把你在模块 7 发现的 mini-agent 失败案例写成训练数据方案（偏好对或 SFT 样本）；有 GPU 选做实验 8-17、8-19 |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| 实验 8-1、8-2 | Q-learning 与 LLM Agent 对比 |
| [实验 8-8](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter8/prompt-distillation) | Prompt 蒸馏 |
| [实验 8-17](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter8/premature-completion-dpo) | 从“过早结束”到 DPO 修复 |
| [实验 8-19](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter8/exact-copy-sft) | 特殊字符串的精确复制 SFT |

完整实验列表见原书 [chapter8/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter8/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 一个问题该用提示词、SFT 还是 RL 来解决？判断依据是什么？
2. 为什么说 SFT 偏记忆、RL 偏泛化？
3. 多轮 Agent 任务的信用分配难在哪里？

原书第8章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
