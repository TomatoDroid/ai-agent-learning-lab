"""内置工具：演示与动手练习用。（本文件无练习，直接使用。）

文件类工具都限制在工作目录内，体现原书第一章的原则：
通用基础能力用于组合与探索，高风险操作用参数明确、权限受限的专用工具。
"""
from __future__ import annotations

import ast
import datetime as _dt
import operator
from pathlib import Path

from .guard import path_escapes_workspace
from .tools import Tool, ToolRegistry

# 固定汇率，保证演示可复现（原书第一章多币种汇总例子的数值）
RATES_TO_USD = {"USD": 1.0, "EUR": 2282608.7 / 2100000, "GBP": 2278481.01 / 1800000, "JPY": 2541806.02 / 380000000, "CNY": 0.14}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Mod: operator.mod}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("只支持数字和 + - * / ** % 运算")


def calculator(expression: str) -> str:
    value = _safe_eval(ast.parse(expression, mode="eval"))
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def convert_currency(amount: float, from_currency: str, to_currency: str = "USD") -> str:
    f, t = from_currency.upper(), to_currency.upper()
    if f not in RATES_TO_USD or t not in RATES_TO_USD:
        raise ValueError(f"不支持的币种：{f if f not in RATES_TO_USD else t}。支持：{', '.join(RATES_TO_USD)}")
    value = float(amount) * RATES_TO_USD[f] / RATES_TO_USD[t]
    return f"{f}->{t}: {value:.2f}"


def basic_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("convert_currency", "Convert an amount between currencies using fixed demo rates. Supported: USD, EUR, GBP, JPY, CNY.",
                      {"type": "object", "properties": {"amount": {"type": "number"}, "from_currency": {"type": "string", "description": "e.g. EUR"},
                                                        "to_currency": {"type": "string", "description": "default USD"}}, "required": ["amount", "from_currency"]},
                      convert_currency))
    reg.register(Tool("calculator", "Evaluate an arithmetic expression such as '2500000 + 2282608.7'. Only numbers and + - * / ** % are allowed.",
                      {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}, calculator))
    return reg


def add_clock(reg: ToolRegistry, clock=None) -> None:
    clock = clock or (lambda: _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    reg.register(Tool("now", "Get the current local date and time.", {"type": "object", "properties": {}}, lambda: clock()))


def add_workspace(reg: ToolRegistry, workspace: str | Path) -> Path:
    """注册 list_dir / read_file / write_file / delete_file，全部限制在 workspace 内。"""
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)

    def inside(path: str) -> Path:
        if path_escapes_workspace(path, str(root)):
            raise PermissionError(f"路径 {path} 不在工作目录内")
        return (root / path).resolve()

    def list_dir(path: str = ".") -> str:
        p = inside(path)
        return "\n".join(sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())) or "(空目录)"

    def read_file(path: str) -> str:
        return inside(path).read_text(encoding="utf-8")

    def write_file(path: str, content: str) -> str:
        p = inside(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {path}"

    def delete_file(path: str) -> str:
        inside(path).unlink()
        return f"deleted {path}"

    obj = {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的路径"}}, "required": ["path"]}
    reg.register(Tool("list_dir", "List files in a workspace directory.", {"type": "object", "properties": {"path": {"type": "string"}}}, list_dir))
    reg.register(Tool("read_file", "Read a UTF-8 text file in the workspace.", obj, read_file))
    reg.register(Tool("write_file", "Create or overwrite a text file in the workspace.",
                      {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
                      write_file, risk="medium"))
    reg.register(Tool("delete_file", "Delete a file in the workspace. Irreversible.", obj, delete_file, risk="high"))
    return root


def add_fake_web(reg: ToolRegistry, pages: dict[str, str]) -> None:
    """一个只读取预置页面的“浏览器”，用来离线演示间接注入。输出标记为不可信。"""
    def fetch_page(url: str) -> str:
        if url not in pages:
            raise KeyError(f"页面不存在：{url}")
        return pages[url]
    reg.register(Tool("fetch_page", "Fetch the text of a web page.", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
                      fetch_page, untrusted_output=True))
