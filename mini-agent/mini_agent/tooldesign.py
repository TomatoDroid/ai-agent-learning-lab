"""工具设计的通用原则：描述检查、参数校验、忠实的编辑工具（练习 4.1）。

对应原书第四章“工具设计的通用原则”：
- 工具描述要写清“什么时候用”、边界、示例和返回值；
- 参数传递必须保真：不悄悄修正模型的输入，发现不合法就快速失败并说清楚为什么。
"""
from __future__ import annotations

import difflib
import re
from dataclasses import replace
from typing import Any

from .tools import Tool

WHEN = r"\b[Uu]se (this )?(only )?(when|for|to)\b|\bwhen you need\b|当.{0,30}时|用于"
BOUNDARY = r"\b(do not|don't|cannot|can't|only|not for|never|must|instead)\b|不能|不要|只能|不支持|仅"
EXAMPLE = r"e\.g\.|\bexamples?\b|例如|比如"
RETURNS = r"\breturns?\b|返回"
JSON_TYPES = {"string": str, "boolean": bool, "array": list, "object": dict}


class ArgumentError(ValueError):
    pass


class EditError(ValueError):
    pass


def lint_description(tool: Tool) -> list[str]:
    """检查一条工具定义，返回问题代码（按下面的顺序；没有问题返回空列表）。

    - "too_short"：description 少于 40 个字符
    - "no_when_to_use"：没说什么时候用（不匹配 WHEN）
    - "no_boundary"：没说做不到什么（不匹配 BOUNDARY）
    - "no_example"：description 和所有参数描述里都没有示例（不匹配 EXAMPLE）
    - "no_returns"：没说返回什么（不匹配 RETURNS）
    - "param_undocumented:{name}"：参数没有 description（按 properties 的顺序）
    - "required_unknown:{name}"：required 里列了 properties 中不存在的参数
    正则匹配都不区分大小写。
    """
    # TODO 练习 4.1a：工具描述检查
    # 提示：props = tool.parameters.get("properties", {})；参数描述 = props[name].get("description", "")。
    # 提示：示例既可以写在 description 里，也可以写在任意一个参数描述里，把它们拼在一起再搜 EXAMPLE。
    raise NotImplementedError("练习 4.1a 还没有完成：工具描述检查")


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, JSON_TYPES.get(expected, object))


def validate_arguments(schema: dict, args: dict) -> list[str]:
    """按 JSON Schema 的一个子集校验参数，返回错误列表（空列表表示合法）。绝不修改 args。

    顺序：
    1. args 里有 "__raw__"（模型给的 JSON 不合法，见 messages.ToolCall.from_api）：
       只返回一条 "arguments are not valid JSON: {原文}"。
    2. required 中缺失的参数："missing required argument '{name}'"
    3. 按 args 的顺序逐个检查：
       - 不在 properties 里："unexpected argument '{name}'"
       - 类型不符（只看 type 字段：string/number/integer/boolean/array/object）：
         "argument '{name}' should be {type}, got {实际类型名} {repr(value)}"，
         实际类型名用 JSON 的叫法：str→string，bool→boolean，int→integer，float→number，list→array，dict→object
       - 有 enum 且值不在其中："argument '{name}' must be one of {enum}, got {repr(value)}"
    注意 True 不是 integer，"5" 也不是 integer：不做任何“智能”转换。
    """
    # TODO 练习 4.1b：参数校验：快速失败，不做智能修正
    # 提示：类型判断可以用上面写好的 _type_ok(value, expected)。
    # 提示：实际类型名：{"str": "string", "bool": "boolean", "int": "integer", "float": "number", "list": "array", "dict": "object"}。
    raise NotImplementedError("练习 4.1b 还没有完成：参数校验：快速失败，不做智能修正")


def strict(tool: Tool) -> Tool:
    """返回一个先校验参数、再执行的工具副本。校验失败抛 ArgumentError，错误信息里列出全部问题。"""
    def fn(**kwargs):
        try:
            errors = validate_arguments(tool.parameters, kwargs)
        except NotImplementedError:  # 练习 4.1b 还没做时不校验，不影响前面的模块
            errors = []
        if errors:
            raise ArgumentError("; ".join(errors))
        return tool.fn(**kwargs)
    return replace(tool, fn=fn)


def _describe_char(ch: str) -> str:
    return f"{ch!r} (U+{ord(ch):04X})"


def apply_edit(text: str, old_string: str, new_string: str, replace_all: bool = False) -> tuple[str, int]:
    """精确替换，返回 (新文本, 替换次数)。对 old_string 和 new_string 一个字符都不改。

    失败时抛 EditError，信息要让模型能自己诊断：
    - old_string 为空："old_string is empty"
    - old_string 和 new_string 相同："old_string and new_string are identical"
    - 找不到："old_string not found."，再附上诊断（见下）
    - 出现多次且 replace_all 为 False：
      "old_string matches {n} times; include more surrounding lines to make it unique, or set replace_all=true"

    找不到时的诊断：取 old_string 的第一个非空行 first，在 text 的各行中找与它最相似的一行
    （difflib.SequenceMatcher(None, first, line).ratio()，取最大的，相同取靠前的）。
    相似度 >= 0.6 时追加：
      " Closest line {行号}: {line!r}."
    并找到两者第一个不同字符的位置 i（逐字符比较，长度不同时较短者结束处即为 i），追加：
      " First difference at column {i + 1}: you sent {_describe_char(first[i])}, the file has {_describe_char(line[i])}."
    （某一方在 i 处已结束时，该方写 "end of line"。）相似度 < 0.6 时追加 " No similar line in the file."
    """
    # TODO 练习 4.1c：忠实的编辑工具
    # 提示：计数用 text.count(old_string)；替换一次用 text.replace(old_string, new_string, 1)。
    # 提示：行号从 1 开始。first = next((l for l in old_string.splitlines() if l.strip()), old_string)。
    raise NotImplementedError("练习 4.1c 还没有完成：忠实的编辑工具")
