"""默认测试练习版 mini_agent/；设置 MINI_AGENT_TARGET=solutions 时测试参考答案。"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
target = ROOT / "solutions" if os.environ.get("MINI_AGENT_TARGET") == "solutions" else ROOT
sys.path.insert(0, str(target))
