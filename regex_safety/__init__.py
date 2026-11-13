# 这个文件让 Python 把 regex_safety 当成一个包，不要删。
__version__ = "0.4.0"
__author__ = "zxy"

# 暴露顶层 API，方便外部调用
from .parser import Parser, ParseError
from .nfa import build, fullmatch, search, findall
from .risk import analyze
from .rewrite import rewrite, to_string
from .equivalence import dfa_isomorphic