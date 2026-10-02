"""
安全符号表达式引擎（白名单 AST），多个因子/进化方法共用。

- 字段（前缀 $）：$open $high $low $close $volume $ret
- 算子：复用 project/src/dsl/operators.py 中的密封算子（经因果性验证）
- 不执行任意代码；仅允许白名单算子与字段
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd

# 引入密封算子
_PROJ_SRC = Path(__file__).resolve().parents[2] / "project" / "src"
sys.path.insert(0, str(_PROJ_SRC))
from dsl.operators import OPERATORS  # noqa: E402

FIELDS = ["open", "high", "low", "close", "volume", "ret"]


class ExprError(ValueError):
    pass


def _eval_node(node, panel: pd.DataFrame) -> pd.Series:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, panel)

    if isinstance(node, ast.Name):
        # $ 字段在解析时去掉了 $，用 Name 表示
        if node.id in FIELDS:
            return panel[node.id]
        raise ExprError(f"未知字段: {node.id}")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        return float(node.value)

    if isinstance(node, ast.UnaryOp):
        v = _eval_node(node.operand, panel)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
        raise ExprError("不支持的一元运算")

    if isinstance(node, ast.BinOp):
        a = _eval_node(node.left, panel)
        b = _eval_node(node.right, panel)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            bv = b.replace(0, np.nan) if isinstance(b, pd.Series) else b
            return a / bv
        raise ExprError("不支持的二元运算")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in OPERATORS:
            raise ExprError("仅允许白名单算子")
        fname = node.func.id
        args = [_eval_node(a, panel) for a in node.args]
        return OPERATORS[fname](*args)

    raise ExprError(f"不支持的语法节点: {type(node).__name__}")


def _preprocess(text: str) -> str:
    # $close -> close（字段名）
    out = text
    for f in FIELDS:
        out = out.replace("$" + f, f)
    return out


def validate_expression(text: str) -> None:
    """仅校验语法与白名单，不求值。"""
    tree = ast.parse(_preprocess(text), mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            raise ExprError("禁止属性访问")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in OPERATORS:
                raise ExprError(f"非白名单算子: {node.func.id}")
        if isinstance(node, ast.Name) and node.id not in FIELDS and node.id not in OPERATORS:
            raise ExprError(f"非白名单字段: {node.id}")


def eval_expression(text: str, panel: pd.DataFrame) -> pd.Series:
    """在给定面板上求值，返回 MultiIndex Series。"""
    validate_expression(text)
    tree = ast.parse(_preprocess(text), mode="eval")
    result = _eval_node(tree, panel)
    if isinstance(result, float):
        raise ExprError("表达式必须产生一个信号，而不是常数")
    return result.replace([np.inf, -np.inf], np.nan)
