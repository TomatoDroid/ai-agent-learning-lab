# 模块 10 · 多 Agent 协作

对应原书：[第十章 多 Agent 协作](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter10.md) · 原书配套实验：[chapter10/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter10)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

2.4 课把子 Agent 当作“隔离优于压缩”的手段；这一章把多 Agent 当作一个独立的系统设计问题：什么时候多 Agent 真的比单 Agent 好，怎么共享或不共享上下文，以及它们会怎样失败。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 10.1 分类框架与协作模式 | §分类框架；§何时真正优于单 Agent；§共享上下文的多 Agent 协作；§不共享上下文的多 Agent 协作 | 给 mini-agent 加管理者模式的并行子 Agent |
| 10.2 失败模式与 Agent 社会 | §多 Agent 协作的失败模式；§Agent 社会 | 在评估集上复现一种失败模式（如并发写冲突）并修复 |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 10-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter10/multi-role-transfer) | 共享上下文中的多角色转换 |
| [实验 10-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter10/book-translation) | 书籍翻译 Agent |
| [实验 10-4](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter10/parallel-web-research) | 并行搜集信息 |
| [实验 10-5](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter10/generative-agents) | 斯坦福 AI 小镇 |

完整实验列表见原书 [chapter10/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter10/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 多 Agent 什么时候反而比单 Agent 更差？
2. 共享上下文和不共享上下文，各自要付出什么代价？
3. 子 Agent 的任务描述为什么必须自包含（回看 2.4）？

原书第10章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
