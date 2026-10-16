"""Coding Agent 的工具箱：搜索、首尾匹配编辑、命令语义解析、bash（练习 5.2）。

对应原书第五章“Coding Agent 的实现技巧”“搜索工具”“文件编辑工具”“安全”。
七个核心工具里，read_file / write_file / edit_file 在 4.1 课已经有了，这里补上 glob、grep、bash，
以及一个比关键字黑名单更可靠的 shell 命令分析器。
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

from .execution import clip_output
from .tooldesign import EditError
from .tools import Tool, ToolRegistry

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache"}
SYSTEM_PATHS = ("/etc", "/usr", "/bin", "/sbin", "/lib", "/boot", "/sys", "/proc", "/dev", "/var/lib", "/root", "~/.ssh")
NETWORK = {"curl", "wget", "nc", "ncat", "scp", "ssh", "rsync", "ftp"}
SHELLS = {"sh", "bash", "zsh", "dash"}
SEPARATORS = {";", "&&", "||", "|", "&"}


def _files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(filenames):
            yield Path(dirpath, f)


def _glob_regex(pattern: str) -> re.Pattern:
    """把 glob 翻译成正则：** / 匹配零层或多层目录，* 和 ? 不跨越 /。"""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def glob_files(root: str | Path, pattern: str = "**/*") -> list[str]:
    """按文件名模式找文件（不读内容），返回相对路径，已排序，跳过隐藏目录和 SKIP_DIRS。
    模式里没有 / 时只比较文件名（"test_*.py" 能找到 tests/test_api.py）。"""
    root, rx = Path(root), _glob_regex(pattern)
    rels = (p.relative_to(root).as_posix() for p in _files(root))
    return [r for r in rels if rx.match(r if "/" in pattern else r.rsplit("/", 1)[-1])]


def grep(root: str | Path, pattern: str, glob: str = "**/*", max_results: int = 50, ignore_case: bool = False) -> str:
    """在 glob_files(root, glob) 列出的文件里逐行搜索正则 pattern。

    - 每个命中一行："{相对路径}:{行号}: {该行去掉行尾空白}"，按文件顺序、行号顺序
    - 不是 UTF-8 的文件（二进制）跳过
    - pattern 不是合法正则：抛 ValueError(f"invalid regex: {原因}")
    - 没有命中：返回 "No matches."
    - 命中超过 max_results：只返回前 max_results 行，再加一行
      "[{总数} matches, showing first {max_results}; narrow the pattern or the glob]"
    """
    # >>> EXERCISE 5.2a grep
    # HINT: re.compile(pattern, re.IGNORECASE if ignore_case else 0)，捕获 re.error。
    # HINT: 读文件用 path.read_text(encoding="utf-8")，捕获 UnicodeDecodeError 跳过。
    try:
        rx = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as exc:
        raise ValueError(f"invalid regex: {exc}") from None
    root = Path(root)
    hits: list[str] = []
    for rel in glob_files(root, glob):
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for no, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{rel}:{no}: {line.rstrip()}")
    if not hits:
        return "No matches."
    if len(hits) > max_results:
        return "\n".join(hits[:max_results] + [f"[{len(hits)} matches, showing first {max_results}; narrow the pattern or the glob]"])
    return "\n".join(hits)
    # <<< EXERCISE


def replace_between(text: str, start: str, end: str, new: str) -> str:
    """首尾匹配编辑（原书“字符串首尾匹配”方案）：只给出要替换区域的开头和结尾，中间省略。

    区域 = 某处 start 的起点，到它之后第一次出现的 end 的终点（end 必须在 start 结束之后才算）。
    - start 一次都没出现：EditError("start not found")
    - 有 start，但它们之后都找不到 end：EditError("end not found after start")
    - 符合条件的区域多于一个：EditError(f"start/end pair matches {n} regions; include more lines in start")
    - 恰好一个：返回替换后的文本
    """
    # >>> EXERCISE 5.2c 首尾匹配编辑
    # HINT: 用 text.find(start, pos) 循环找出所有 start 的位置 i；对每个 i，j = text.find(end, i + len(start))。
    starts, i = [], text.find(start)
    while start and i != -1:
        starts.append(i)
        i = text.find(start, i + 1)
    if not starts:
        raise EditError("start not found")
    regions = []
    for i in starts:
        j = text.find(end, i + len(start))
        if j != -1:
            regions.append((i, j + len(end)))
    if not regions:
        raise EditError("end not found after start")
    if len(regions) > 1:
        raise EditError(f"start/end pair matches {len(regions)} regions; include more lines in start")
    a, b = regions[0]
    return text[:a] + new + text[b:]
    # <<< EXERCISE


# ───────────────────────── 命令语义解析 ─────────────────────────

def naive_blacklist(cmd: str) -> bool:
    """反面教材：关键字黑名单。返回 True 表示拦下。"""
    return any(k in cmd for k in ("rm -rf", "rm -fr", "mkfs", "dd if="))


def _is_system_path(p: str) -> bool:
    return p == "/" or any(p == s or p.startswith(s + "/") for s in SYSTEM_PATHS)


def _split(cmd: str) -> list[tuple[list[str], bool]]:
    """把一条命令拆成简单命令序列 [(词列表, 是否由管道接入)]。"""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|<>")
    lex.whitespace_split = True
    segments, cur, piped = [], [], False
    for tok in lex:
        if tok in SEPARATORS:
            if cur:
                segments.append((cur, piped))
            cur, piped = [], tok == "|"
        else:
            cur.append(tok)
    if cur:
        segments.append((cur, piped))
    return segments


def analyze_command(cmd: str, _depth: int = 0) -> list[str]:
    """理解一条 shell 命令真正会做什么，返回发现（去重，按发现顺序）。词汇表：

    - "dynamic_command"：命令名本身是 $(...)、反引号或 $变量，执行前无法知道它是什么
    - "recursive_delete"：rm 同时带递归（-r/-R/--recursive）和强制（-f/--force）
    - "find_delete"：find 带 -delete，或 -exec/-execdir/-ok 后面跟着 rm/shred/unlink
    - "pipe_to_shell"：管道把内容喂给 sh/bash/zsh/dash（且没有 -c）
    - "system_write:{路径}"：> 或 >> 重定向、curl -o/--output、wget -O、cp/mv/tee 的目标、dd 的 of=，指向系统路径；
      rm 的目标是系统路径也算
    - "privilege:sudo"
    - "network:{命令名}"：NETWORK 里的命令（致命三要素的“对外通信”）

    要求：
    1. 先把 $(...) 和 `...` 里的内容取出来，递归分析（发现并入结果），原位置换成占位符 __SUB{n}__；
       命令名是占位符时记 dynamic_command，若那段子命令只是 echo/printf 一个词（$(echo rm)），按那个词继续分析；
    2. 用 _split 拆成简单命令；每段先处理重定向（> / >> 和其后的路径），再去掉开头的 VAR=值、sudo、env、nohup、time；
    3. find 的 -exec 部分、xargs 后面的命令（只跳过 xargs 自己的选项）、sh -c "…" 的字符串，都要递归分析；
    4. 递归深度超过 5 层时返回 ["too_nested"]。
    命令名比较用 os.path.basename（/bin/rm 也是 rm）。
    """
    # >>> EXERCISE 5.2b 命令语义解析
    # HINT: 取子命令：re.sub(r"\$\(([^()]*)\)|`([^`]*)`", 替换函数, cmd)，替换函数里记下 m.group(1) or m.group(2)。
    # HINT: 写一个内部函数 simple(words, piped) 处理一个简单命令，它可以对 -exec / xargs 的部分再调用自己。
    if _depth > 5:
        return ["too_nested"]
    findings: list[str] = []

    def add(f: str) -> None:
        if f not in findings:
            findings.append(f)

    subs: list[str] = []

    def grab(m):
        subs.append(m.group(1) if m.group(1) is not None else m.group(2))
        return f"__SUB{len(subs) - 1}__"

    text = re.sub(r"\$\(([^()]*)\)|`([^`]*)`", grab, cmd)
    for s in subs:
        for f in analyze_command(s, _depth + 1):
            add(f)

    def simple(words: list[str], piped: bool) -> None:
        rest, k = [], 0
        while k < len(words):
            if words[k] in (">", ">>") and k + 1 < len(words):
                if _is_system_path(words[k + 1]):
                    add(f"system_write:{words[k + 1]}")
                k += 2
                continue
            rest.append(words[k])
            k += 1
        while rest and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", rest[0]) or rest[0] in ("sudo", "env", "nohup", "time")):
            if rest[0] == "sudo":
                add("privilege:sudo")
            rest = rest[1:]
        if not rest:
            return
        name = rest[0]
        if "__SUB" in name or name.startswith("$"):
            add("dynamic_command")
            m = re.fullmatch(r"__SUB(\d+)__", name)
            echoed = m and re.fullmatch(r"\s*(?:echo|printf)\s+['\"]?([\w./-]+)['\"]?\s*", subs[int(m.group(1))])
            if echoed:  # $(echo rm) 换汤不换药：按 rm 继续分析
                name = echoed.group(1)
        base, args = os.path.basename(name), rest[1:]
        short = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
        if base == "rm":
            if ("r" in short or "R" in short or "--recursive" in args) and ("f" in short or "--force" in args):
                add("recursive_delete")
            for a in args:
                if not a.startswith("-") and _is_system_path(a):
                    add(f"system_write:{a}")
        elif base == "find":
            if "-delete" in args:
                add("find_delete")
            for flag in ("-exec", "-execdir", "-ok"):
                if flag in args:
                    inner = args[args.index(flag) + 1:]
                    inner = inner[: next((n for n, w in enumerate(inner) if w in (";", "+")), len(inner))]
                    if inner and os.path.basename(inner[0]) in ("rm", "shred", "unlink"):
                        add("find_delete")
                    if inner:
                        simple(inner, False)
        elif base == "xargs":
            first = next((n for n, a in enumerate(args) if not a.startswith("-")), len(args))
            if args[first:]:
                simple(args[first:], False)  # 只跳过 xargs 自己的选项，内层命令的选项要保留
        elif base in SHELLS:
            if "-c" in args and args.index("-c") + 1 < len(args):
                for f in analyze_command(args[args.index("-c") + 1], _depth + 1):
                    add(f)
            elif piped:
                add("pipe_to_shell")
        elif base in NETWORK:
            add(f"network:{base}")
            for flag in ("-o", "--output", "-O"):
                if flag in args and args.index(flag) + 1 < len(args) and _is_system_path(args[args.index(flag) + 1]):
                    add(f"system_write:{args[args.index(flag) + 1]}")
        elif base in ("cp", "mv", "tee", "install", "ln"):
            targets = [a for a in args if not a.startswith("-")]
            dests = targets if base == "tee" else targets[-1:]
            for d in dests:
                if _is_system_path(d):
                    add(f"system_write:{d}")
        elif base == "dd":
            for a in args:
                if a.startswith("of=") and _is_system_path(a[3:]):
                    add(f"system_write:{a[3:]}")

    for words, piped in _split(text):
        simple(words, piped)
    return findings
    # <<< EXERCISE


def command_risk(findings: list[str]) -> str:
    """只有网络访问 → medium；有任何其他发现 → high；没有发现 → low。"""
    if not findings:
        return "low"
    return "medium" if all(f.startswith("network:") for f in findings) else "high"


def semantic_classifier(payload: dict) -> tuple[str, str]:
    """给 4.3 的 SidecarGuard 用：bash 命令按语义分析，high 风险拒绝。"""
    cmd = payload.get("arguments", {}).get("command")
    if payload.get("tool") != "bash" or not isinstance(cmd, str):
        return "allow", ""
    found = analyze_command(cmd)
    return ("deny", ", ".join(found)) if command_risk(found) == "high" else ("allow", "")


# ───────────────────────── 组装工具 ─────────────────────────

def add_coding_tools(reg: ToolRegistry, root: str | Path, timeout: float = 120) -> Path:
    """注册 glob、grep、bash。bash 在 root 下执行，记住 cd 之后的目录（持久会话的最小版本），
    超时返回结构化错误而不是静默杀掉，长输出交给 clip_output 处理。"""
    root = Path(root).resolve()
    state = {"cwd": root, "n": 0}
    out_dir = root / ".mini-agent" / "outputs"

    def save(text: str) -> str:
        out_dir.mkdir(parents=True, exist_ok=True)
        state["n"] += 1
        p = out_dir / f"out-{state['n']}.txt"
        p.write_text(text, encoding="utf-8")
        return p.relative_to(root).as_posix()

    def bash(command: str) -> str:
        script = f"{command}\n__rc=$?\necho\necho __CWD__=$(pwd)\nexit $__rc"
        try:
            r = subprocess.run(["bash", "-c", script], cwd=state["cwd"], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            tail = exc.stdout or ""
            if isinstance(tail, bytes):
                tail = tail.decode(errors="replace")
            return f"ERROR: command killed after {timeout:g}s timeout. Last output:\n{tail[-500:]}"
        out = r.stdout
        m = re.search(r"\n?__CWD__=(.*)\n?$", out)
        if m:
            new = Path(m.group(1))
            state["cwd"] = new if new == root or root in new.parents else root  # 不让会话目录跑出工作区
            out = out[: m.start()]
        body = (out + (("\n" if out and r.stderr else "") + r.stderr)).rstrip("\n")
        return clip_output(f"{body}\n[exit code {r.returncode}]".lstrip("\n"), save)

    reg.register(Tool("glob", "Use this to find files by NAME pattern, e.g. '**/*.py' or 'tests/test_*.py'. Returns relative paths, "
                      "one per line. It does not look inside files; use grep for that.",
                      {"type": "object", "properties": {"pattern": {"type": "string", "description": "glob pattern, e.g. 'src/**/*.ts'"}},
                       "required": ["pattern"]}, lambda pattern: "\n".join(glob_files(root, pattern)) or "No files."))
    reg.register(Tool("grep", "Use this to search file CONTENTS with a regular expression, e.g. 'def average' or 'TODO'. "
                      "Returns 'path:line: text' lines, at most max_results; cannot search binary files.",
                      {"type": "object", "properties": {
                          "pattern": {"type": "string", "description": "Python regex, e.g. 'class \\w+Error'"},
                          "glob": {"type": "string", "description": "limit to files matching this, e.g. '**/*.py'"},
                          "ignore_case": {"type": "boolean", "description": "e.g. true to match TODO and todo"}},
                       "required": ["pattern"]},
                      lambda pattern, glob="**/*", ignore_case=False: grep(root, pattern, glob, ignore_case=ignore_case)))
    reg.register(Tool("bash", "Use this to run a shell command in the workspace, e.g. 'python -m pytest -q'. The working directory "
                      "persists between calls. Do not use it to read or edit files; use read_file and edit_file. "
                      f"Returns stdout, stderr and the exit code; long output is clipped and saved to a file; killed after {timeout:g}s.",
                      {"type": "object", "properties": {"command": {"type": "string", "description": "e.g. 'cd src && ls'"}},
                       "required": ["command"]}, bash, risk="medium"))
    return root
