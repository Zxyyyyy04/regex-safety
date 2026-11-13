# 递归下降。优先级从低到高：Alt < Concat < Repeat < Atom。
# 没做错误恢复，出错直接抛。新手项目够用。

from .ast_nodes import (
    Literal, CharClass, Dot, Concat, Alt,
    Repeat, Group, Anchor, Empty,
)


class ParseError(Exception):
    def __init__(self, msg, pos):
        super().__init__(f"{msg} at position {pos}")
        self.pos = pos


class Parser:
    def __init__(self, pattern):
        self.src = pattern
        self.pos = 0
        self._group_count = 0

    def parse(self):
        node = self._parse_alt()
        if self.pos != len(self.src):
            # 正常不会到这，除非有没闭合的括号
            raise ParseError(f"unexpected {self.src[self.pos]!r}", self.pos)
        return node

    def _peek(self):
        return self.src[self.pos] if self.pos < len(self.src) else None

    def _advance(self):
        c = self.src[self.pos]
        self.pos += 1
        return c

    def _parse_alt(self):
        branches = [self._parse_concat()]
        while self._peek() == '|':
            self._advance()
            branches.append(self._parse_concat())
        return branches[0] if len(branches) == 1 else Alt(branches)

    def _parse_concat(self):
        parts = []
        while self.pos < len(self.src) and self._peek() not in '|)':
            parts.append(self._parse_repeat())
        if not parts:
            return Empty()
        return parts[0] if len(parts) == 1 else Concat(parts)

    def _parse_repeat(self):
        atom = self._parse_atom()
        while True:
            c = self._peek()
            if c == '*':
                self._advance()
                atom = Repeat(atom, 0, None)
            elif c == '+':
                self._advance()
                atom = Repeat(atom, 1, None)
            elif c == '?':
                self._advance()
                atom = Repeat(atom, 0, 1)
            elif c == '{':
                # {n} {n,} {n,m}
                save = self.pos
                self._advance()
                try:
                    mn, mx = self._parse_braces()
                    atom = Repeat(atom, mn, mx)
                except ParseError:
                    self.pos = save
                    break
            else:
                break
            # 非贪婪
            if self._peek() == '?':
                self._advance()
                atom.greedy = False
        return atom

    def _parse_braces(self):
        digits = ''
        while self._peek() and self._peek().isdigit():
            digits += self._advance()
        if not digits:
            raise ParseError("expected number in {}", self.pos)
        mn = int(digits)
        if self._peek() == '}':
            self._advance()
            return mn, mn
        if self._peek() != ',':
            raise ParseError("expected , or }", self.pos)
        self._advance()
        if self._peek() == '}':
            self._advance()
            return mn, None
        digits = ''
        while self._peek() and self._peek().isdigit():
            digits += self._advance()
        if not digits or self._peek() != '}':
            raise ParseError("expected }", self.pos)
        self._advance()
        return mn, int(digits)

    def _parse_atom(self):
        c = self._peek()
        if c is None:
            raise ParseError("unexpected end", self.pos)
        if c == '(':
            self._advance()
            capturing = True
            if self.src[self.pos:self.pos + 2] == '?:':
                self.pos += 2
                capturing = False
            inner = self._parse_alt()
            if self._peek() != ')':
                raise ParseError("missing )", self.pos)
            self._advance()
            if capturing:
                self._group_count += 1
                return Group(inner, True, self._group_count)
            return Group(inner, False, 0)
        if c == '[':
            return self._parse_charclass()
        if c == '.':
            self._advance()
            return Dot()
        if c == '^':
            self._advance()
            return Anchor('^')
        if c == '$':
            self._advance()
            return Anchor('$')
        if c == '\\':
            self._advance()
            nxt = self._peek()
            if nxt is None:
                raise ParseError("trailing backslash", self.pos)
            self._advance()
            # 只处理常用转义，TODO: \b \B \1 反向引用
            mapping = {'d': set('0123456789'), 'w': set(
                'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'),
                's': set(' \t\n\r')}
            if nxt in mapping:
                return CharClass(mapping[nxt])
            return Literal(nxt)
        self._advance()
        return Literal(c)

    def _parse_charclass(self):
        self._advance()  # [
        negated = False
        if self._peek() == '^':
            self._advance()
            negated = True
        chars = set()
        while True:
            c = self._peek()
            if c is None:
                raise ParseError("unclosed [", self.pos)
            if c == ']':
                self._advance()
                break
            self._advance()
            if c == '\\':
                nxt = self._peek()
                self._advance()
                # TODO: 只处理单字符转义，\d 在字符类里没展开
                chars.add(nxt)
                continue
            # 范围 a-z
            if self._peek() == '-' and self.pos + 1 < len(self.src) and self.src[self.pos + 1] != ']':
                self._advance()
                hi = self._advance()
                for x in range(ord(c), ord(hi) + 1):
                    chars.add(chr(x))
            else:
                chars.add(c)
        return CharClass(chars, negated)