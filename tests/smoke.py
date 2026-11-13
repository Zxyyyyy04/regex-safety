# 不是正经测试，就是手动跑一遍看有没有炸。
# 正经测试用 pytest 写，TODO。

from regex_safety.parser import Parser
from regex_safety.nfa import build, fullmatch
from regex_safety.risk import analyze
from regex_safety.rewrite import rewrite, to_string
from regex_safety.equivalence import sample_equivalent


def run():
    cases = [
        ("a+", ["a", "aaa", ""], [True, True, False]),
        ("(a+)+b", ["ab", "aaab", "aaa"], [True, True, False]),
        ("[0-9]{2,3}", ["12", "123", "1", "1234"], [True, True, False, False]),
        ("a|b", ["a", "b", "c"], [True, True, False]),
    ]
    for pat, texts, expects in cases:
        nfa = build(Parser(pat).parse())
        for t, e in zip(texts, expects):
            got = fullmatch(nfa, t)
            print(f"{pat!r} on {t!r}: {got} (expect {e})")
            assert got == e, (pat, t)

    for p in ["a+", "(a+)+b", "(a|aa)+"]:
        ast = Parser(p).parse()
        print(p, "->", analyze(ast))

    ast = Parser("(a+)+").parse()
    new_ast, changed = rewrite(ast)
    print("rewrite:", to_string(ast), "->", to_string(new_ast), changed)
    ok, cex = sample_equivalent("(a+)+", to_string(new_ast))
    print("equiv:", ok, cex)


if __name__ == "__main__":
    run()