"""Agent Skills：目录常驻、正文按需加载（练习 2.4c）。

对应原书第二章“动态提示词与 Agent Skills”。每个 Skill 是一个目录，里面有 SKILL.md：
开头是 YAML frontmatter（至少有 name 和 description），后面是正文。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    path: Path

    def body(self) -> str:
        return parse_skill_md(self.path.read_text(encoding="utf-8"))[1]


def parse_skill_md(text: str) -> tuple[dict[str, str], str]:
    """拆出 frontmatter 和正文。只需支持最简单的 `key: value` 单行格式。

    - 文本必须以一行 "---" 开头，到下一行 "---" 为止是 frontmatter；否则抛 ValueError。
    - 每行按第一个冒号切开，key 和 value 都去掉首尾空白；value 两侧成对的引号去掉。空行忽略。
    - 正文是第二个 "---" 之后的全部内容，去掉首尾空白。
    """
    # >>> EXERCISE 2.4c 解析 SKILL.md
    # HINT: lines = text.splitlines()；lines[0].strip() 必须是 "---"；再找下一个 "---" 的行号。
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md 必须以 --- 开头的 frontmatter 开始")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("frontmatter 没有结束的 ---") from None
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:]).strip()
    # <<< EXERCISE


def load_skills(root: str | Path) -> dict[str, Skill]:
    """扫描 root 下每个子目录里的 SKILL.md，按 name 排序返回。缺少 name 或 description 的跳过。"""
    skills: dict[str, Skill] = {}
    for path in sorted(Path(root).glob("*/SKILL.md")):
        meta, _ = parse_skill_md(path.read_text(encoding="utf-8"))
        if meta.get("name") and meta.get("description"):
            skills[meta["name"]] = Skill(meta["name"], meta["description"], path)
    return dict(sorted(skills.items()))


def catalog_text(skills: dict[str, Skill]) -> str:
    """第一层：常驻上下文的目录。每行 “- name: description”，顺序固定，保证前缀稳定。"""
    # >>> EXERCISE 2.4c 目录
    # HINT: 第一行写 "Available skills (call load_skill to read one):"，之后每个 Skill 一行。
    lines = ["Available skills (call load_skill to read one):"]
    lines += [f"- {s.name}: {s.description}" for s in skills.values()]
    return "\n".join(lines)
    # <<< EXERCISE


def activation_message(skill: Skill) -> dict:
    """第二层：被选中的 Skill 正文作为一条 user 消息追加到末尾（Claude Code 的做法）。"""
    return {"role": "user", "content": f'<skill name="{skill.name}">\n{skill.body()}\n</skill>'}
