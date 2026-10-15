# 模块 3 · 用户记忆和知识库

对应原书：[第三章 用户记忆和知识库](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter3.md) · 原书配套实验：[chapter3/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

第二章处理的是**一次任务之内**的上下文。这一章把同样的思路扩展到跨任务：用户记忆让 Agent 记住“这个人”，知识库让它查到“这件事”。两者共用一套检索技术，也共用一个风险：检索回来的内容同样是注入通道。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 3.1 用户记忆 | §用户记忆系统（全节） | 给 mini-agent 加跨会话记忆：JSON Cards 存储、整理与遗忘，记忆写入前过一遍脱敏 |
| 3.2 RAG 基础：分块、稠密、稀疏、混合检索 | §RAG 基础 | 从零写 BM25（对照实验 3-5），再接一个稠密检索，用小测试集看两者如何互补 |
| 3.3 超越扁平文本与 Agentic RAG | §超越扁平文本：知识的组织与检索 | 把检索做成 Agent 可调用的工具（Agentic RAG），对比“先检索再回答”的固定流程 |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 3-1、3-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/user-memory-evaluation) | 三层评估框架与记忆策略对比 |
| [实验 3-5](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/sparse-embedding) | 从零实现 BM25 |
| [实验 3-6](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/retrieval-pipeline) | 稀疏 + 稠密 + 重排序 |
| [实验 3-8](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/agentic-rag) | Agentic RAG 对比 |
| [实验 3-10](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/contextual-retrieval) | 上下文感知检索 |

完整实验列表见原书 [chapter3/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter3/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 记忆系统的三个层次分别评估什么？
2. 为什么“检索回来的内容”也需要来源标记？
3. Agentic RAG 比固定的检索流水线多付出了什么、换来了什么？

原书第3章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
