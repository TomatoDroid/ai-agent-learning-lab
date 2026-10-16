# mini-agent：跟着书一章一章长大的 Agent

这是课程的主线项目。每学完一课，你就给它补上一块原书讲过的能力，并用测试验收。
结课时，你会拥有一个自己从零写出来、每个设计决定都说得出理由的 Agent。

原书作者的建议是：“读懂书中的设计原则后，借助 coding agent 从头实现一遍。”
这里把“从头实现”拆成了小步：骨架和无关细节已经写好，你只需要写**体现原则的那几十行**。

## 准备

需要 Python 3.10+，只依赖标准库；跑测试需要 pytest。

```sh
cd mini-agent
python -m pip install pytest      # 或 uv pip install pytest
python -m pytest -q               # 一开始全部失败：每个失败都是一道练习
```

## 目录

| 路径 | 说明 |
| --- | --- |
| `mini_agent/` | **你的练习区**。带 `TODO 练习 x.y` 的地方由你来写 |
| `solutions/mini_agent/` | 参考答案。先自己写，卡住再看 |
| `tests/` | 每课的检查点测试，全部用假模型（`ScriptedLLM`）运行，不需要 API Key |
| `skills/` | 2.4 课用的示例 Skill |
| `tools/make_exercises.py` | 从参考答案重新生成练习版（会覆盖你的代码，慎用；`--file loop.py` 只重置一个文件） |

## 练习清单

后面的检查点会用到前面写好的代码，按顺序做最省事。

| 课 | 文件 | 练习 | 检查点 |
| --- | --- | --- | --- |
| [1.2](../course/01-intro/1.2-react.md) | `loop.py` | 1.2、1.2b：ReAct 循环；把错误变成观察 | `pytest tests/test_ch01_loop.py` |
| [1.3](../course/01-intro/1.3-harness.md) | `guard.py`、`loop.py` | 1.3a：动态风险评估、人工确认、熔断器；1.3b：把护栏接进循环 | `pytest tests/test_ch01_guard.py` |
| [2.1](../course/02-context/2.1-api-and-template.md) | `chat_template.py` | 2.1：简化版 Qwen3 Chat Template | `pytest tests/test_ch02_template.py` |
| [2.2](../course/02-context/2.2-kv-cache.md) | `context.py` | 2.2：前缀缓存计量、上下文体检 | `pytest tests/test_ch02_cache.py` |
| [2.3](../course/02-context/2.3-prompt-and-injection.md) | `injection.py` | 2.3：来源标记、注入扫描 | `pytest tests/test_ch02_injection.py` |
| [2.4](../course/02-context/2.4-skills-status-compression.md) | `status.py`、`compress.py`、`skills.py` | 2.4a/b/c：状态栏、阈值压缩、Skills | `pytest tests/test_ch02_status_compress_skills.py` |
| [3.1](../course/03-memory/3.1-user-memory.md) | `memory.py` | 3.1a/b/c：只追加的记忆卡片、记忆提取与校验、日志脱敏 | `pytest tests/test_ch03_memory.py` |
| [3.2](../course/03-memory/3.2-rag-basics.md) | `retrieval.py` | 3.2a/b/c/d：分块、BM25、RRF 融合、评测指标 | `pytest tests/test_ch03_retrieval.py` |
| [3.3](../course/03-memory/3.3-agentic-rag.md) | `knowledge.py` | 3.3a/b/c：上下文前缀、检索层过滤、检索工具 | `pytest tests/test_ch03_knowledge.py` |
| [4.1](../course/04-tools/4.1-tool-design.md) | `tooldesign.py` | 4.1a/b/c：工具描述检查、参数校验、忠实的编辑工具 | `pytest tests/test_ch04_tooldesign.py` |
| [4.2](../course/04-tools/4.2-mcp-and-discovery.md) | `mcp.py`、`discovery.py` | 4.2a/b/c：MCP 服务器、第三方服务器审计、工具搜索 | `pytest tests/test_ch04_mcp.py` |
| [4.3](../course/04-tools/4.3-perception-execution-collab.md) | `execution.py` | 4.3a/b/c：显式截断、Sidecar 门控、先查询再重试 | `pytest tests/test_ch04_execution.py` |

后续模块（Coding Agent、交互、评估……）会继续往这里加文件。

## 离线演示

```sh
python -m mini_agent demo
```

用假模型重放原书第一章的多币种汇总轨迹，打印每条消息，以及每次调用模型时读入了几条消息。
练习版需要先完成 1.2 才能跑通；想先看效果，可以 `cd solutions && python -m mini_agent demo`。

## 接入真实模型

任何 OpenAI 兼容接口都可以（Kimi、GLM、DeepSeek、SiliconFlow、OpenRouter、本地 vLLM / Ollama）：

```sh
export MINI_AGENT_BASE_URL=https://api.moonshot.cn/v1   # 换成你的服务商
export MINI_AGENT_API_KEY=sk-...
export MINI_AGENT_MODEL=<模型名>                         # 选一个支持工具调用的模型
python -m mini_agent chat --workspace ./workspace
```

`chat` 模式会装配你写好的全部零件：工作目录内的文件工具、护栏（高风险操作在终端里问你）、状态栏和压缩，以及参数校验（4.1 课）。
加上 `--memory memory.jsonl` 后，会话开始时载入用户记忆，退出时提炼新记忆并追加写回（3.1 课）。

```sh
python -m mini_agent mcp --workspace ./workspace
```

把工作目录工具作为 MCP 服务器（stdio）暴露出去，任何支持 MCP 的客户端都能接入（4.2 课）。
模型名和地址以服务商文档为准；选型建议见原书第一章“如何选择模型”。

## 设计约定

- 消息一律用 OpenAI Chat Completions 风格的 dict，便于和真实接口互换。
- 轨迹只追加、不改写（第二章“KV Cache”）。
- 工具错误永远变成给模型的观察，而不是让循环崩溃（第一章“工具结果反馈”）。
- 高风险操作的确认在**模型上下文之外**完成（第一章“护栏”）。
- 工具不悄悄修改参数；不合法就快速失败，错误信息要让模型能自己诊断（第四章“参数保真”）。

## 测试参考答案

```sh
MINI_AGENT_TARGET=solutions python -m pytest -q
python tools/make_exercises.py --check   # 练习版与参考答案是否同步
```
