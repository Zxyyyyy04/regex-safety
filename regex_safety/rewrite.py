# 只做最基本的几条改写。别信"自动改写安全"，先保守。
# 每条规则必须能通过 equivalence 对拍，否则不返回。

from .ast_nodes import Repeat, Group, Alt, CharClass, Literal, Concat


def rewrite(node):
    changed = False
    node, c1 = _collapse_nested(node)
    changed = changed or c1
    node, c2 = _merge_ambiguous_alt(node)
    changed = changed or c2
    return node, changed


def _collapse_nested(node):
    if isinstance(node, Repeat):
        inner, c = _collapse_nested(node.inner)
        node = Repeat(inner, node.min, node.max, node.greedy)

        # (a+)+ → a+
        # 注意：外层的 + 有可能包着的是 (a+) 这个 Group。
        # 所以我们要先看穿 Group，找到里面真正的结构。
        target = node.inner
        # 无论是捕获组 (a+) 还是非捕获组 (?:a+)，都强行穿进去。
        # 这里的取舍：丢掉捕获组语义，换取防 ReDoS 爆炸。
        if isinstance(target, Group):
            target = target.inner

        # 如果里面的目标是个无限重复 (比如 * 或 +)
        if isinstance(target, Repeat):
            outer_inf = (node.max is None and node.min in (0, 1))
            inner_inf = (target.max is None and target.min in (0, 1))

            if outer_inf and inner_inf:
                # 合并规则：只要有一个是 *，结果就是 *；否则是 +
                new_min = 0 if (node.min == 0 or target.min == 0) else 1

                # 直接把内层剥出来。如果是 (a+)+，结果就是 a+。
                return Repeat(target.inner, new_min, None, node.greedy), True

        return node, c
    if isinstance(node, Concat):
        parts, changed = [], False
        for p in node.parts:
            np, c = _collapse_nested(p)
            parts.append(np)
            changed = changed or c
        return Concat(parts), changed
    if isinstance(node, Alt):
        branches, changed = [], False
        for b in node.branches:
            nb, c = _collapse_nested(b)
            branches.append(nb)
            changed = changed or c
        return Alt(branches), changed
    if isinstance(node, Group):
        inner, c = _collapse_nested(node.inner)
        return Group(inner, node.capturing, node.index), c
    return node, False


def _merge_ambiguous_alt(node):
    # (a|aa)+ → a+ 这种先不做，太激进
    # 只处理单字符字面量的 alt: (a|b) 不合并，没什么收益
    return node, False


def to_string(node):
    # 简单回写，不保证最小化
    if isinstance(node, Literal):
        return node.ch
    if isinstance(node, CharClass):
        body = ''.join(sorted(node.chars))
        return '[' + ('^' if node.negated else '') + body + ']'
    if isinstance(node, Concat):
        return ''.join(to_string(p) for p in node.parts)
    if isinstance(node, Alt):
        return '|'.join(to_string(b) for b in node.branches)
    if isinstance(node, Repeat):
        inner = to_string(node.inner)
        # 加括号防优先级问题
        if isinstance(node.inner, Concat) or isinstance(node.inner, Alt):
            inner = '(' + inner + ')'
        if node.min == 0 and node.max is None:
            return inner + '*'
        if node.min == 1 and node.max is None:
            return inner + '+'
        if node.min == 0 and node.max == 1:
            return inner + '?'
        if node.min == node.max:
            return inner + '{%d}' % node.min
        if node.max is None:
            return inner + '{%d,}' % node.min
        return inner + '{%d,%d}' % (node.min, node.max)
    if isinstance(node, Group):
        return '(' + to_string(node.inner) + ')'
    return ''