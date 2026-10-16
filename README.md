# 深入理解 AI Agent · 实践课

跟着李博杰《深入理解 AI Agent：设计原理与工程实践》**v2.0** 逐章精读，用动画看懂机制，再在自己的 Agent 里把每条原则写成代码、用测试验证。

**[在线开始学习](https://tomatodroid.github.io/ai-agent-learning-lab/)** · [原书开源项目](https://github.com/bojieli/ai-agent-book) · [课程首页（Markdown）](course/README.md)

这是一份独立的学习课程，并非作者官方课程。它不替代原书：每节课都会告诉你读原书的哪几节，然后帮你把读到的东西拆开、看动画、动手实现、闭卷检验。

## 每节课怎么学

| 环节 | 做什么 |
| --- | --- |
| 读前复习 / 读前问题 | 带着问题去读 |
| 精读 | 按给出的范围读原书（链接固定在上游的同一个版本） |
| 拆解 | 关键机制的逐步动画、表格和推理链 |
| 动手 | 在 `mini-agent` 中完成练习，跑测试验收；或先预测、再运行原书实验 |
| 检验 | 先闭卷回答，再展开对照 |
| 原书思考题 / 复盘卡 | 连接原书思考题，一张卡片收束本课 |

主线项目 [`mini-agent`](mini-agent/README.md) 是一个纯 Python、零依赖的小型 Agent。每章给它加一块书里讲的能力，测试使用剧本化的模型，**不需要 API Key**；想接真实模型时，配好兼容 OpenAI 的接口即可。

## 当前进度

| 模块 | 对应原书 | 状态 |
| --- | --- | --- |
| 0 开学 | 引言 | 完成（2 节，1 个动画） |
| 1 Agent 入门 | 第一章 | 完成（3 节，5 个动画，练习 1.2、1.3） |
| 2 上下文工程 | 第二章 | 完成（4 节，7 个动画，练习 2.1–2.4） |
| 3 用户记忆和知识库 | 第三章 | 完成（3 节，7 个动画，练习 3.1–3.3） |
| 4 工具 | 第四章 | 完成（3 节，9 个动画，练习 4.1–4.3） |
| 5 Coding Agent | 第五章 | 完成（3 节，9 个动画，练习 5.1–5.3，里程碑 A） |
| 6 交互 | 第六章 | 完成（3 节，9 个动画，练习 6.1–6.3） |
| 7–10 | 第七至十章 | 大纲：精读范围、计划练习、推荐实验、自测题 |
| 结业 | 后记 | 大纲 |

## 本地运行

课程网站是无构建步骤的静态页面，课文用 `fetch` 读取，所以需要通过 HTTP 访问：

```sh
git clone https://github.com/TomatoDroid/ai-agent-learning-lab.git
cd ai-agent-learning-lab
python3 -m http.server 5186 --bind 127.0.0.1
```

访问 [http://localhost:5186/](http://localhost:5186/)。学习进度只保存在当前浏览器的 localStorage 中。

做练习：

```sh
cd mini-agent
python -m pip install pytest
python -m pytest tests/test_ch01_loop.py -v   # 每节课会告诉你跑哪个文件
python -m mini_agent demo                     # 离线演示
```

## 部署到 GitHub Pages

Settings → Pages → Deploy from a branch，选择 **codex/publish** 分支的 **/ (root)**。`.nojekyll` 让站点按普通静态文件发布，全部资源使用相对路径。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `index.html`、`assets/` | 课程网站：路由与渲染（`app.js`）、样式、动画框架与各章动画（`assets/anim/`）、marked |
| `course/` | 课文（Markdown，在 GitHub 上也能直接读）与 `manifest.json` 目录 |
| `mini-agent/` | 主线项目：练习版、参考答案（`solutions/`）、测试与练习生成脚本 |

## 参与修改

- 改课文：编辑 `course/` 下的 Markdown。动画用 `<div class="anim" data-anim="名称">后备文字</div>` 嵌入。
- 改练习：只改 `mini-agent/solutions/`，再运行 `python tools/make_exercises.py` 重新生成练习版。
- 提交前检查：

```sh
cd mini-agent
MINI_AGENT_TARGET=solutions python -m pytest -q   # 参考答案全部通过
python tools/make_exercises.py --check            # 练习版与参考答案同步
cd .. && for f in assets/*.js assets/anim/*.js; do node --check "$f"; done
```

## 许可与致谢

采用 [Apache License 2.0](LICENSE)。原书作者为 **李博杰**，原始项目 [bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book)，Copyright 2025 Bojie Li。课程与代码 Copyright 2026 TomatoDroid。完整声明见 [NOTICE](NOTICE)。
