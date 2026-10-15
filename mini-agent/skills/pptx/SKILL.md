---
name: pptx
description: 需要创建、编辑或分析 PowerPoint（.pptx）文件时使用。只是聊幻灯片内容、不产出文件时不要用。
---

# PPTX（教学用的简化版）

真实的官方 Skill 见 https://github.com/anthropics/skills 。这里只演示结构。

1. 读取：先把 .pptx 转成 Markdown 看文字，再按需解压看 XML。
2. 生成：先列大纲（每页一句话结论），用户确认后再生成。
3. 需要从 HTML 模板生成时，再去读 html2pptx.md（第三层细则，本示例未附带）。
