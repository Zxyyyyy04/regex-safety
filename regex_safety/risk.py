# 启发式分级。不是严格判定，README 里要写清楚。
# 判断逻辑：嵌套量词/歧义分支 → EXPONENTIAL，其余按情况降级。

from .ast_nodes import Repeat, Alt, Concat, Group, CharClass, Literal


SAFE = "SAFE"
LINEAR = "LINEAR"
POLY = "POLYNOMIAL"
EXP = "EXPONENTIAL"


def analyze(node):
    return _risk(node, {})


def _risk(node, env):
    # env 没用上，本来想传上下文，先留着
    if isinstance(node, Repeat):
        inner_risk = _risk(node.inner, env)
        if inner_risk == EXP:
            return EXP
        if _has_alt(node.inner) or _has_repeat(node.inner):
            return EXP
        if _is_ambiguous(node.inner):
            return POLY
        return LINEAR

    if isinstance(node, Concat):
        rs = [_risk(p, env) for p in node.parts]
        return max(rs, key=_order)

    if isinstance(node, Alt):
        # 歧义分支：a|aa 这种，前缀相同
        if _branches_overlap(node.branches):
            return POLY
        rs = [_risk(b, env) for b in node.branches]
        return max(rs, key=_order)

    if isinstance(node, Group):
        return _risk(node.inner, env)

    return SAFE


def _order(r):
    return {SAFE: 0, LINEAR: 1, POLY: 2, EXP: 3}[r]


def _has_repeat(node):
    if isinstance(node, Repeat):
        return True
    if isinstance(node, Concat):
        return any(_has_repeat(p) for p in node.parts)
    if isinstance(node, Alt):
        return any(_has_repeat(b) for b in node.branches)
    if isinstance(node, Group):
        return _has_repeat(node.inner)
    return False


def _has_alt(node):
    if isinstance(node, Alt):
        return True
    if isinstance(node, Concat):
        return any(_has_alt(p) for p in node.parts)
    if isinstance(node, Repeat):
        return _has_alt(node.inner)
    if isinstance(node, Group):
        return _has_alt(node.inner)
    return False


def _is_ambiguous(node):
    # 粗判：单个字符类里含多个字符且被量词套，算重叠
    if isinstance(node, Repeat):
        if isinstance(node.inner, CharClass) and len(node.inner.chars) > 1:
            return True
    return False


def _branches_overlap(branches):
    firsts = []
    for b in branches:
        firsts.append(_first_chars(b))
    for i in range(len(firsts)):
        for j in range(i + 1, len(firsts)):
            if firsts[i] & firsts[j]:
                return True
    return False


def _first_chars(node):
    if isinstance(node, Literal):
        return {node.ch}
    if isinstance(node, CharClass):
        return set(node.chars)
    if isinstance(node, Concat):
        return _first_chars(node.parts[0])
    if isinstance(node, Group):
        return _first_chars(node.inner)
    if isinstance(node, Repeat):
        return _first_chars(node.inner)
    return set()


def dangerous_nodes(node):
    # 给报告用，TODO: 位置信息现在没有，得靠 parser 记 span
    out = []
    _collect(node, out)
    return out


def _collect(node, out):
    if isinstance(node, Repeat):
        if _has_alt(node.inner) or _has_repeat(node.inner) or _is_ambiguous(node.inner):
            out.append({"type": "repeat", "inner": type(node.inner).__name__})
    if isinstance(node, Concat):
        for p in node.parts:
            _collect(p, out)
    if isinstance(node, Alt):
        if _branches_overlap(node.branches):
            out.append({"type": "ambiguous_alt"})
        for b in node.branches:
            _collect(b, out)
    if isinstance(node, Group):
        _collect(node.inner, out)
    if isinstance(node, Repeat):
        _collect(node.inner, out)