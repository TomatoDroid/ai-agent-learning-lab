"""从参考答案生成练习版代码。

solutions/mini_agent/ 是唯一的事实来源。其中用

    # >>> EXERCISE 1.2 标题
    # HINT: 提示……
    参考实现……
    # <<< EXERCISE

标记的区域，在练习版 mini_agent/ 里会被替换成 TODO 注释和 raise NotImplementedError。

    python tools/make_exercises.py           重新生成 mini_agent/（会覆盖你的练习进度！）
    python tools/make_exercises.py --check   只检查是否需要重新生成（CI 用）
    python tools/make_exercises.py --file loop.py   只重置一个文件
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "solutions" / "mini_agent"
DST = ROOT / "mini_agent"
BEGIN = re.compile(r"^(?P<indent>\s*)# >>> EXERCISE (?P<id>\S+)\s*(?P<title>.*)$")
END = re.compile(r"^\s*# <<< EXERCISE\s*$")
HINT = re.compile(r"^\s*# HINT: ?(?P<text>.*)$")


def strip(text: str, name: str) -> str:
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = BEGIN.match(lines[i])
        if not m:
            if END.match(lines[i]):
                sys.exit(f"{name}:{i + 1}: 多余的 <<< EXERCISE")
            out.append(lines[i])
            i += 1
            continue
        indent, ex_id, title = m["indent"], m["id"], m["title"].strip()
        out.append(f"{indent}# TODO 练习 {ex_id}：{title}")
        i += 1
        while i < len(lines) and not END.match(lines[i]):
            if BEGIN.match(lines[i]):
                sys.exit(f"{name}:{i + 1}: 练习区域不能嵌套")
            h = HINT.match(lines[i])
            if h:
                out.append(f"{indent}# 提示：{h['text']}")
            i += 1
        if i == len(lines):
            sys.exit(f"{name}: 练习 {ex_id} 缺少 <<< EXERCISE")
        out.append(f'{indent}raise NotImplementedError("练习 {ex_id} 还没有完成：{title}")')
        i += 1
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--file")
    args = ap.parse_args()
    sources = [SRC / args.file] if args.file else sorted(SRC.glob("*.py"))
    stale = []
    for src in sources:
        target = DST / src.name
        generated = strip(src.read_text(encoding="utf-8"), src.name)
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != generated:
                stale.append(src.name)
        else:
            DST.mkdir(exist_ok=True)
            target.write_text(generated, encoding="utf-8")
            print(f"生成 {target.relative_to(ROOT)}")
    if args.check and stale:
        sys.exit("练习版与参考答案不同步，请运行 python tools/make_exercises.py：" + ", ".join(stale))


if __name__ == "__main__":
    main()
