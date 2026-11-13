# 只负责把 NFA 转成 DFA，用于测状态爆炸。
# 取舍：不处理捕获组，因为 DFA 每一条路径都被合并了，无法记录下标。
# 但纯匹配（is_match）完全没问题。

from .nfa import epsilon_closure


class DFA:
    def __init__(self):
        self.trans = {}  # state_id -> {char: state_id}
        self.start = None
        self.accepts = set()
        self.state_count = 0


def build_dfa(nfa):
    dfa = DFA()

    # 初始状态是 NFA 起始状态的 epsilon 闭包
    start_closure = frozenset(epsilon_closure(nfa, {nfa.start}))
    dfa.start = 0
    dfa.trans[0] = {}

    # 用一个队列来做子集构造
    queue = [start_closure]
    # 映射：frozenset(状态集合) -> DFA 的状态 ID
    state_map = {start_closure: 0}

    while queue:
        current_set = queue.pop(0)
        current_id = state_map[current_set]

        # 判断当前集合是否包含 NFA 的接受状态
        if nfa.accept in current_set:
            dfa.accepts.add(current_id)

        # 收集当前集合能遇到的所有字符
        # 注意：'*' 代表任意字符，这里为了简化，只取具体的字符做转移
        chars = set()
        for s in current_set:
            if s in nfa.trans:
                chars.update(nfa.trans[s].keys())

        for ch in chars:
            # 计算 move
            next_set = set()
            for s in current_set:
                if s in nfa.trans and ch in nfa.trans[s]:
                    next_set.update(nfa.trans[s][ch])

            if not next_set:
                continue

            # 计算 epsilon 闭包
            next_closure = frozenset(epsilon_closure(nfa, next_set))

            if next_closure not in state_map:
                new_id = len(state_map)
                state_map[next_closure] = new_id
                dfa.trans[new_id] = {}
                queue.append(next_closure)

            next_id = state_map[next_closure]
            dfa.trans[current_id][ch] = next_id

    dfa.state_count = len(state_map)
    return dfa


def is_match_dfa(dfa, text):
    state = dfa.start
    for ch in text:
        if ch not in dfa.trans.get(state, {}):
            return False
        state = dfa.trans[state][ch]
    return state in dfa.accepts