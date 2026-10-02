"""QuantaAlpha 因子 DSL 解析器离线测试（不依赖 LLM/Docker/qlib）。
直接调用仓库内 quantaalpha/factors/coder/expr_parser.py 的 parse_expression。"""
import sys
sys.path.insert(0, ".")
from expr_parser import parse_expression

cases = [
    # 1 算术
    ("$close + $open", "ADD"),
    ("$close - $open", "SUBTRACT"),
    ("$close * $volume", "MULTIPLY"),
    ("$close / $open", "DIVIDE"),
    # 2 比较
    ("$close > $open", "GT"),
    ("$close < $open", "LT"),
    ("$close >= $open", "GE"),
    ("$close == $open", "EQ"),
    # 3 条件
    ("$close > $open ? $close : $open", "WHERE"),
    # 4 一元负号（数字与变量相乘时，解析器保留算术形式 -1*$close，是设计行为）
    ("-1 * $close", "-1*$close"),
    # 5 函数嵌套
    ("RANK(DELTA($close, 5))", "RANK"),
    ("TS_RANK($close, 20)", "TS_RANK"),
    # 6 论文 test.py 中的真实表达式
    ("ZSCORE( (TS_STD($return,20) < TS_QUANTILE(TS_STD($return,20),60,0.3)) ? (1.5/(TS_STD($return,20)+1e-8)) : (1/(TS_STD($return,20)+1e-8)) )", "ZSCORE"),
]

passed = 0
failed = 0
for expr, expect in cases:
    try:
        out = parse_expression(expr)
        ok = expect in out
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else:
            failed += 1
            print(f"[{status}] expect token {expect} not found")
            print(f"       expr: {expr}")
            print(f"       out : {out}")
    except Exception as e:
        failed += 1
        print(f"[ERROR] {expr}")
        print(f"        {type(e).__name__}: {e}")

print(f"\n{passed}/{len(cases)} passed, {failed} failed")
sys.exit(1 if failed else 0)
