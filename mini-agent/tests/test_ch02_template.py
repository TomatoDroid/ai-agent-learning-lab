"""检查点 2.1：Chat Template。运行：pytest tests/test_ch02_template.py"""
from mini_agent import messages as M
from mini_agent.chat_template import last_query_index, render
from mini_agent.messages import ToolCall

WEATHER = {"type": "function", "function": {"name": "get_weather", "description": "查天气", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}


def test_单轮对话():
    out = render([M.system("你是助手"), M.user("你好")])
    assert out == "<|im_start|>system\n你是助手<|im_end|>\n<|im_start|>user\n你好<|im_end|>\n<|im_start|>assistant\n"


def test_工具定义写进system():
    out = render([M.system("你是助手"), M.user("温哥华天气")], tools=[WEATHER], add_generation_prompt=False)
    assert out.startswith('<|im_start|>system\n你是助手\n\n<tools>\n{"name": "get_weather", "description": "查天气"')
    assert "</tools><|im_end|>\n<|im_start|>user\n温哥华天气<|im_end|>\n" in out


def test_没有system时为工具新建一条():
    out = render([M.user("hi")], tools=[WEATHER], add_generation_prompt=False)
    assert out.startswith("<|im_start|>system\n<tools>\n")


def test_工具调用与工具结果():
    msgs = [
        M.system("s"), M.user("温哥华天气"),
        M.assistant(None, [ToolCall("c1", "get_weather", {"city": "温哥华"})], reasoning="需要查天气"),
        M.tool_result("c1", "13.2°C 晴"),
    ]
    out = render(msgs)
    assert ('<|im_start|>assistant\n<think>\n需要查天气\n</think>\n\n\n<tool_call>\n'
            '{"name": "get_weather", "arguments": {"city": "温哥华"}}\n</tool_call><|im_end|>\n') in out
    assert "<|im_start|>user\n<tool_response>\n13.2°C 晴\n</tool_response><|im_end|>\n" in out
    assert out.endswith("<|im_start|>assistant\n")


def test_连续工具结果合并进一个块():
    msgs = [M.user("q"), M.assistant(None, [ToolCall("a", "t", {}), ToolCall("b", "t", {})]),
            M.tool_result("a", "1"), M.tool_result("b", "2")]
    out = render(msgs, add_generation_prompt=False)
    assert out.endswith("<|im_start|>user\n<tool_response>\n1\n</tool_response>\n<tool_response>\n2\n</tool_response><|im_end|>\n")


def test_只保留最后一次真实提问之后的思考():
    msgs = [
        M.user("第一个问题"), M.assistant("答一", reasoning="旧思考"),
        M.user("第二个问题"), M.assistant(None, [ToolCall("c", "t", {})], reasoning="新思考"), M.tool_result("c", "r"),
    ]
    assert last_query_index(msgs) == 2
    out = render(msgs)
    assert "旧思考" not in out
    assert "新思考" in out


def test_陷阱_把工具结果伪装成user消息会丢掉思考():
    right = [M.user("温哥华天气"), M.assistant(None, [ToolCall("c", "get_weather", {})], reasoning="需要查天气"), M.tool_result("c", "13.2°C")]
    wrong = right[:2] + [M.user("工具结果：13.2°C")]
    assert "需要查天气" in render(right)
    assert "需要查天气" not in render(wrong), "模板把它当成了新问题，于是清掉了之前的思考"
