import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex_safety.parser import Parser
from regex_safety.nfa import build, search as my_search, findall as my_findall


def test_search():
    test_cases = [
        (r"(\d+)-(\w+)", "abc 123-xyz 456-abc"),
        (r"([a-z]+)@([a-z]+)\.com", "mail: test@example.com or admin@test.com"),
        (r"a+", "baaab"),
    ]

    print("开始对拍 search():")
    for pat, text in test_cases:
        # Python re
        std_m = re.search(pat, text)
        std_res = std_m.groups() if std_m else None

        # 你的引擎
        ast = Parser(pat).parse()
        nfa = build(ast)
        my_m = my_search(nfa, text)
        my_res = my_m.groups() if my_m else None

        assert std_res == my_res, f"Search mismatched for {pat} on {text}: {std_res} != {my_res}"
        print(f"  [OK] {pat} on {text!r} -> {std_res}")


def test_findall():
    test_cases = [
        (r"\d+", "a1b22c333"),
        (r"([a-z]+)(\d+)", "a1 bb22 ccc333"),
        (r"a+", "baaab"),
    ]

    print("\n开始对拍 findall():")
    for pat, text in test_cases:
        # Python re
        std_res = re.findall(pat, text)

        # 你的引擎
        ast = Parser(pat).parse()
        nfa = build(ast)
        my_res = my_findall(nfa, text)

        assert std_res == my_res, f"Findall mismatched for {pat} on {text}: {std_res} != {my_res}"
        print(f"  [OK] {pat} on {text!r} -> {std_res}")


if __name__ == "__main__":
    test_search()
    test_findall()
    print("\n太强了！全部对拍通过！")