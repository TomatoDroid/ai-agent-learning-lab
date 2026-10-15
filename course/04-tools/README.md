# 模块 4 · 工具

对应原书：[第四章 工具](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/chapter4.md) · 原书配套实验：[chapter4/](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter4)

> **本模块正在编写中。** 下面是课程大纲：你现在就可以按“精读”一栏读原书，按“读完应该能回答”自测。完整的课（动画、练习和测试）会在后续版本补上。

工具决定了 Agent 的动作空间。2.3 课说过“去掉工具描述，错误率 +45%”；这一章系统回答：工具怎么分类、怎么设计、多了怎么办，以及感知、执行、协作三类工具各自的坑。

| 课 | 精读 | 计划的动手 |
| --- | --- | --- |
| 4.1 工具设计的通用原则 | §工具的分类；§工具设计的通用原则；§感知工具；§执行工具；§协作工具 | 重写 mini-agent 的工具描述（使用边界、示例、协作关系），用消融测试对比前后 |
| 4.2 MCP 与主动工具发现 | §工具生态：MCP 与 Skill Hub；§工具太多怎么办 | 把 mini-agent 的工具暴露为 MCP server；实现按需加载的工具目录（呼应 2.3 的工具搜索） |

## 原书配套实验（推荐）

| 实验 | 内容 |
| --- | --- |
| [实验 4-1](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter4/active-tool-discovery) | 主动工具发现 |
| [实验 4-2](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter4/perception-tools) | 感知工具 MCP 服务器 |
| [实验 4-4](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter4/execution-tools) | 执行工具 MCP 服务器 |
| [实验 4-5](https://github.com/bojieli/ai-agent-book/tree/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter4/collaboration-tools) | 协作工具 MCP 服务器 |

完整实验列表见原书 [chapter4/README.md](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/chapter4/README.md)。先预测结果，再运行。

## 读完应该能回答

1. 专用工具、通用执行器和 Skill 各适合什么场景？
2. 工具太多时，按需加载如何同时照顾缓存和准确率？
3. 执行工具为什么要区分风险等级（回看 1.3 的 assess_risk）？

原书第4章末尾的思考题与[参考答案](https://github.com/bojieli/ai-agent-book/blob/dbc046eb896ac4e39aa19c7774c8bf49583b89a6/book/reference-answers.md)同样适用。
