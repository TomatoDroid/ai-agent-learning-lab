# Agent 学习实验室 📖

通过 **12 个递进关卡、12 个互动实验、24 道反馈测验**，理解 AI Agent 的核心概念。

**[在线开始学习](https://tomatodroid.github.io/ai-agent-learning-lab/)** · [原书开源项目](https://github.com/bojieli/ai-agent-book) · [原书 v1.4 PDF](source.pdf)

基于李博杰《深入理解 AI Agent：设计原理与工程实践》v1.4（2026-08-13）改编。这是一份独立互动导读，并非作者官方课程。

## 怎么学

每关按 **理解概念 → 动手实验 → 检验理解** 推进。完成实验、答对两题后计为已掌握；答错可以查看解释并重试，目录允许自由预习和复习。

- 起步：Agent 三个组件、ReAct 反馈循环、上下文管理。
- 构建：工具与安全、记忆与 RAG、Coding Agent、评估、Harness 与工作流。
- 进阶：持续进化、SFT/RL、多模态、多 Agent 协作。

支持手机浏览、术语搜索、原书页码跳转、进度自动保存、学习笔记和 Markdown 导出。

所有实验均为确定性的浏览器教学模拟，无需 API Key，不调用真实模型、天气或企业系统，也不执行用户输入的任意代码。导读覆盖原书 10 章的核心概念，不包含全部数学推导及高级实验。

## 本地运行

直接用浏览器打开 `index.html`，或：

```sh
git clone https://github.com/TomatoDroid/ai-agent-learning-lab.git
cd ai-agent-learning-lab
python3 -m http.server 5186 --bind 127.0.0.1
```

访问 [http://localhost:5186/](http://localhost:5186/)。无安装、构建或外部服务依赖。

进度与笔记仅保存在当前浏览器的 localStorage 中。不同域名、浏览器、设备之间不会同步；清理浏览器数据会清除它们。重要笔记请导出保存。

## 部署到 GitHub Pages

本仓库通过 GitHub Pages 的分支发布模式部署，无需自定义工作流。

1. 打开仓库 **Settings → Pages**。
2. Source 选择 **Deploy from a branch**。
3. Branch 选择 **codex/publish**，目录选择 **/ (root)**。
4. 保存后等待 Pages 构建完成。之后推送到该分支会自动更新网站。

`.nojekyll` 使站点按普通静态文件发布，全部资源使用相对路径，支持 GitHub 项目子路径。Fork 后请将 README 与页面底部的仓库地址改为自己的地址。

## 文件结构

| 文件 | 内容 |
| --- | --- |
| `index.html` | 应用结构与导航 |
| `content.js` | 课程内容、原文页码、24 道测验、术语 |
| `labs.js` | 12 个本地互动实验 |
| `app.js` | 学习进度、测验、笔记、搜索、导出 |
| `style.css` | 桌面与手机布局、键盘焦点样式 |
| `source.pdf` | 未修改的原书 v1.4 PDF |
| `LICENSE` / `NOTICE` | 开源许可、原作者署名与改编说明 |

原书印刷页码与 PDF 页码相差 8 页，网页链接已加偏移。部分 PDF 阅读器可能忽略页码锚点，可按标示页码手动定位。导读锁定 v1.4，上游新版目录可能不同。

## 修改与检查

修改课程请同时核对原书章节、答案解释、页码和对应实验。提交前运行：

```sh
node --check app.js
node --check content.js
node --check labs.js
```

并在浏览器验证受影响关卡、错误重试、刷新恢复与移动端布局。现有版本已手动验证完整 12 关和 24 道测验、术语搜索、笔记下载及桌面/手机布局。

欢迎通过 Issues 报告错字、交互问题或教学建议，通过 Pull Requests 改进内容。

## 许可与致谢

采用 [Apache License 2.0](LICENSE)。原书 Copyright 2025 Bojie Li；网页与互动改编 Copyright 2026 TomatoDroid。

原书作者为 **李博杰**；原始项目：[bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book)。本项目保留原文 PDF 的署名，将其核心思想重排为入门关卡，并新增模拟实验、讲解、测验和界面。完整声明见 [NOTICE](NOTICE)。
