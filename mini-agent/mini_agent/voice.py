"""语音交互：流式分段、首音延迟、快慢思考（练习 6.2）。

对应原书第六章“语音交互：从级联到全双工”。真实语音需要麦克风、ASR、TTS 和网络，这里不碰音频，
只把决定体验的三件事变成可以确定性测试的纯逻辑：

- 什么时候把文字交给 TTS（LLM 分段输出：第一段能念就先念）；
- 一次回答的首音延迟由哪些等待串起来（串行 / 流式感知 / 推测执行）；
- 前台快模型和后台慢模型怎么分工（方案一“各说各的” vs 方案二“慢模型提醒，快模型表达”）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from . import messages as M
from .messages import tool_calls_of

SENTENCE_END = "。！？!?；;\n"
SOFT_BREAK = "，,、"


def split_for_tts(chunks: Iterable[str], min_chars: int = 6) -> Iterator[str]:
    """把 LLM 流式吐出的文字块切成适合播报的片段，切出一段就立刻交给 TTS。

    - 缓冲区里出现句末标点（SENTENCE_END），且截到这个标点的片段去掉首尾空白后至少 min_chars 个字，就产出这一段；
    - 第一段可以更早：遇到逗号类停顿（SOFT_BREAK）也可以切，越早开口越好；之后的段只在句末切；
    - 太短的片段（如“嗯。”）不单独切，和后面的内容合在一起；
    - 流结束时，把剩下的非空内容（去掉首尾空白）作为最后一段产出。
    """
    # TODO 练习 6.2a：流式分段：第一段能念就先念
    # 提示：维护一个 buf 和 first 标志。每来一个块，就在 buf 里从前往后找可切点；切下的部分 strip 后够长才产出。
    raise NotImplementedError("练习 6.2a 还没有完成：流式分段：第一段能念就先念")


_TAG = re.compile(r"\[([A-Z]+)(?::([^\]]*))?\]")


def parse_control_tags(text: str) -> list[dict]:
    """原书“更像人的语音合成”：主 LLM 在文字之外输出控制标记，TTS 执行层把它们变成停顿、情绪和语速。

    返回动作列表：{"pause": True} 或 {"say": 文本, "emotion": ..., "speed": ...}。
    [THINKING] → 一次停顿；[EMO:x] 和 [SPEED:0.8x] 改变之后所有片段的状态，直到再次改变；
    不认识的标记直接丢弃——无论如何，标记都不能被念出来。
    """
    actions: list[dict] = []
    emotion, speed, pos = "neutral", 1.0, 0

    def say(s: str) -> None:
        if s.strip():
            actions.append({"say": s.strip(), "emotion": emotion, "speed": speed})

    for m in _TAG.finditer(text):
        say(text[pos:m.start()])
        name, arg = m.group(1), (m.group(2) or "").strip()
        if name == "THINKING":
            actions.append({"pause": True})
        elif name == "EMO" and arg:
            emotion = arg
        elif name == "SPEED" and arg:
            try:
                speed = float(arg.rstrip("xX"))
            except ValueError:
                pass
        pos = m.end()
    say(text[pos:])
    return actions


@dataclass
class Turn:
    """一轮语音对话的时间参数（毫秒）。默认值取原书图 6-7 空载理想情况的下限。

    end_ms：用户停止说话的时刻；partials：说话过程中流式 ASR 给出的临时转录 [(时刻, 文本)]；final：最终文本。
    asr_full_ms：说完后整段识别；asr_final_ms：流式 ASR 已在边听边转，说完后只需确认最终文本。
    llm_ttft_ms / llm_gen_ms：首 token 延迟 / 生成完整回复；llm_seg_ms：首 token 后生成出第一段可播报文本的时间。
    """
    end_ms: int = 0
    vad_silence_ms: int = 500
    asr_full_ms: int = 50
    asr_final_ms: int = 20
    llm_ttft_ms: int = 100
    llm_gen_ms: int = 100
    llm_seg_ms: int = 30
    tts_first_ms: int = 200
    partials: list[tuple[int, str]] = field(default_factory=list)
    final: str = ""


def first_audio_ms(turn: Turn, mode: str) -> tuple[int, int]:
    """用户开始听到回答的时刻，以及这一轮调用 LLM 的次数。返回 (毫秒, 调用次数)。

    - "serial"：等静音 → 整段 ASR → 等 LLM 生成完整回复（ttft + gen）→ TTS 首包。1 次调用。
    - "streaming"：等静音 → 确认最终文本（asr_final）→ LLM 首段（ttft + seg）→ TTS 首包。1 次调用。
    - "speculative"：每当临时转录变化，就取消上一次推测、用新文本调用 LLM。
      调用次数 = 相邻去重后的临时转录条数，最后一条与 final 不同时还要再调 1 次。
      若最后一条临时转录（时刻 tp）与 final 相同：LLM 首段在 tp + ttft + seg 就绪，但必须等最终文本确认
      （end + 静音 + asr_final），首音 = 两者较晚者 + TTS 首包；否则推测作废，延迟与 streaming 相同。
      没有临时转录时等同 streaming。
    """
    # TODO 练习 6.2b：首音延迟：串行、流式、推测执行
    # 提示：先算出 confirmed = end + 静音 + asr_final，三种模式都围绕它（或 serial 的整段 ASR）展开。
    raise NotImplementedError("练习 6.2b 还没有完成：首音延迟：串行、流式、推测执行")


THINK_DEEPLY = {
    "type": "function",
    "function": {
        "name": "think_deeply",
        "description": "把需要推理、计算或查资料的问题交给后台慢模型。调用时先对用户说一句自然的过渡语，结果会作为建议返回。",
        "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]},
    },
}


class FastSlowVoice:
    """前台快模型维持对话，后台慢模型深度思考（原书“认知时序”）。

    scheme="respond"（方案一 快思考回应，慢思考回答）：两个模型各自独立回答，两段话都念给用户。
    scheme="advise"（方案二 快思考交互，慢思考提醒）：只有快模型对用户说话；它可以调用 think_deeply，
    慢模型的结论以 "[后台建议] ..." 的工具结果送回，由快模型决定怎么说。
    ask() 返回这一轮念给用户的话 [(说话者, 文本)]；slow_calls 统计慢模型被调用的次数。
    """

    def __init__(self, fast, slow, scheme: str = "advise",
                 fast_prompt: str = "你是语音助手。回答要短、口语化。", slow_prompt: str = "你是后台推理模型。给出准确、简洁的结论。"):
        self.fast, self.slow, self.scheme = fast, slow, scheme
        self.history: list[dict] = [M.system(fast_prompt)]
        self.slow_prompt = slow_prompt
        self.slow_calls = 0

    def _think_slow(self, question: str) -> str:
        self.slow_calls += 1
        return self.slow.complete([M.system(self.slow_prompt), M.user(question)]).content or ""

    def ask(self, question: str) -> list[tuple[str, str]]:
        self.history.append(M.user(question))
        if self.scheme == "respond":
            quick = self.fast.complete(self.history).content or ""
            deep = self._think_slow(question)
            self.history.append(M.assistant(f"{quick}\n{deep}"))
            return [("fast", quick), ("slow", deep)]
        return self._advise()

    def _advise(self) -> list[tuple[str, str]]:
        """方案二：快模型带着 think_deeply 工具回答。

        - 回复里没有工具调用：直接念出 content（简单问题慢模型完全不参与）；
        - 有 think_deeply 调用：先把 content（过渡语，如“我算一下”）念出来（为空就不念），
          把这条 assistant 消息记入历史，对每个调用请慢模型思考 arguments["question"]，
          以 M.tool_result(id, "[后台建议] " + 结论) 送回，再让快模型继续，直到它不再调用工具。
        每次调用快模型都传 tools=[THINK_DEEPLY]；最终回复也要记入 history。
        """
        # TODO 练习 6.2c：方案二：慢思考提醒，快思考表达
        # 提示：用 while 循环；M.assistant(content, reply.tool_calls) 记入历史，与 1.1 课的 Agent 循环几乎一样。
        raise NotImplementedError("练习 6.2c 还没有完成：方案二：慢思考提醒，快思考表达")
