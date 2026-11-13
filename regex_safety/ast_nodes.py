# AST 节点。没用继承树，因为节点就这几种，isinstance 够了。
# 本来想上 dataclass 的 frozen，但后面 rewrite 要改字段，算了。

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Literal:
    ch: str


@dataclass
class CharClass:
    # 先只存字符集合，范围在 parser 里展开。缺点：大范围会占内存，
    # 但 MVP 正则都短，先不管。TODO: 换成区间表示
    chars: set
    negated: bool = False


@dataclass
class Dot:
    # '.' 单独一个节点，因为 risk 分析里 '.' 和字符类的风险不一样
    pass


@dataclass
class Concat:
    parts: list


@dataclass
class Alt:
    branches: list


@dataclass
class Repeat:
    inner: object
    min: int
    max: Optional[int]   # None 表示无穷
    greedy: bool = True


@dataclass
class Group:
    inner: object
    capturing: bool = True
    index: int = 0       # 0 表示还没编号


@dataclass
class Anchor:
    kind: str            # '^' 或 '$'


@dataclass
class Empty:
    # 空匹配，比如 'a|' 的右分支。留着是为了让 Concat/Alt 不用特判
    pass