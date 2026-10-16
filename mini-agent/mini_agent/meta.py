"""代码作为元能力：思考工具、业务规则守门员、声明式生成界面（练习 5.3）。

对应原书第五章“代码：通用 Agent 的元能力”：
- 让 LLM 负责把问题形式化，让代码负责精确求解；
- 关键操作的规则写进工具内部，政策事实一律以服务端真值为准，不采信模型自报的参数；
- 生成界面时只输出“界面描述”，由客户端用受信任的组件目录渲染，而不是执行任意 HTML。
"""
from __future__ import annotations

import html
import itertools
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .execution import clip_output
from .tools import Tool, ToolRegistry

# ───────────────────────── 代码作为思考工具 ─────────────────────────


def solve_knights(people: list[str], says: dict[str, Callable[[dict[str, bool]], bool]]) -> list[dict[str, bool]]:
    """骑士与无赖：骑士永远说真话，无赖永远说假话。

    people：所有人；says：某人 → 他的陈述，陈述是一个函数，给定一种身份分配 world（人 → 是否骑士）返回陈述是否为真。
    枚举全部 2^n 种分配（按 itertools.product([True, False], repeat=n) 的顺序），
    保留“每个说了话的人：陈述为真 当且仅当 他是骑士”的分配，返回全部解。
    """
    # TODO 练习 5.3a：把谜题交给代码
    # 提示：world = dict(zip(people, values))；条件：all(says[p](world) == world[p] for p in says)。
    raise NotImplementedError("练习 5.3a 还没有完成：把谜题交给代码")


def run_python(code: str, timeout: float = 10, save: Callable[[str], str] | None = None) -> str:
    """最小的代码解释器：在临时目录里用隔离模式（-I）的子进程运行，超时返回结构化错误。
    注意：子进程不是沙盒（4.3 课），只适合在你自己的机器上跑你信任的任务。"""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"ERROR: killed after {timeout:g}s timeout (infinite loop?)"
    out = (r.stdout + r.stderr).rstrip("\n") + (f"\n[exit code {r.returncode}]" if r.returncode else "")
    return clip_output(out, save) if save else out


def add_code_interpreter(reg: ToolRegistry, timeout: float = 10) -> None:
    reg.register(Tool("python", "Use this for exact arithmetic, symbolic math, counting or brute-force search instead of computing in your head, "
                      "e.g. print(40*0.45 - 40*0.25). Only what you print() is returned. Cannot access the network or your files; "
                      f"killed after {timeout:g}s.",
                      {"type": "object", "properties": {"code": {"type": "string", "description": "Python 3 code, e.g. 'print(sum(range(10)))'"}},
                       "required": ["code"]}, lambda code: run_python(code, timeout), risk="medium"))


# ───────────────────────── 代码作为业务规则的守门员 ─────────────────────────

@dataclass
class Reservation:
    id: str
    cabin_class: str            # basic_economy / economy / business
    has_insurance: bool
    booking_time: datetime
    any_segment_used: bool = False
    flight_status: str = "scheduled"   # scheduled / cancelled_by_airline


@dataclass
class AirlineDB:
    reservations: dict[str, Reservation] = field(default_factory=dict)
    cancelled: list[str] = field(default_factory=list)
    mismatches: list[tuple[str, str, object, object]] = field(default_factory=list)  # (订单, 字段, 模型自报, 真值)


def cancel_reservation(db: AirlineDB, reservation_id: str, cancellation_reason: str,
                       expected_cabin_class: str | None = None, expected_has_insurance: bool | None = None,
                       *, now: datetime) -> dict:
    """取消订单（原书 τ-bench 航空取消政策的写法）。now 来自服务端时钟，不是模型给的参数。

    1. 订单不存在：{"success": False, "reason": "Reservation not found"}
    2. 模型自报的 expected_* 与数据库真值不一致：往 db.mismatches 追加 (订单号, 字段名, 自报值, 真值)，
       字段名为 "cabin_class" / "has_insurance"。只记录，不影响裁决。
    3. 按顺序裁决（全部用数据库真值）：
       - 已使用任何航段 → 失败 "Cannot cancel with used segments"
       - 距预订小时数 < 0 → 失败 "Booking time is in the future"
       - 距预订 <= 24 小时 → 成功 "Cancelled within 24-hour window"
       - 航空公司取消了航班 → 成功 "Airline cancelled flight"
       - 商务舱 → 成功 "Business class cancellation"
       - basic_economy / economy：有保险 → 成功 f"{舱位} with insurance"；没有 → 失败 f"{舱位} requires insurance"
       - 其他 → 失败 "Does not meet cancellation policy"
    成功时把订单号追加到 db.cancelled。返回 {"success": bool, "reason": str}。
    """
    # TODO 练习 5.3b：服务端真值守门
    # 提示：hours = (now - r.booking_time).total_seconds() / 3600。cancellation_reason 只做记录，不参与裁决。
    raise NotImplementedError("练习 5.3b 还没有完成：服务端真值守门")


def add_airline_tools(reg: ToolRegistry, db: AirlineDB, clock: Callable[[], datetime]) -> None:
    """查询工具 + 取消工具。时钟在注册时绑定在服务端：模型没有任何参数可以改变“现在几点”。"""
    def get_reservation(reservation_id: str) -> dict:
        r = db.reservations[reservation_id]
        return {"id": r.id, "cabin_class": r.cabin_class, "has_insurance": r.has_insurance,
                "booking_time": r.booking_time.isoformat(), "any_segment_used": r.any_segment_used, "flight_status": r.flight_status}

    reg.register(Tool("get_reservation", "Use this to look up a reservation before changing it. Returns cabin class, insurance, "
                      "booking time, segment usage and flight status. Read-only; it cannot modify anything.",
                      {"type": "object", "properties": {"reservation_id": {"type": "string", "description": "e.g. 'R123'"}},
                       "required": ["reservation_id"]}, get_reservation))
    reg.register(Tool(
        "cancel_reservation",
        "Use this to cancel a reservation. Cancellation policy (enforced by the server from database facts): "
        "1) never if any segment was used; 2) always within 24 hours of booking; 3) always if the airline cancelled the flight; "
        "4) always for business class; 5) basic_economy and economy only with travel insurance. "
        "Before calling, look up the reservation and check every rule; fill expected_* with what you found. "
        "Returns {success, reason}. If a rule forbids it, do not call; offer the user an alternative instead.",
        {"type": "object", "properties": {
            "reservation_id": {"type": "string", "description": "e.g. 'R123'"},
            "cancellation_reason": {"type": "string", "enum": ["change_of_plan", "airline_cancelled", "other"], "description": "why the user cancels"},
            "expected_cabin_class": {"type": "string", "description": "the cabin you saw in get_reservation, e.g. 'economy'"},
            "expected_has_insurance": {"type": "boolean", "description": "the insurance flag you saw, e.g. false"}},
         "required": ["reservation_id", "cancellation_reason"]},
        lambda **kw: cancel_reservation(db, now=clock(), **kw), risk="high"))


# ───────────────────────── 生成式 UI：声明式表单 ─────────────────────────

CATALOG = {"text", "number", "date", "select", "checkbox"}
_ID = re.compile(r"[a-z][a-z0-9_]*")


def render_form(spec: dict) -> str:
    """把模型给的“界面描述”渲染成 HTML。模型只能使用 CATALOG 里的组件，所有文字一律转义。

    spec = {"title": str, "fields": [{"id", "type", "label", "options"?: [str], "show_if"?: {"field": id, "equals": str}}]}

    校验（不合格抛 ValueError，信息如下）：
    - type 不在 CATALOG："component not in catalog: {type}"
    - id 不匹配 _ID（小写字母开头，只含小写字母、数字、下划线）或重复："bad field id: {id}"
    - select 没有 options 或 options 为空："select needs options: {id}"
    - show_if 引用的字段不存在或出现在当前字段之后："show_if must refer to an earlier field: {id}"

    输出（各部分用 "\\n" 连接）：
      <form class="gen-form">
      <h3>{title}</h3>
      每个字段一行：<div class="field"{条件属性}>{控件}</div>
        条件属性：有 show_if 时为  data-show-if="{field}={equals}" hidden （前面一个空格），否则为空
        控件：
          text/number/date：<label for="{id}">{label}</label><input id="{id}" name="{id}" type="{type}">
          checkbox：<label><input id="{id}" name="{id}" type="checkbox"> {label}</label>
          select：<label for="{id}">{label}</label><select id="{id}" name="{id}"> + 每个选项 <option value="{v}">{v}</option> + </select>
      <button type="submit">提交</button>
      </form>
    所有来自 spec 的文字（title、label、选项、show_if 的值）都用 html.escape(…, quote=True) 转义。
    """
    # TODO 练习 5.3c：声明式生成界面
    # 提示：e = lambda s: html.escape(str(s), quote=True)。先完整校验一遍，再生成，避免半截输出。
    raise NotImplementedError("练习 5.3c 还没有完成：声明式生成界面")
