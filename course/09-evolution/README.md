# 模块 9 · Agent 的持续进化

对应原书：[第九章 Agent 的持续进化](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter9.md) · 原书配套实验：[chapter9/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

评估告诉你哪里不好，后训练是一种改法，但不是唯一的改法。这一章回答：Agent 能不能从自己的运行轨迹中学习，把经验写成知识、指令、程序或模型参数，并且安全地上线？

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 9.1 学习信号与四种更新载体 | §从运行轨迹中获得学习信号；§Agent 持续进化的四种方法 | 实验 9-1：为客服 Agent 构建轨迹验证器 |
| 9.2 安全的进化闭环 | §构建可长期运行的持续进化闭环 | 让 mini-agent 从失败轨迹提炼规则写进自己的 Skill 或提示词，经评估集门禁、灰度和回滚才生效（对照实验 9-2、9-7） |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 9-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9/trajectory-verifier) | 轨迹验证器 |
| [实验 9-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9/tau2-escalation-experience) | 从失败轨迹提炼规则 |
| [实验 9-3](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9/prompt-auto-optimization) | 基于失败轨迹优化提示词 |
| [实验 9-7](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9/harness-safety-gate) | 高风险操作确认门禁 |
| [实验 9-9](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9/self-evolution-eval) | 评估 Agent 是否在持续进化 |

完整实验列表见原书 [chapter9/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter9/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 一条经验应该写成知识、指令、程序还是参数？各自的更新成本和风险是什么？
2. 为什么自我修改必须经过评估集门禁？
3. 怎样判断一个 Agent “真的在进化”，而不是在过拟合评估集？

原书第9章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
