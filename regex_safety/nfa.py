from .ast_nodes import (
    Literal, CharClass, Dot, Concat, Alt,
    Repeat, Group, Anchor, Empty,
)


class NFA:
    def __init__(self):
        self.trans = {}  # state -> {char: [state]}
        self.eps = {}  # state -> [(action, state)]
        self.start = None
        self.accept = None
        self._next = 0
        # 新增：记录取反字符集。键为特殊标记字符串（如 '~0'），值为需要排除的字符集合
        self.negated_sets = {}

    def new_state(self):
        s = self._next
        self._next += 1
        return s

    def add_trans(self, s, ch, t):
        self.trans.setdefault(s, {}).setdefault(ch, []).append(t)

    def add_eps(self, s, t, action=None):
        self.eps.setdefault(s, []).append((action, t))


def build(node):
    nfa = NFA()
    s, t = _build(node, nfa)
    nfa.start = s
    nfa.accept = t
    return nfa


def _build(node, nfa):
    if isinstance(node, Literal):
        s, t = nfa.new_state(), nfa.new_state()
        nfa.add_trans(s, node.ch, t)
        return s, t

    if isinstance(node, CharClass):
        s, t = nfa.new_state(), nfa.new_state()
        if node.negated:
            # 取反字符集：生成一个唯一的标记，挂载到 NFA 上
            key = f"~{len(nfa.negated_sets)}"
            nfa.negated_sets[key] = node.chars
            nfa.add_trans(s, key, t)
        else:
            for ch in node.chars:
                nfa.add_trans(s, ch, t)
        return s, t

    if isinstance(node, Dot):
        s, t = nfa.new_state(), nfa.new_state()
        nfa.add_trans(s, '*', t)
        return s, t

    if isinstance(node, Empty):
        s, t = nfa.new_state(), nfa.new_state()
        nfa.add_eps(s, t)
        return s, t

    if isinstance(node, Concat):
        s, _ = _build(node.parts[0], nfa)
        prev_t = _
        for p in node.parts[1:]:
            ps, pt = _build(p, nfa)
            nfa.add_eps(prev_t, ps)
            prev_t = pt
        return s, prev_t

    if isinstance(node, Alt):
        s, t = nfa.new_state(), nfa.new_state()
        for b in node.branches:
            bs, bt = _build(b, nfa)
            nfa.add_eps(s, bs)
            nfa.add_eps(bt, t)
        return s, t

    if isinstance(node, Group):
        s, t = nfa.new_state(), nfa.new_state()
        inner_s, inner_t = _build(node.inner, nfa)

        if node.capturing:
            nfa.add_eps(s, inner_s, ('enter', node.index))
            nfa.add_eps(inner_t, t, ('leave', node.index))
        else:
            nfa.add_eps(s, inner_s)
            nfa.add_eps(inner_t, t)
        return s, t

    if isinstance(node, Repeat):
        s, t = nfa.new_state(), nfa.new_state()
        inner_s, inner_t = _build(node.inner, nfa)
        prev = s
        for _ in range(node.min):
            is_, it = _build(node.inner, nfa)
            nfa.add_eps(prev, is_)
            prev = it
        if node.max is None:
            nfa.add_eps(prev, t)
            nfa.add_eps(prev, inner_s)
            nfa.add_eps(inner_t, inner_s)
            nfa.add_eps(inner_t, t)
        else:
            extra = node.max - node.min
            for _ in range(extra):
                nfa.add_eps(prev, t)
                is_, it = _build(node.inner, nfa)
                nfa.add_eps(prev, is_)
                prev = it
            nfa.add_eps(prev, t)
        return s, t

    if isinstance(node, Anchor):
        s, t = nfa.new_state(), nfa.new_state()
        nfa.add_eps(s, t)
        return s, t

    raise NotImplementedError(f"build: {type(node).__name__}")


# ================= DFA 构建所需的 epsilon 闭包 =================

def epsilon_closure(nfa, states):
    stack = list(states)
    seen = set(states)
    while stack:
        s = stack.pop()
        for action, t in nfa.eps.get(s, []):
            if t not in seen:
                seen.add(t)
                stack.append(t)
    return seen


# ================= 全新的模拟执行（带捕获组 DFS 版） =================

def _match_at(nfa, text, start_pos, full=False, max_steps=1000000):
    steps = 0
    stack = [(nfa.start, start_pos, {})]
    best_match = None

    while stack:
        state_id, pos, groups = stack.pop()
        steps += 1
        if steps > max_steps:
            break

        if state_id == nfa.accept:
            if full and pos != len(text):
                pass
            else:
                if best_match is None or pos > best_match["end"]:
                    best_match = {
                        "start": start_pos,
                        "end": pos,
                        "groups": groups.copy()
                    }
                continue

        for action, next_state in nfa.eps.get(state_id, []):
            new_groups = groups.copy()
            if action:
                kind, idx = action
                if kind == 'enter':
                    new_groups[idx] = (pos, None)
                elif kind == 'leave':
                    if idx in new_groups and new_groups[idx][1] is None:
                        new_groups[idx] = (new_groups[idx][0], pos)
            stack.append((next_state, pos, new_groups))

        if pos < len(text):
            ch = text[pos]
            # 1. 普通字符转移
            for next_state in nfa.trans.get(state_id, {}).get(ch, []):
                stack.append((next_state, pos + 1, groups.copy()))
            # 2. 通配符 (.)
            for next_state in nfa.trans.get(state_id, {}).get('*', []):
                stack.append((next_state, pos + 1, groups.copy()))

            # 3. 取反字符集 (处理以 '~' 开头的特殊边)
            for key, excluded in nfa.negated_sets.items():
                if ch not in excluded:
                    for next_state in nfa.trans.get(state_id, {}).get(key, []):
                        stack.append((next_state, pos + 1, groups.copy()))

    if best_match:
        result_groups = {}
        for idx, span in best_match["groups"].items():
            if span[0] is not None and span[1] is not None:
                result_groups[idx] = text[span[0]:span[1]]
            else:
                result_groups[idx] = None

        class Match:
            def __init__(self, text, start, end, groups):
                self.text = text
                self.start = start
                self.end = end
                self.groups_dict = groups

            def group(self, n=0):
                if n == 0:
                    return self.text[self.start:self.end]
                return self.groups_dict.get(n, None)

            def groups(self):
                if not self.groups_dict:
                    return ()
                max_idx = max(self.groups_dict.keys())
                return tuple(self.groups_dict.get(i) for i in range(1, max_idx + 1))

            def __repr__(self):
                return f"<Match object; span=({self.start}, {self.end}), match='{self.group(0)}'>"

        return Match(text, best_match["start"], best_match["end"], result_groups)

    return None


def search(nfa, text, start_pos=0, full=False):
    if full:
        return _match_at(nfa, text, start_pos=0, full=True)

    for i in range(start_pos, len(text) + 1):
        m = _match_at(nfa, text, start_pos=i, full=False)
        if m is not None:
            return m
    return None


def fullmatch(nfa, text, max_steps=1000000):
    return search(nfa, text, start_pos=0, full=True) is not None


def findall(nfa, text):
    results = []
    pos = 0
    while pos <= len(text):
        m = search(nfa, text, start_pos=pos)
        if m:
            if m.groups_dict:
                if len(m.groups_dict) == 1:
                    results.append(m.group(1))
                else:
                    results.append(m.groups())
            else:
                results.append(m.group(0))

            if m.start == m.end:
                pos = m.end + 1
            else:
                pos = m.end
        else:
            break
    return results