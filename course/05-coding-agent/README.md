# 模块 5 · Coding Agent 与通用 Agent

对应原书：[第五章 Coding Agent 与通用 Agent](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter5.md) · 原书配套实验：[chapter5/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

Coding Agent 是目前最成熟的 Agent 形态，也是前四章所有原则的集大成者。这一章的后半部分给出一个更大的判断：**代码是通用 Agent 的元能力**，会写代码的 Agent 可以为自己造工具、造界面，甚至造 Agent。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 5.1 Coding Agent 的流程与错误恢复 | §Coding Agent（前半：流程、Harness 实践、故障与恢复） | 实验 5-1、5-2：跨厂商轨迹接管、输出中断后的接续 |
| 5.2 搜索、编辑与安全 | §Coding Agent（后半：搜索工具、编辑工具、沙箱） | **里程碑 A**：给 mini-agent 实现 read / grep / edit（old_string 精确替换）/ bash 四件套，加权限与沙箱，让它修好一个小仓库里的 bug |
| 5.3 代码：通用 Agent 的元能力 | §代码：通用 Agent 的元能力 | 先预测再验证：实验 5-3、5-4，代码真能提升数学和逻辑题吗？ |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 5-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/provider-failover) | 跨厂商的轨迹接管 |
| [实验 5-3](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/code-for-math) | 用代码提升数学解题 |
| [实验 5-4](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/code-for-logic) | 用代码提升逻辑思考 |
| [实验 5-5](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/small-model-codified-rules) | 小模型通过代码化知识执行规则 |
| [实验 5-16](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/agent-creator) | 能创造 Agent 的 Agent |

完整实验列表见原书 [chapter5/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 为什么编辑工具用 old_string 精确替换，而不是行号或整文件重写？
2. Coding Agent 的哪些故障应该静默重试，哪些必须交给人？
3. “代码是元能力”具体体现在哪几种用法上？

原书第5章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
