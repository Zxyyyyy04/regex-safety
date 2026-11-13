from regex_safety.parser import Parser
from regex_safety.nfa import build
from regex_safety.dfa import build_dfa, is_match_dfa


def run():
    patterns = [
        "a+",
        "(a|b)*",
        "(a|b)*a(a|b){5}",
        "(a|b)*a(a|b){10}",
    ]

    for pat in patterns:
        nfa = build(Parser(pat).parse())
        dfa = build_dfa(nfa)
        print(f"正则: {pat:20} -> NFA 状态数: {nfa._next:3} | DFA 状态数: {dfa.state_count}")

        # 简单验证一下布尔匹配
        print(f"  'ababa' 匹配结果: {is_match_dfa(dfa, 'ababa')}")


if __name__ == "__main__":
    run()