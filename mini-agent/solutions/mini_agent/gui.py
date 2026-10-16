"""Computer Use 与机器人：坐标缩放、结构化元素索引、逐步检查的闭环（练习 6.3）。

对应原书第六章“Computer Use：GUI 自动化 Agent”和“机器人操作：以 XLeRobot 整理桌面为例”。
这里没有真实屏幕和机械臂，只保留决定成败的三段逻辑：

- 坐标预测路线：截图要按宽高比缩放到模型训练时的分辨率，模型给出的坐标再映射回真实屏幕；
- 选择题路线：从 DOM 里枚举可交互元素并编号，模型只需说“点击 [2]”；
- 物理世界：工具返回“已尝试”不等于做成了，每个技能之后都要重新观察、检查后置条件。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .tools import Tool, ToolRegistry

# ---------- 6.3a 分辨率匹配与双向坐标缩放 ----------

TARGETS = [("XGA", 1024, 768), ("WXGA", 1280, 800), ("FWXGA", 1366, 768)]


@dataclass
class Scaler:
    """真实屏幕与模型分辨率之间的双向坐标换算。用 for_screen() 创建。"""
    screen: tuple[int, int]
    name: str
    target: tuple[int, int]

    @classmethod
    def for_screen(cls, width: int, height: int) -> "Scaler":
        """在 TARGETS 里选宽高比最接近屏幕的一档（差值相同取靠前的）。

        2560×1440（16:9）→ FWXGA 1366×768；不能把 16:9 硬拉进 4:3 的 1024×768，画面会被压扁、坐标系统性偏移。
        """
        # >>> EXERCISE 6.3a 按宽高比选目标分辨率，坐标双向缩放
        # HINT: min(TARGETS, key=...) 比较 abs(w / h - 屏幕宽高比)；下面的 to_model / to_screen 各乘一个比例再 round。
        ratio = width / height
        name, tw, th = min(TARGETS, key=lambda t: abs(t[1] / t[2] - ratio))
        return cls((width, height), name, (tw, th))
        # <<< EXERCISE

    def to_model(self, x: float, y: float) -> tuple[int, int]:
        """真实屏幕坐标 → 模型看到的截图坐标。"""
        # >>> EXERCISE 6.3a 按宽高比选目标分辨率，坐标双向缩放
        return round(x * self.target[0] / self.screen[0]), round(y * self.target[1] / self.screen[1])
        # <<< EXERCISE

    def to_screen(self, x: float, y: float) -> tuple[int, int]:
        """模型输出的坐标 → 真实屏幕坐标（执行点击时用）。"""
        # >>> EXERCISE 6.3a 按宽高比选目标分辨率，坐标双向缩放
        return round(x * self.screen[0] / self.target[0]), round(y * self.screen[1] / self.target[1])
        # <<< EXERCISE


# ---------- 6.3b 结构化元素索引（SoM 思想在 Web 上的结构化实现） ----------

INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea"}
INTERACTIVE_ROLES = {"button", "link", "textbox", "checkbox", "radio", "combobox", "menuitem", "tab", "switch"}
SHOWN_ATTRS = ["id", "type", "name", "placeholder", "aria-label", "role", "href", "value"]


@dataclass
class Element:
    id: int
    line: str
    center: tuple[int, int]
    node: dict = field(repr=False)


def index_elements(nodes: list[dict]) -> list[Element]:
    """从拍平的 DOM 节点列表里枚举可交互元素并编号（从 1 开始，按文档顺序）。

    节点形如 {"tag": "input", "attrs": {...}, "box": (x, y, w, h), "text": "可选", "visible": True}。
    - 可交互：tag 在 INTERACTIVE_TAGS，或 attrs["role"] 在 INTERACTIVE_ROLES，或 attrs 里有 "onclick"；
    - 跳过：visible 为 False、宽或高为 0、attrs 里有 "disabled"；
    - line：按原顺序只保留 SHOWN_ATTRS 里的属性（class、style 之类对模型没用），形如 '<input type="text" placeholder="Search" />'，
      有 text 时写成 '<button id="go">搜索</button>'；前面加上 "[编号] "；
    - center：边框中心 (x + w // 2, y + h // 2)，模型说“点 [2]”时就点这里。
    """
    # >>> EXERCISE 6.3b 枚举可交互元素并编号
    # HINT: 先过滤再编号，编号才连续；属性拼成 f'{k}="{v}"'，用空格连接。
    out: list[Element] = []
    for node in nodes:
        attrs = node.get("attrs", {})
        x, y, w, h = node.get("box", (0, 0, 0, 0))
        interactive = node["tag"] in INTERACTIVE_TAGS or attrs.get("role") in INTERACTIVE_ROLES or "onclick" in attrs
        if not interactive or not node.get("visible", True) or w == 0 or h == 0 or "disabled" in attrs:
            continue
        shown = " ".join(f'{k}="{v}"' for k, v in attrs.items() if k in SHOWN_ATTRS)
        open_tag = f"<{node['tag']}{' ' + shown if shown else ''}"
        text = node.get("text")
        markup = f"{open_tag}>{text}</{node['tag']}>" if text else f"{open_tag} />"
        out.append(Element(len(out) + 1, f"[{len(out) + 1}] {markup}", (x + w // 2, y + h // 2), node))
    return out
    # <<< EXERCISE


class FakeBrowser:
    """一个只有几页的假浏览器，用来驱动“选择题”式的 Web Agent。

    pages：{页面名: {"nodes": [...], "text": 页面可读文字}}。节点可以带 "goto"（点击后跳转）和 "submit"（点击时
    读取某个输入框的值，跳转到 pages[goto] 并把 {query} 替换成该值）。
    每次 observe() 重新编号；页面变化后旧编号作废，用旧编号操作会得到明确的错误，提示先 observe。
    """

    def __init__(self, pages: dict[str, dict], start: str):
        self.pages, self.page = pages, start
        self.values: dict[int, str] = {}       # 当前页面上输入框的值：DOM 下标 → 值
        self.elements: list[Element] | None = None
        self.query = ""
        self.actions: list[str] = []

    def _nodes(self) -> list[dict]:
        return self.pages[self.page]["nodes"]

    def observe(self) -> str:
        self.elements = index_elements(self._nodes())
        text = self.pages[self.page].get("text", "").replace("{query}", self.query)
        return "\n".join([f"Page: {self.page}", "Elements:", *[e.line for e in self.elements], "Text:", text])

    def _element(self, element: int) -> Element:
        if self.elements is None or not 1 <= element <= len(self.elements):
            raise LookupError(f"element {element} no longer exists; call observe again")
        return self.elements[element - 1]

    def type_text(self, element: int, text: str) -> str:
        e = self._element(element)
        self.values[self._nodes().index(e.node)] = text
        self.actions.append(f"type {element} {text}")
        return f"typed into [{element}]"

    def click(self, element: int) -> str:
        e = self._element(element)
        self.actions.append(f"click {element} at {e.center}")
        if "submit" in e.node:
            self.query = self.values.get(e.node["submit"], "")
        if "goto" in e.node:
            self.page, self.values, self.elements = e.node["goto"], {}, None
            return f"clicked [{element}]; page changed to {self.page}, call observe"
        return f"clicked [{element}]"

    def tools(self) -> ToolRegistry:
        reg = ToolRegistry()
        num = {"type": "integer", "description": "元素编号，来自最近一次 observe"}
        reg.register(Tool("observe", "列出当前页面的可交互元素（带编号）和可读文字。页面变化后必须重新调用。",
                          {"type": "object", "properties": {}}, self.observe, untrusted_output=True))
        reg.register(Tool("type_text", "在编号为 element 的输入框里输入文字",
                          {"type": "object", "properties": {"element": num, "text": {"type": "string"}}, "required": ["element", "text"]},
                          self.type_text, risk="medium"))
        reg.register(Tool("click", "点击编号为 element 的元素",
                          {"type": "object", "properties": {"element": num}, "required": ["element"]}, self.click, risk="medium"))
        return reg


# ---------- 6.3c 机器人：逐步检查的闭环 ----------

class TabletopSim:
    """桌面模拟器：红色杯子放进托盘、黄色废纸放进垃圾盒（原书实验 6-13 的同一任务）。

    pick / place 只返回 "attempted"——执行器不知道自己有没有成功，就像真实机械臂；
    只有 observe() 返回的状态才是事实。failures 是注入的瞬时失败：每次 pick/place 依次取一个布尔值，
    True 表示这一次没有做成（夹空了、没放进去），列表用完后都成功。
    """

    def __init__(self, objects=("red_cup", "yellow_paper"), failures: list[bool] | None = None):
        self.where = {o: "table" for o in objects}
        self.held: str | None = None
        self.failures = list(failures or [])
        self.calls: list[str] = []

    def _fails(self) -> bool:
        return self.failures.pop(0) if self.failures else False

    def pick(self, obj: str) -> str:
        self.calls.append(f"pick({obj})")
        if not self._fails() and self.held is None and self.where.get(obj) not in (None, "gripper"):
            self.where[obj], self.held = "gripper", obj
        return "attempted"

    def place(self, obj: str, target: str) -> str:
        self.calls.append(f"place({obj},{target})")
        if not self._fails() and self.held == obj:
            self.where[obj], self.held = target, None
        return "attempted"

    def observe(self) -> dict[str, str]:
        self.calls.append("observe()")
        return dict(self.where)


@dataclass
class Report:
    success: bool          # 环境里的事实
    claimed: bool          # 执行策略自己认为完成了没有
    calls: int             # 工具调用次数（含 observe）
    recoveries: int = 0
    log: list[str] = field(default_factory=list)


def postcondition(step: tuple, state: dict[str, str]) -> bool:
    """一个技能做成之后应该看到的状态：pick(obj) → obj 在夹爪里；place(obj, t) → obj 在 t。"""
    if step[0] == "pick":
        return state.get(step[1]) == "gripper"
    if step[0] == "place":
        return state.get(step[1]) == step[2]
    raise ValueError(f"unknown skill: {step[0]}")


def _do(sim: TabletopSim, step: tuple) -> None:
    getattr(sim, step[0])(*step[1:])


def run_open_loop(sim: TabletopSim, plan: list[tuple], goal: dict[str, str]) -> Report:
    """开环：一次生成完整动作序列，中途不看。它总是“认为”自己完成了。"""
    for step in plan:
        _do(sim, step)
    truth = all(sim.where.get(o) == t for o, t in goal.items())   # 事实由环境决定，而不是由策略汇报
    return Report(success=truth, claimed=True, calls=len(sim.calls))


def run_closed_loop(sim: TabletopSim, plan: list[tuple], goal: dict[str, str], max_retries: int = 2) -> Report:
    """逐步检查：每个技能之后 observe 一次，检查 postcondition。

    - 没做成：只重试当前技能（recoveries += 1，log 记 f"retry {step[0]}({step[1]})"），每个技能最多重试 max_retries 次；
    - 重试用完仍失败：停下（log 记 f"stop at {step[0]}({step[1]})"），返回 success=False、claimed=False；
    - 全部做完后再 observe 一次，用新观察确认 goal（每个物体都在目标位置）：claimed 和 success 都取这个确认结果。
    calls 取 len(sim.calls)。
    """
    # >>> EXERCISE 6.3c 每一步都看一眼：只重试当前技能
    # HINT: 外层 for 遍历 plan，内层 for attempt in range(max_retries + 1)；成功就 break，for-else 处理重试用完。
    recoveries, log = 0, []
    for step in plan:
        for attempt in range(max_retries + 1):
            if attempt:
                recoveries += 1
                log.append(f"retry {step[0]}({step[1]})")
            _do(sim, step)
            if postcondition(step, sim.observe()):
                break
        else:
            log.append(f"stop at {step[0]}({step[1]})")
            return Report(success=False, claimed=False, calls=len(sim.calls), recoveries=recoveries, log=log)
    final = sim.observe()
    ok = all(final.get(o) == t for o, t in goal.items())
    return Report(success=ok, claimed=ok, calls=len(sim.calls), recoveries=recoveries, log=log)
    # <<< EXERCISE


TIDY_PLAN = [("pick", "red_cup"), ("place", "red_cup", "tray"), ("pick", "yellow_paper"), ("place", "yellow_paper", "bin")]
TIDY_GOAL = {"red_cup": "tray", "yellow_paper": "bin"}
