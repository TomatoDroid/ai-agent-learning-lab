"""上下文层的注入防御：来源标记与可疑模式扫描（练习 2.3）。

对应原书第二章“提示注入：上下文安全的核心威胁”与实验 2-5。
记住书里的判断：这一层只能降低攻击成功率，给不出保证；兜底靠执行层（1.3 的 Guard）。
"""
from __future__ import annotations

import re

SUSPICIOUS = [
    r"ignore (all )?(the )?(previous|prior|above) instructions",
    r"disregard (all )?(the )?(previous|prior|above)",
    r"忽略(之前|以上|前面|上述)(的)?(所有)?(指令|指示|要求)",
    r"(reveal|print|output|show) (your|the) system prompt",
    r"(输出|泄露|告诉我)(你的)?系统提示词",
    r"(send|forward|email) .{0,40}@",
    r"(发送|转发|抄送).{0,20}@",
]


def wrap_external(content: str, source: str) -> str:
    """把外部内容包进来源标记，让模型知道这是数据而不是指令。

    格式：<external_content source="{source}">\\n{content}\\n</external_content>
    两条安全要求：
    1. 攻击者可能在内容里写一个 </external_content> 提前“闭合”标签，然后在标签外写指令。
       必须把内容中所有 <external_content 和 </external_content（不区分大小写）里的 "<" 换成 "&lt;"。
    2. source 只允许字母、数字和 . _ : / - 这些字符，其余字符一律删掉，防止从属性里逃逸。
    """
    # TODO 练习 2.3：来源标记
    # 提示：用 re.sub(r"<(/?external_content)", r"&lt;\1", content, flags=re.IGNORECASE) 处理内容。
    # 提示：用 re.sub(r"[^A-Za-z0-9._:/-]", "", source) 清洗来源。
    raise NotImplementedError("练习 2.3 还没有完成：来源标记")


def scan_injection(text: str) -> list[str]:
    """返回 text 中命中的可疑模式（SUSPICIOUS 中的正则原文），不区分大小写。

    这只是辅助手段：措辞稍一变化就能绕过。用它来打日志、提高警惕，而不是当成安全边界。
    """
    # TODO 练习 2.3：可疑模式扫描
    # 提示：遍历 SUSPICIOUS，用 re.search(pattern, text, re.IGNORECASE)。
    raise NotImplementedError("练习 2.3 还没有完成：可疑模式扫描")
