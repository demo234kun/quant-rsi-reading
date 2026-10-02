"""
可插拔 LLM 后端。

- OpenAICompatibleLLM：有 API key 时调用真实 LLM
- RuleBasedLLM：无 key 时，用基于 AST 的规则变异替代 LLM（表达式进化照样可跑），
  此时方法 fidelity 标注为 llm_replaced_by_rule，明确不是论文原始 LLM
"""
from __future__ import annotations
import ast
import os
import random
from typing import List, Optional

import numpy as np

from .expr import FIELDS, OPERATORS, validate_expression

# 同参数族算子，便于替换
WINDOW_OPS = ["rolling_mean", "rolling_std", "rolling_max", "rolling_min", "rolling_rank"]
PRICE_FIELDS = ["open", "high", "low", "close", "volume", "ret"]
WINDOW_CHOICES = [3, 5, 10, 20, 30]


class RuleBasedLLM:
    """用 AST 重写做规则变异，不调用任何外部模型。"""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def mutate(self, expr: str, feedback: str = "") -> str:
        text = expr
        for f in FIELDS:
            text = text.replace("$" + f, f)
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError:
            return expr

        mode = self.rng.choice(["field", "window", "op", "wrap"])
        try:
            if mode == "field":
                names = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in FIELDS]
                if names:
                    n = self.rng.choice(names)
                    n.id = self.rng.choice([f for f in PRICE_FIELDS if f != n.id])
            elif mode == "window":
                consts = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                          and isinstance(n.value, int)]
                if consts:
                    n = self.rng.choice(consts)
                    n.value = self.rng.choice([w for w in WINDOW_CHOICES if w != n.value])
            elif mode == "op":
                calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Name) and n.func.id in WINDOW_OPS]
                if calls:
                    c = self.rng.choice(calls)
                    c.func.id = self.rng.choice([o for o in WINDOW_OPS if o != c.func.id])
            elif mode == "wrap":
                inner = ast.unparse(tree.body)
                wrapped = f"cs_rank({inner})"
                return wrapped
        except Exception:
            return expr

        candidate = ast.unparse(tree)
        try:
            validate_expression(candidate)
        except Exception:
            return expr
        return candidate


class OpenAICompatibleLLM:
    """真实 LLM 调用（OpenAI 兼容接口）。需要 OPENAI_API_KEY。"""

    def __init__(self, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        self.model = model
        self.base_url = base_url
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai 未安装")
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url=base_url)

    def mutate(self, expr: str, feedback: str = "") -> str:
        prompt = (
            "你是量化因子研究员。给定一个 Alpha 因子表达式和反馈，提出一个改进的新表达式。"
            f"仅输出表达式本身。\n当前表达式: {expr}\n反馈: {feedback}"
        )
        resp = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}], temperature=0.8
        )
        cand = resp.choices[0].message.content.strip().strip("`")
        return cand


def get_llm(model: str = "gpt-4o-mini", seed: Optional[int] = None):
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAICompatibleLLM(model=model)
    return RuleBasedLLM(seed=seed)
