"""Lexer for Rea language (Korean scripting)."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    # Keywords
    OBJECT = auto()          # 오브젝트
    CREATE = auto()          # 생성할 때
    STEP = auto()            # 매 순간
    DRAW = auto()            # 그릴 때
    COLLISION = auto()       # 충돌할 때
    IF = auto()              # 만약
    ELSE = auto()            # 아니면
    WHILE = auto()           # 동안
    FOR = auto()             # 반복
    FUNC = auto()            # 함수
    RETURN = auto()          # 반환
    TRUE = auto()            # 참
    FALSE = auto()           # 거짓
    AND = auto()             # 그리고
    OR = auto()              # 또는
    NOT = auto()             # 아니다

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()              # =
    EQEQ = auto()            # ==
    NEQ = auto()             # !=
    LT = auto()              # <
    GT = auto()              # >
    LTE = auto()             # <=
    GTE = auto()             # >=
    PLUS_EQ = auto()         # +=
    MINUS_EQ = auto()        # -=
    STAR_EQ = auto()         # *=
    SLASH_EQ = auto()        # /=

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()          # not used, we use indentation or :
    RBRACE = auto()
    COLON = auto()
    COMMA = auto()
    DOT = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()

    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()

    EOF = auto()
    COMMENT = auto()


@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    col: int


KEYWORDS = {
    "오브젝트": TokenType.OBJECT,
    "생성할": TokenType.CREATE,   # 생성할 때
    "매": TokenType.STEP,         # 매 순간
    "그릴": TokenType.DRAW,       # 그릴 때
    "충돌할": TokenType.COLLISION,
    "만약": TokenType.IF,
    "아니면": TokenType.ELSE,
    "동안": TokenType.WHILE,
    "반복": TokenType.FOR,
    "함수": TokenType.FUNC,
    "반환": TokenType.RETURN,
    "참": TokenType.TRUE,
    "거짓": TokenType.FALSE,
    "그리고": TokenType.AND,
    "또는": TokenType.OR,
    "아니다": TokenType.NOT,
    # aliases / common words
    "때": None,  # handled specially
    "순간": None,
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.indent_stack = [0]

    def error(self, msg: str):
        raise SyntaxError(f"[줄 {self.line}] 렉서 오류: {msg}")

    def peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        if i >= len(self.source):
            return "\0"
        return self.source[i]

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def skip_whitespace_except_newline(self):
        while self.peek() in (" ", "\t", "\r"):
            self.advance()

    def read_number(self) -> Token:
        start_col = self.col
        num_str = ""
        while self.peek().isdigit() or self.peek() == ".":
            num_str += self.advance()
        try:
            if "." in num_str:
                val = float(num_str)
            else:
                val = int(num_str)
        except ValueError:
            self.error(f"잘못된 숫자: {num_str}")
        return Token(TokenType.NUMBER, val, self.line, start_col)

    def read_string(self) -> Token:
        start_col = self.col
        quote = self.advance()  # " or '
        s = ""
        while self.peek() != quote and self.peek() != "\0":
            if self.peek() == "\\":
                self.advance()
                esc = self.advance()
                if esc == "n":
                    s += "\n"
                elif esc == "t":
                    s += "\t"
                elif esc == "\\":
                    s += "\\"
                elif esc == quote:
                    s += quote
                else:
                    s += esc
            else:
                s += self.advance()
        if self.peek() != quote:
            self.error("문자열이 닫히지 않았습니다")
        self.advance()  # closing quote
        return Token(TokenType.STRING, s, self.line, start_col)

    def read_ident_or_keyword(self) -> Token:
        start_col = self.col
        ident = ""
        while self.peek().isalnum() or self.peek() in ("_", "가", "나", "다", "라", "마", "바", "사", "아", "자", "차", "카", "타", "파", "하") or "\uac00" <= self.peek() <= "\ud7a3":
            # Korean Hangul range
            ident += self.advance()
        # Better Hangul check
        # Actually simplify: continue while not whitespace/symbol
        # Re-do properly

        # Fallback: we already advanced some, but let's make robust
        return self._finish_ident(ident, start_col)

    def _finish_ident(self, ident: str, start_col: int) -> Token:
        # Continue reading Hangul and alnum
        while True:
            ch = self.peek()
            if ch.isalnum() or ch == "_" or ("\uac00" <= ch <= "\ud7a3") or ch in "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ":
                ident += self.advance()
            else:
                break

        if ident in KEYWORDS:
            kw = KEYWORDS[ident]
            if kw is not None:
                return Token(kw, ident, self.line, start_col)
            # special cases like "때", "순간" are part of multi-word
            return Token(TokenType.IDENT, ident, self.line, start_col)
        return Token(TokenType.IDENT, ident, self.line, start_col)

    def tokenize(self) -> List[Token]:
        self.tokens = []
        at_line_start = True

        while self.pos < len(self.source):
            # Handle indentation at start of line
            if at_line_start:
                indent = 0
                while self.peek() in (" ", "\t"):
                    if self.peek() == "\t":
                        indent += 4
                    else:
                        indent += 1
                    self.advance()
                # Skip empty lines and comments
                if self.peek() in ("\n", "\0"):
                    if self.peek() == "\n":
                        self.advance()
                    continue
                if self.peek() == "#":
                    while self.peek() not in ("\n", "\0"):
                        self.advance()
                    continue

                # Emit INDENT/DEDENT
                current = self.indent_stack[-1]
                if indent > current:
                    self.indent_stack.append(indent)
                    self.tokens.append(Token(TokenType.INDENT, indent, self.line, 1))
                elif indent < current:
                    while self.indent_stack and self.indent_stack[-1] > indent:
                        self.indent_stack.pop()
                        self.tokens.append(Token(TokenType.DEDENT, indent, self.line, 1))
                    if not self.indent_stack or self.indent_stack[-1] != indent:
                        self.error("들여쓰기가 일치하지 않습니다")
                at_line_start = False

            self.skip_whitespace_except_newline()

            ch = self.peek()
            if ch == "\0":
                break

            if ch == "\n":
                self.advance()
                self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line - 1, self.col))
                at_line_start = True
                continue

            if ch == "#":
                while self.peek() not in ("\n", "\0"):
                    self.advance()
                continue

            start_line, start_col = self.line, self.col

            # Multi-char operators
            if ch == "=":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.EQEQ, "==", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.EQ, "=", start_line, start_col))
                continue
            if ch == "!":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.NEQ, "!=", start_line, start_col))
                else:
                    self.error("알 수 없는 문자 '!'")
                continue
            if ch == "<":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.LTE, "<=", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.LT, "<", start_line, start_col))
                continue
            if ch == ">":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.GTE, ">=", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.GT, ">", start_line, start_col))
                continue
            if ch == "+":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.PLUS_EQ, "+=", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.PLUS, "+", start_line, start_col))
                continue
            if ch == "-":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.MINUS_EQ, "-=", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.MINUS, "-", start_line, start_col))
                continue
            if ch == "*":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.STAR_EQ, "*=", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.STAR, "*", start_line, start_col))
                continue
            if ch == "/":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.SLASH_EQ, "/=", start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.SLASH, "/", start_line, start_col))
                continue
            if ch == "%":
                self.advance()
                self.tokens.append(Token(TokenType.PERCENT, "%", start_line, start_col))
                continue

            if ch == "(":
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col))
                continue
            if ch == ")":
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col))
                continue
            if ch == ":":
                self.advance()
                self.tokens.append(Token(TokenType.COLON, ":", start_line, start_col))
                continue
            if ch == ",":
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, ",", start_line, start_col))
                continue
            if ch == ".":
                self.advance()
                self.tokens.append(Token(TokenType.DOT, ".", start_line, start_col))
                continue

            if ch in ('"', "'"):
                self.tokens.append(self.read_string())
                continue

            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Identifier / keyword (including Hangul)
            if ch.isalpha() or ch == "_" or ("\uac00" <= ch <= "\ud7a3"):
                ident = ""
                while True:
                    c = self.peek()
                    if c.isalnum() or c == "_" or ("\uac00" <= c <= "\ud7a3"):
                        ident += self.advance()
                    else:
                        break
                if ident in KEYWORDS and KEYWORDS[ident] is not None:
                    self.tokens.append(Token(KEYWORDS[ident], ident, start_line, start_col))
                else:
                    # Handle multi-word keywords: 생성할 때, 매 순간, 그릴 때, 충돌할 때
                    self.tokens.append(Token(TokenType.IDENT, ident, start_line, start_col))
                continue

            self.error(f"알 수 없는 문자: '{ch}'")

        # Final dedents
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, 0, self.line, 1))

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens
