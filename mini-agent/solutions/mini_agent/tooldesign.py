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
    # >>> EXERCISE 4.1a 工具描述检查
    # HINT: props = tool.parameters.get("properties", {})；参数描述 = props[name].get("description", "")。
    # HINT: 示例既可以写在 description 里，也可以写在任意一个参数描述里，把它们拼在一起再搜 EXAMPLE。
    desc = tool.description
    props = tool.parameters.get("properties", {})
    problems: list[str] = []
    if len(desc) < 40:
        problems.append("too_short")
    if not re.search(WHEN, desc, re.IGNORECASE):
        problems.append("no_when_to_use")
    if not re.search(BOUNDARY, desc, re.IGNORECASE):
        problems.append("no_boundary")
    all_text = desc + "\n" + "\n".join(p.get("description", "") for p in props.values())
    if not re.search(EXAMPLE, all_text, re.IGNORECASE):
        problems.append("no_example")
    if not re.search(RETURNS, desc, re.IGNORECASE):
        problems.append("no_returns")
    problems += [f"param_undocumented:{n}" for n, p in props.items() if not p.get("description")]
    problems += [f"required_unknown:{n}" for n in tool.parameters.get("required", []) if n not in props]
    return problems
    # <<< EXERCISE


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
    # >>> EXERCISE 4.1b 参数校验：快速失败，不做智能修正
    # HINT: 类型判断可以用上面写好的 _type_ok(value, expected)。
    # HINT: 实际类型名：{"str": "string", "bool": "boolean", "int": "integer", "float": "number", "list": "array", "dict": "object"}。
    if "__raw__" in args:
        return [f"arguments are not valid JSON: {args['__raw__']}"]
    props = schema.get("properties", {})
    errors = [f"missing required argument '{n}'" for n in schema.get("required", []) if n not in args]
    names = {"str": "string", "bool": "boolean", "int": "integer", "float": "number", "list": "array", "dict": "object"}
    for name, value in args.items():
        if name not in props:
            errors.append(f"unexpected argument '{name}'")
            continue
        spec = props[name]
        expected = spec.get("type")
        if expected and not _type_ok(value, expected):
            actual = names.get(type(value).__name__, type(value).__name__)
            errors.append(f"argument '{name}' should be {expected}, got {actual} {value!r}")
        elif "enum" in spec and value not in spec["enum"]:
            errors.append(f"argument '{name}' must be one of {spec['enum']}, got {value!r}")
    return errors
    # <<< EXERCISE


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
    # >>> EXERCISE 4.1c 忠实的编辑工具
    # HINT: 计数用 text.count(old_string)；替换一次用 text.replace(old_string, new_string, 1)。
    # HINT: 行号从 1 开始。first = next((l for l in old_string.splitlines() if l.strip()), old_string)。
    if not old_string:
        raise EditError("old_string is empty")
    if old_string == new_string:
        raise EditError("old_string and new_string are identical")
    n = text.count(old_string)
    if n == 0:
        first = next((l for l in old_string.splitlines() if l.strip()), old_string)
        best, best_no, best_ratio = "", 0, 0.0
        for no, line in enumerate(text.splitlines(), 1):
            r = difflib.SequenceMatcher(None, first, line).ratio()
            if r > best_ratio:
                best, best_no, best_ratio = line, no, r
        msg = "old_string not found."
        if best_ratio >= 0.6:
            i = next((k for k, (a, b) in enumerate(zip(first, best)) if a != b), min(len(first), len(best)))
            sent = _describe_char(first[i]) if i < len(first) else "end of line"
            has = _describe_char(best[i]) if i < len(best) else "end of line"
            msg += f" Closest line {best_no}: {best!r}. First difference at column {i + 1}: you sent {sent}, the file has {has}."
        else:
            msg += " No similar line in the file."
        raise EditError(msg)
    if n > 1 and not replace_all:
        raise EditError(f"old_string matches {n} times; include more surrounding lines to make it unique, or set replace_all=true")
    if replace_all:
        return text.replace(old_string, new_string), n
    return text.replace(old_string, new_string, 1), 1
    # <<< EXERCISE
