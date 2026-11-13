import re
import time

# 从你的包导入
from regex_safety.parser import Parser
from regex_safety.nfa import build, fullmatch
from regex_safety.rewrite import rewrite, to_string


def run_bench():
    # 恶意正则，故意构造回溯爆炸
    bad_pattern = r"(a+)+b"
    # 构造 25 个 a，最后放个非 b 字符
    bad_text = "a" * 25 + "!"

    print(f"测试正则: {bad_pattern}")
    print(f"测试文本: 长度 {len(bad_text)} (25个a + '!')")
    print("-" * 40)

    # 1. 测试 Python 自带的 re (C语言写的回溯引擎)
    print("[1] 跑 Python 自带的 re (可能卡住)...")
    start = time.perf_counter()
    re.search(bad_pattern, bad_text)
    re_time = time.perf_counter() - start
    print(f"耗时: {re_time:.4f} 秒")

    # 2. 测试你的 NFA 引擎
    print("\n[2] 跑你自己写的 NFA 引擎...")
    nfa = build(Parser(bad_pattern).parse())
    start = time.perf_counter()
    fullmatch(nfa, bad_text)
    my_time = time.perf_counter() - start
    print(f"耗时: {my_time:.8f} 秒")

    # 3. 跑改写后的正则
    print("\n[3] 跑改写后的正则 (利用你的 re 引擎)...")
    ast = Parser(bad_pattern).parse()

    # 注意这里：把 _ 换成 changed，看看改写到底有没有生效
    new_ast, changed = rewrite(ast)
    safe_pattern = to_string(new_ast)

    print(f"改写后正则: {safe_pattern} (是否发生改写: {changed})")

    start = time.perf_counter()
    re.search(safe_pattern, bad_text)
    safe_time = time.perf_counter() - start
    print(f"耗时: {safe_time:.8f} 秒")

    print("-" * 40)
    if my_time > 0:
        print(f"你的 NFA 引擎比 re 快了 {re_time / my_time:,.0f} 倍！")
    else:
        print("你的 NFA 引擎太快了，快到测不出时间！")


if __name__ == "__main__":
    run_bench()