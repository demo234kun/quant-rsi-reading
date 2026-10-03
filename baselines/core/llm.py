"""
可插拔 LLM 后端。

- OpenAICompatibleLLM：有 API key 时调用真实 LLM
- RuleBasedLLM：无 key 时，用基于 AST 的规则变异替代 LLM（表达式进化照样可跑），
  此时方法 fidelity 标注为 llm_replaced_by_rule，明确不是论文原始 LLM
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
import random
import time
from pathlib import Path
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


# ============================================================================
# 文本生成后端（供 08/09/10/11 等「LLM 改写自然语言策略 / 生成程序」的方法使用）
#
# 设计约束：
#   1. 真实 LLM：无 key 时不可用，方法必须显式降级并改 fidelity 标注，不假装。
#   2. 磁盘缓存：同一输入只付一次代价，重跑结果稳定（key = 全部入参的 sha256）。
#   3. 零 test 期调用：LLM 只在 fit 阶段产出「产物」，produce_signal 只做确定性解释。
# ============================================================================

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "llm"


class LLMUnavailable(RuntimeError):
    """真实 LLM 不可用（无凭据 / 调用失败）。调用方须降级并标注 fidelity。"""


def _resolve_endpoint() -> Optional[tuple]:
    """返回 (base_url, api_key, model)；按环境变量优先级解析。"""
    # 优先使用显式配置的三元组（base_url + key + model 必须成套）
    llm_key = os.environ.get("LLM_API_KEY")
    llm_base = os.environ.get("LLM_BASE_URL")
    llm_model = os.environ.get("LLM_MODEL")
    if llm_key and llm_base and llm_model:
        return llm_base.rstrip("/"), llm_key, llm_model
    # 其次退回 OpenAI 兼容端点
    oa_key = os.environ.get("OPENAI_API_KEY")
    if oa_key:
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        return base, oa_key, os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return None


class TextLLM:
    """真实 LLM 文本生成 + 磁盘缓存 + 显式降级。

    用法::

        llm = TextLLM(tag="evolve_trade")
        if llm.available:
            policy = llm.complete(system, user)
        else:
            ...  # 走确定性降级路径，并把 fidelity 改成 *_replaced_by_rule
    """

    def __init__(
        self,
        tag: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 1600,
        cache: bool = True,
        timeout: int = 90,
        max_retries: int = 3,
    ):
        self.tag = tag
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.cache_enabled = cache
        self.timeout = timeout
        self.max_retries = max_retries
        self.stats = {"cache_hit": 0, "api_call": 0, "error": 0}
        ep = _resolve_endpoint()
        self.base_url, self.api_key, self.model = ep if ep else (None, None, None)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @property
    def backend_name(self) -> str:
        return f"{self.model}@{self.base_url}" if self.available else "none"

    def _cache_path(self, system: str, user: str, temperature: float, max_tokens: int) -> Path:
        blob = json.dumps(
            {"tag": self.tag, "model": self.model, "system": system,
             "user": user, "temperature": temperature, "max_tokens": max_tokens},
            ensure_ascii=False, sort_keys=True,
        )
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]
        d = CACHE_DIR / self.tag
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{h}.json"

    def _post(self, system: str, user: str, temperature: float, max_tokens: int) -> str:
        import urllib.request
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()

    def complete(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        purpose: str = "",
    ) -> str:
        """生成文本。不可用或最终失败时抛 LLMUnavailable（不返回静默兜底文本）。"""
        if not self.available:
            raise LLMUnavailable(
                f"[{self.tag}] 无 LLM 凭据（需 LLM_API_KEY+LLM_BASE_URL+LLM_MODEL "
                f"或 OPENAI_API_KEY）"
            )
        temp = self.temperature if temperature is None else temperature
        mt = self.max_tokens if max_tokens is None else max_tokens

        cpath = self._cache_path(system, user, temp, mt) if self.cache_enabled else None
        if cpath is not None and cpath.exists():
            try:
                self.stats["cache_hit"] += 1
                return json.loads(cpath.read_text(encoding="utf-8"))["text"]
            except Exception:
                pass  # 缓存损坏则忽略，重新调用

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                text = self._post(system, user, temp, mt)
                self.stats["api_call"] += 1
                if cpath is not None:
                    try:
                        cpath.write_text(
                            json.dumps({"text": text, "purpose": purpose,
                                        "model": self.model}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
                    except Exception:
                        pass
                return text
            except Exception as e:  # 网络/限流/格式
                last_err = e
                if attempt < self.max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
        self.stats["error"] += 1
        raise LLMUnavailable(f"[{self.tag}] LLM 调用失败（purpose={purpose}）: {last_err}")


def get_text_llm(tag: str = "default", **kwargs) -> TextLLM:
    """工厂：始终返回真实后端对象；是否可用由 `.available` 决定。"""
    return TextLLM(tag=tag, **kwargs)
