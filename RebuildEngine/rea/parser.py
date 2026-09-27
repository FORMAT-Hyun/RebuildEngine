"""Parser for Rea language."""

from typing import List, Optional, Any
from .lexer import Lexer, Token, TokenType
from . import ast as AST


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def error(self, msg: str):
        tok = self.current()
        raise SyntaxError(f"[줄 {tok.line}] 파서 오류: {msg} (토큰: {tok.type.name} '{tok.value}')")

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek(self, offset: int = 0) -> Token:
        i = self.pos + offset
        if i < len(self.tokens):
            return self.tokens[i]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok

    def match(self, *types: TokenType) -> bool:
        if self.current().type in types:
            self.advance()
            return True
        return False

    def expect(self, typ: TokenType, msg: str = "") -> Token:
        if self.current().type == typ:
            return self.advance()
        self.error(msg or f"{typ.name} 이(가) 필요합니다")

    def skip_newlines(self):
        while self.match(TokenType.NEWLINE):
            pass

    def parse(self) -> AST.Program:
        program = AST.Program(line=1)
        self.skip_newlines()
        while self.current().type != TokenType.EOF:
            if self.current().type == TokenType.OBJECT:
                obj = self.parse_object()
                program.objects.append(obj)
            elif self.current().type == TokenType.FUNC:
                func = self.parse_function()
                program.functions.append(func)
            else:
                # top-level statement (rare)
                stmt = self.parse_statement()
                if stmt:
                    program.statements.append(stmt)
            self.skip_newlines()
        return program

    def parse_object(self) -> AST.ObjectDef:
        self.expect(TokenType.OBJECT)
        name_tok = self.expect(TokenType.IDENT, "오브젝트 이름이 필요합니다")
        name = name_tok.value
        self.expect(TokenType.COLON, "':' 이 필요합니다")
        self.skip_newlines()

        events = {}
        if self.current().type == TokenType.INDENT:
            self.advance()  # INDENT
            while self.current().type not in (TokenType.DEDENT, TokenType.EOF):
                self.skip_newlines()
                if self.current().type == TokenType.DEDENT:
                    break
                event_name, body = self.parse_event()
                events[event_name] = body
                self.skip_newlines()
            if self.current().type == TokenType.DEDENT:
                self.advance()
        return AST.ObjectDef(name=name, events=events, line=name_tok.line)

    def parse_event(self):
        """Parse event like: 생성할 때: or 매 순간: etc."""
        # Collect tokens until COLON
        parts = []
        start_line = self.current().line
        while self.current().type not in (TokenType.COLON, TokenType.NEWLINE, TokenType.EOF, TokenType.DEDENT):
            if self.current().type in (TokenType.IDENT, TokenType.CREATE, TokenType.STEP, TokenType.DRAW, TokenType.COLLISION):
                parts.append(self.advance().value)
            else:
                break
        if not parts:
            self.error("이벤트 이름이 필요합니다")
        self.expect(TokenType.COLON, "이벤트 뒤에 ':' 이 필요합니다")
        self.skip_newlines()

        # Map common Korean event names
        key = " ".join(parts)
        event_map = {
            "생성할 때": "create",
            "생성할": "create",
            "매 순간": "step",
            "매": "step",
            "그릴 때": "draw",
            "그릴": "draw",
            "충돌할 때": "collision",
            "충돌할": "collision",
        }
        event_name = event_map.get(key, key)

        body = self.parse_block()
        return event_name, body

    def parse_block(self) -> List[Any]:
        stmts = []
        if self.current().type == TokenType.INDENT:
            self.advance()
            while self.current().type not in (TokenType.DEDENT, TokenType.EOF):
                self.skip_newlines()
                if self.current().type == TokenType.DEDENT:
                    break
                stmt = self.parse_statement()
                if stmt is not None:
                    stmts.append(stmt)
                self.skip_newlines()
            if self.current().type == TokenType.DEDENT:
                self.advance()
        else:
            # single statement on same line (rare)
            stmt = self.parse_statement()
            if stmt:
                stmts.append(stmt)
        return stmts

    def parse_function(self) -> AST.FunctionDef:
        self.expect(TokenType.FUNC)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.LPAREN)
        params = []
        if self.current().type != TokenType.RPAREN:
            params.append(self.expect(TokenType.IDENT).value)
            while self.match(TokenType.COMMA):
                params.append(self.expect(TokenType.IDENT).value)
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.COLON)
        self.skip_newlines()
        body = self.parse_block()
        return AST.FunctionDef(name=name, params=params, body=body, line=self.current().line)

    def parse_statement(self) -> Optional[Any]:
        tok = self.current()
        if tok.type == TokenType.IF:
            return self.parse_if()
        if tok.type == TokenType.WHILE:
            return self.parse_while()
        if tok.type == TokenType.FOR:
            return self.parse_for()
        if tok.type == TokenType.RETURN:
            return self.parse_return()
        if tok.type == TokenType.NEWLINE or tok.type == TokenType.DEDENT:
            return None

        # Assignment or expression / call
        # Lookahead for assignment
        if tok.type == TokenType.IDENT:
            # could be assign, compound assign, or call
            if self.peek(1).type in (TokenType.EQ, TokenType.PLUS_EQ, TokenType.MINUS_EQ, TokenType.STAR_EQ, TokenType.SLASH_EQ):
                return self.parse_assign()
            # function call as statement
            if self.peek(1).type == TokenType.LPAREN:
                return self.parse_call_expr()
            # just variable? ignore or error
            self.advance()
            return None

        # expression statement
        expr = self.parse_expression()
        return expr

    def parse_assign(self) -> AST.Assign:
        name = self.expect(TokenType.IDENT).value
        op_tok = self.advance()
        value = self.parse_expression()
        if op_tok.type == TokenType.EQ:
            return AST.Assign(name=name, value=value, line=op_tok.line)
        # compound: x += 1  -->  x = x + 1
        op_map = {
            TokenType.PLUS_EQ: "+",
            TokenType.MINUS_EQ: "-",
            TokenType.STAR_EQ: "*",
            TokenType.SLASH_EQ: "/",
        }
        binop = AST.BinaryOp(op=op_map[op_tok.type], left=AST.Variable(name=name, line=op_tok.line), right=value, line=op_tok.line)
        return AST.Assign(name=name, value=binop, line=op_tok.line)

    def parse_if(self) -> AST.If:
        line = self.current().line
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()
        then_body = self.parse_block()
        else_body = None
        self.skip_newlines()
        if self.current().type == TokenType.ELSE:
            self.advance()
            self.expect(TokenType.COLON)
            self.skip_newlines()
            else_body = self.parse_block()
        return AST.If(condition=condition, then_body=then_body, else_body=else_body, line=line)

    def parse_while(self) -> AST.While:
        line = self.current().line
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()
        body = self.parse_block()
        return AST.While(condition=condition, body=body, line=line)

    def parse_for(self) -> AST.For:
        # 반복 i = 0 부터 10:
        line = self.current().line
        self.expect(TokenType.FOR)
        var = self.expect(TokenType.IDENT).value
        self.expect(TokenType.EQ)
        start = self.parse_expression()
        # optional "부터"
        if self.current().type == TokenType.IDENT and self.current().value in ("부터", "to"):
            self.advance()
        end = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()
        body = self.parse_block()
        return AST.For(var=var, start=start, end=end, body=body, line=line)

    def parse_return(self) -> AST.Return:
        line = self.current().line
        self.expect(TokenType.RETURN)
        value = None
        if self.current().type not in (TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF):
            value = self.parse_expression()
        return AST.Return(value=value, line=line)

    # Expression parsing (precedence climbing)
    def parse_expression(self) -> Any:
        return self.parse_or()

    def parse_or(self) -> Any:
        left = self.parse_and()
        while self.current().type == TokenType.OR:
            op = self.advance().value
            right = self.parse_and()
            left = AST.BinaryOp(op="or", left=left, right=right, line=left.line)
        return left

    def parse_and(self) -> Any:
        left = self.parse_equality()
        while self.current().type == TokenType.AND:
            op = self.advance().value
            right = self.parse_equality()
            left = AST.BinaryOp(op="and", left=left, right=right, line=left.line)
        return left

    def parse_equality(self) -> Any:
        left = self.parse_comparison()
        while self.current().type in (TokenType.EQEQ, TokenType.NEQ):
            op = self.advance().value
            right = self.parse_comparison()
            left = AST.BinaryOp(op=op, left=left, right=right, line=left.line)
        return left

    def parse_comparison(self) -> Any:
        left = self.parse_term()
        while self.current().type in (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.advance().value
            right = self.parse_term()
            left = AST.BinaryOp(op=op, left=left, right=right, line=left.line)
        return left

    def parse_term(self) -> Any:
        left = self.parse_factor()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self.parse_factor()
            left = AST.BinaryOp(op=op, left=left, right=right, line=left.line)
        return left

    def parse_factor(self) -> Any:
        left = self.parse_unary()
        while self.current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance().value
            right = self.parse_unary()
            left = AST.BinaryOp(op=op, left=left, right=right, line=left.line)
        return left

    def parse_unary(self) -> Any:
        if self.current().type in (TokenType.MINUS, TokenType.NOT):
            op = self.advance().value
            expr = self.parse_unary()
            return AST.UnaryOp(op=op if op != "아니다" else "not", expr=expr, line=expr.line)
        return self.parse_primary()

    def parse_primary(self) -> Any:
        tok = self.current()
        if tok.type == TokenType.NUMBER:
            self.advance()
            return AST.Number(value=tok.value, line=tok.line)
        if tok.type == TokenType.STRING:
            self.advance()
            return AST.String(value=tok.value, line=tok.line)
        if tok.type == TokenType.TRUE:
            self.advance()
            return AST.Boolean(value=True, line=tok.line)
        if tok.type == TokenType.FALSE:
            self.advance()
            return AST.Boolean(value=False, line=tok.line)
        if tok.type == TokenType.IDENT:
            # Support multi-word function names: 키를 눌렀다(...)
            # Collect consecutive IDENTs, then if LPAREN -> call, else variable (first only)
            names = []
            start_line = tok.line
            while self.current().type == TokenType.IDENT:
                names.append(self.advance().value)
                if self.current().type != TokenType.IDENT:
                    break
            if self.current().type == TokenType.LPAREN:
                # function call with possibly multi-word name
                full_name = " ".join(names)
                # also try underscore version
                return self._finish_call(full_name, start_line)
            # variable: only first name, put others back? For simplicity take last or first
            # Usually single. If multiple without (, treat as error or first
            if len(names) > 1:
                # put remaining back by not consuming? Already consumed.
                # For now treat joined as variable name (rare)
                return AST.Variable(name=" ".join(names), line=start_line)
            return AST.Variable(name=names[0], line=start_line)
        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        self.error(f"예상치 못한 토큰: {tok.type.name}")

    def _finish_call(self, name: str, line: int) -> AST.Call:
        self.expect(TokenType.LPAREN)
        args = []
        if self.current().type != TokenType.RPAREN:
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expression())
        self.expect(TokenType.RPAREN)
        return AST.Call(name=name, args=args, line=line)

    def parse_call_expr(self) -> AST.Call:
        name_tok = self.expect(TokenType.IDENT)
        return self._finish_call(name_tok.value, name_tok.line)
