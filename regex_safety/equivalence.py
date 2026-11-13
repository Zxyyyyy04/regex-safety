# 等价性验证。
# 升级：从纯随机样本对拍，升级为基于 DFA 的严格同构证明。

import random
from .parser import Parser
from .nfa import build, fullmatch, _match_at
from .dfa import build_dfa


def sample_equivalent(pat_a, pat_b, n=2000, max_len=12, seed=42):
    """
    样本对拍：速度快，但不严格。作为 DFA 同构的保底。
    """
    nfa_a = build(Parser(pat_a).parse())
    nfa_b = build(Parser(pat_b).parse())
    rng = random.Random(seed)
    alphabet = 'ab01'
    for _ in range(n):
        L = rng.randint(0, max_len)
        s = ''.join(rng.choice(alphabet) for _ in range(L))
        if fullmatch(nfa_a, s) != fullmatch(nfa_b, s):
            return False, s
    return True, None


def dfa_isomorphic(pat_a, pat_b):
    """
    基于 DFA 图同构的严格等价验证。
    把两个正则转成 DFA，同时 BFS 遍历，看它们的状态转移是否完全一致。
    如果完全一致，返回 (True, None)；如果发现差异，返回 (False, 反例字符串)。
    """
    try:
        nfa_a = build(Parser(pat_a).parse())
        nfa_b = build(Parser(pat_b).parse())
        dfa_a = build_dfa(nfa_a)
        dfa_b = build_dfa(nfa_b)
    except Exception:
        return None, "DFA 构建失败（可能状态爆炸）"

    # 队列里存的是 (dfa_a的状态, dfa_b的状态, 到达这里的路径字符串)
    queue = [(dfa_a.start, dfa_b.start, "")]
    visited = set()
    visited.add((dfa_a.start, dfa_b.start))

    while queue:
        s_a, s_b, path = queue.pop(0)

        # 如果一个是接受状态，另一个不是，说明不等价
        if (s_a in dfa_a.accepts) != (s_b in dfa_b.accepts):
            return False, path

        # 收集两个 DFA 所有的出边字符（包括 '*'）
        chars = set(dfa_a.trans.get(s_a, {}).keys())
        chars.update(dfa_b.trans.get(s_b, {}).keys())

        for ch in chars:
            next_a = dfa_a.trans.get(s_a, {}).get(ch)
            next_b = dfa_b.trans.get(s_b, {}).get(ch)

            # 如果某个分支只有一边存在，说明不等价
            if (next_a is None) != (next_b is None):
                return False, path + (ch if ch != '*' else 'X')

            # 如果两边都有转移，且没被访问过，入队
            if next_a is not None and next_b is not None:
                if (next_a, next_b) not in visited:
                    visited.add((next_a, next_b))
                    queue.append((next_a, next_b, path + (ch if ch != '*' else 'X')))

    # 遍历完所有状态没有差异，严格同构
    return True, None