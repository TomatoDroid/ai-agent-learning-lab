"""最小 MCP：把 ToolRegistry 暴露成 MCP 服务器，再审计接入的第三方服务器（练习 4.2a、4.2b）。

对应原书第四章“工具生态：MCP 与 Skill Hub”。MCP 用 JSON-RPC 2.0 通信：
  客户端 initialize → tools/list 拿到工具定义 → tools/call 调用工具。
这里只实现 tools 这一类原语（还有 resources 和 prompts），传输层用 stdio：每行一条 JSON。
做完后可以运行 `python -m mini_agent mcp`，把 mini-agent 的工具接进任何支持 MCP 的客户端。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Callable

from .injection import SUSPICIOUS
from .messages import ToolCall
from .tools import Tool, ToolRegistry, UnknownToolError

PROTOCOL_VERSION = "2025-06-18"
METHOD_NOT_FOUND, INVALID_PARAMS, PARSE_ERROR = -32601, -32602, -32700

# 工具描述投毒的常见话术（原书：把 description 当作不可信输入来审计）
POISON = SUSPICIOUS + [
    r"\bssh\b", r"private key|私钥", r"\.env\b|api[_ ]?key|password|密码|凭证",
    r"before (calling|using) (this|any)", r"(do not|don't) (tell|inform|mention)",
    r"instead of (the )?\w+ tool", r"(不要|别)告诉用户",
]


class McpServer:
    def __init__(self, registry: ToolRegistry, name: str = "mini-agent", version: str = "0.4"):
        self.registry = registry
        self.info = {"name": name, "version": version}

    def handle(self, msg: dict) -> dict | None:
        """处理一条 JSON-RPC 消息，返回响应；通知（没有 "id" 字段）返回 None。

        - "initialize" → {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": self.info}
        - "ping" → {}
        - "tools/list" → {"tools": [{"name", "description", "inputSchema"}, …]}，只列 registry.schemas() 里的工具
        - "tools/call"，params = {"name", "arguments"}：
            * 工具不存在（含未加载的）→ 错误 INVALID_PARAMS，message 为 "Unknown tool: {name}"
            * 执行抛异常 → 正常结果，但 isError 为 True：
              {"content": [{"type": "text", "text": "{异常类型名}: {异常}"}], "isError": True}
              （工具失败是给模型看的观察，不是协议错误）
            * 成功 → {"content": [{"type": "text", "text": 输出}], "isError": False}
        - 其他方法 → 错误 METHOD_NOT_FOUND，message 为 "Method not found: {method}"
        成功响应：{"jsonrpc": "2.0", "id": id, "result": …}
        错误响应：{"jsonrpc": "2.0", "id": id, "error": {"code": …, "message": …}}
        """
        # TODO 练习 4.2a：MCP 服务器
        # 提示：先判断 "id" not in msg → return None。method = msg.get("method")，params = msg.get("params") or {}。
        # 提示：tools/list 从 self.registry.schemas() 里取 s["function"] 的三个字段，parameters 改名为 inputSchema。
        # 提示：tools/call 先 self.registry.get(name) 确认存在（捕获 UnknownToolError），
        # 提示：再 self.registry.execute(ToolCall("mcp", name, arguments))。
        raise NotImplementedError("练习 4.2a 还没有完成：MCP 服务器")


def serve_stdio(server: McpServer, stdin=None, stdout=None) -> None:
    """stdio 传输：每行读一条 JSON-RPC 消息，每条响应写一行。"""
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    for line in stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": PARSE_ERROR, "message": str(exc)}}
        else:
            resp = server.handle(msg)
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()


def remote_tools(send: Callable[[dict], dict], registry: ToolRegistry, prefix: str = "") -> list[str]:
    """客户端一侧：通过 send（发一条请求、收一条响应）列出远端工具，注册成本地工具。

    prefix 用来给不同服务器的工具加命名空间（如 "github__"），避免同名工具互相遮蔽。返回注册的工具名。
    """
    send({"jsonrpc": "2.0", "id": 0, "method": "initialize",
          "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "mini-agent", "version": "0.4"}}})
    listed = send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    names = []
    for t in listed:
        def fn(_name=t["name"], **arguments):
            resp = send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": _name, "arguments": arguments}})
            if "error" in resp:
                raise RuntimeError(resp["error"]["message"])
            text = "\n".join(c.get("text", "") for c in resp["result"]["content"])
            if resp["result"].get("isError"):
                raise RuntimeError(text)
            return text
        registry.register(Tool(prefix + t["name"], t["description"], t["inputSchema"], fn, risk="medium", untrusted_output=True))
        names.append(prefix + t["name"])
    return names


def fingerprint(tool: dict) -> str:
    """一条 MCP 工具定义的指纹：规范化 JSON 的 SHA-256 前 12 位。描述或 schema 改一个字，指纹就变。"""
    return hashlib.sha256(json.dumps(tool, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def audit_servers(servers: dict[str, list[dict]], pinned: dict[str, str]) -> list[str]:
    """接入前审计第三方 MCP 服务器。servers：服务器名 → tools/list 返回的工具列表；
    pinned：“服务器名/工具名” → 上次审查通过时的指纹。

    返回发现的问题，顺序：服务器名升序，同一服务器内按工具列表顺序，每个工具依次检查：
    - "unpinned:{服务器}/{工具}"：从没审查过（不在 pinned 里）
    - "changed:{服务器}/{工具}"：审查过，但指纹变了（静默更新，可能是供应链攻击）
    - "poisoned:{服务器}/{工具}"：description 或任一参数的 description 命中 POISON 中的模式（不区分大小写）
    最后检查遮蔽：同一个工具名出现在多个服务器里，按工具名升序追加
    - "shadowed:{工具}({服务器1},{服务器2},…)"，服务器名升序、逗号分隔无空格
    """
    # TODO 练习 4.2b：第三方服务器审计
    # 提示：参数描述在 tool["inputSchema"].get("properties", {}) 的每一项的 "description" 里。
    # 提示：遮蔽：先建一个 工具名 → [服务器…] 的字典，再筛出长度大于 1 的。
    raise NotImplementedError("练习 4.2b 还没有完成：第三方服务器审计")
