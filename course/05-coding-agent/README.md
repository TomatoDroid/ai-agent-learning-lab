# 模块 5 · Coding Agent 与通用 Agent

对应原书：[第五章 Coding Agent 与通用 Agent](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter5.md) · 原书配套实验：[chapter5/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5)

Coding Agent 是目前最成熟的 Agent 形态，也是前四章所有原则的集大成者。这一章的后半部分给出一个更大的判断：**代码是通用 Agent 的元能力**，会写代码的 Agent 可以为自己造工具、造约束、造界面，甚至造 Agent。学完这一模块，mini-agent 会成为一个真正的 Coding Agent：能静默重试、识破重复调用、看穿危险命令，并在**里程碑 A** 里自己修好一个 bug。

| 课 | 精读 | 动手 | 时长 |
| --- | --- | --- | --- |
| [5.1 Coding Agent 的流程与错误恢复](5.1-flow-and-recovery.md) | 开头 至 §故障与错误恢复 | 练习 5.1：错误分类与退避、重复调用指纹、轨迹修复与跨厂商接管 | 约 100 分钟 |
| [5.2 搜索、编辑与安全](5.2-search-edit-security.md) | §实现技巧 至 §安全 | 练习 5.2：grep、命令语义解析、首尾匹配编辑；**里程碑 A** | 约 110 分钟 |
| [5.3 代码：通用 Agent 的元能力](5.3-code-as-meta-capability.md) | §代码：通用 Agent 的元能力 至章末 | 练习 5.3：约束求解、服务端真值守门、声明式表单 | 约 110 分钟 |

学完后你应该能：

- 说出 Coding Agent 的工作流程，以及为什么“完成”的标准是测试通过；
- 解释 Coding Agent 成熟的原因，并说出四条可迁移的 Harness 原则；
- 为四层故障分别设计检测、恢复与终止路径，讲清跨厂商接管带得走什么、带不走什么；
- 比较五种文件编辑方案，解释为什么用语义解析而不是关键字黑名单；
- 用致命三要素分析一个 Agent 的攻击面，并给出隔离兜底的方案；
- 说出代码作为元能力的六个方向，特别是“参数是 checklist，真值是守门员”和“信任边界下移到数据层”。

## 原书配套实验（推荐）

| 实验 | 内容 | 在哪一课 |
| --- | --- | --- |
| [实验 5-1、5-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/provider-failover) | 跨厂商轨迹接管；输出中断后的接续 | 5.1 |
| [coding-agent](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/coding-agent) | 读/搜 → 补丁 → 测试 → 修复 → 验证的完整循环 | 5.2 |
| [实验 5-3](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/code-for-math)、[5-4](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/code-for-logic) | 代码辅助数学与逻辑：先预测，再看原书的负结果 | 5.3 |
| [实验 5-5](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/small-model-codified-rules) | 小模型通过代码化规则执行政策 | 5.3 |
| [实验 5-12](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/dynamic-form) | 动态表单澄清意图 | 5.3 |
| [实验 5-16](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/agent-creator) | 能创造 Agent 的 Agent | 5.3 |

完整实验列表见原书 [chapter5/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/README.md)，正式结果与负结论记录在 [EXPERIMENT_LEDGER.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter5/EXPERIMENT_LEDGER.md)。
