# 命令行入口。输出故意不搞花哨，就一行一行打。

import sys
import os
import json

# 这段代码是为了兼容在 IDE 里直接点运行 cli.py
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from regex_safety.parser import Parser, ParseError
    from regex_safety.risk import analyze, dangerous_nodes
    from regex_safety.rewrite import rewrite, to_string
    from regex_safety.equivalence import sample_equivalent, dfa_isomorphic
    from regex_safety.nfa import build
    from regex_safety.dfa import build_dfa, DFAStateExplosion
else:
    # 正常的包导入
    from .parser import Parser, ParseError
    from .risk import analyze, dangerous_nodes
    from .rewrite import rewrite, to_string
    from .equivalence import sample_equivalent, dfa_isomorphic
    from .nfa import build
    from .dfa import build_dfa, DFAStateExplosion


def check(pattern):
    try:
        ast = Parser(pattern).parse()
    except ParseError as e:
        return {"pattern": pattern, "error": str(e)}

    level = analyze(ast)
    nodes = dangerous_nodes(ast)

    # 构建 NFA
    nfa = build(ast)

    # 尝试构建 DFA 并统计状态数
    try:
        # 核心升级：传入 max_states=5000 阈值
        dfa = build_dfa(nfa, max_states=5000)
        dfa_states = dfa.state_count
    except DFAStateExplosion:
        # 捕获我们自定义的爆炸异常
        dfa_states = "状态爆炸 (主动拦截)"
    except Exception:
        # 捕获其他未知的构建异常
        dfa_states = "构建失败 (未知错误)"

    new_ast, changed = rewrite(ast)
    new_pat = to_string(new_ast) if changed else pattern

    result = {
        "pattern": pattern,
        "risk": level,
        "nfa_states": nfa._next,
        "dfa_states": dfa_states,
        "danger_nodes": nodes,
        "rewrite": new_pat if changed else None,
    }

    if changed:
        # 优先尝试基于 DFA 的严格同构证明
        ok, counter = dfa_isomorphic(pattern, new_pat)
        method = "dfa_isomorphism"

        # 如果 DFA 因为状态爆炸等原因无法构建，退回样本对拍
        if ok is None:
            ok, counter = sample_equivalent(pattern, new_pat)
            method = "sample_fallback"

        result["equivalence"] = {
            "method": method,
            "ok": ok,
            "counterexample": counter,
        }
    return result


def main(argv):
    if len(argv) < 2:
        print("未提供参数，默认测试: (a+)+b")
        pattern = "(a+)+b"
    else:
        pattern = argv[1]

    print(json.dumps(check(pattern), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))