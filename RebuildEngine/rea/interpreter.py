"""Interpreter for Rea language."""

from typing import Any, Dict, List, Optional, Callable
from . import ast as AST


class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


class ReaRuntimeError(Exception):
    def __init__(self, message: str, line: int = 0):
        self.message = message
        self.line = line
        super().__init__(f"[줄 {line}] {message}" if line else message)


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.vars: Dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str) -> Any:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise ReaRuntimeError(f"정의되지 않은 변수: '{name}'")

    def set(self, name: str, value: Any):
        # Set in current scope (or find existing)
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent and self.parent.has(name):
            self.parent.set(name, value)
            return
        self.vars[name] = value

    def has(self, name: str) -> bool:
        if name in self.vars:
            return True
        if self.parent:
            return self.parent.has(name)
        return False

    def define(self, name: str, value: Any):
        self.vars[name] = value


class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.builtins: Dict[str, Callable] = {}
        self.objects: Dict[str, AST.ObjectDef] = {}
        self.functions: Dict[str, AST.FunctionDef] = {}
        self._register_builtins()

    def _register_builtins(self):
        # These will be overridden/connected by the engine
        self.builtins["키를_눌렀다"] = lambda *a: False
        self.builtins["키를눌렀다"] = lambda *a: False
        self.builtins["그리기"] = lambda *a: None
        self.builtins["출력"] = lambda *a: print(*a)
        self.builtins["절대값"] = abs
        self.builtins["최소"] = min
        self.builtins["최대"] = max
        self.builtins["정수"] = int
        self.builtins["실수"] = float
        self.builtins["문자열"] = str

    def register_builtin(self, name: str, func: Callable):
        self.builtins[name] = func
        # also common variants
        self.builtins[name.replace("_", "")] = func

    def load(self, program: AST.Program):
        self.objects.clear()
        self.functions.clear()
        for obj in program.objects:
            self.objects[obj.name] = obj
        for func in program.functions:
            self.functions[func.name] = func

    def get_object(self, name: str) -> Optional[AST.ObjectDef]:
        return self.objects.get(name)

    def execute_block(self, statements: List[Any], env: Environment):
        for stmt in statements:
            self.execute(stmt, env)

    def execute(self, node: Any, env: Environment) -> Any:
        if node is None:
            return None
        method = getattr(self, f"exec_{type(node).__name__}", None)
        if method:
            return method(node, env)
        raise ReaRuntimeError(f"알 수 없는 노드: {type(node).__name__}", getattr(node, "line", 0))

    def exec_Assign(self, node: AST.Assign, env: Environment):
        value = self.evaluate(node.value, env)
        env.set(node.name, value)
        return value

    def exec_If(self, node: AST.If, env: Environment):
        cond = self.evaluate(node.condition, env)
        if self.is_truthy(cond):
            self.execute_block(node.then_body, env)
        elif node.else_body:
            self.execute_block(node.else_body, env)

    def exec_While(self, node: AST.While, env: Environment):
        while self.is_truthy(self.evaluate(node.condition, env)):
            self.execute_block(node.body, env)

    def exec_For(self, node: AST.For, env: Environment):
        start = int(self.evaluate(node.start, env))
        end = int(self.evaluate(node.end, env))
        for i in range(start, end + 1):
            env.define(node.var, i)
            self.execute_block(node.body, env)

    def exec_Return(self, node: AST.Return, env: Environment):
        value = self.evaluate(node.value, env) if node.value is not None else None
        raise ReturnValue(value)

    def exec_Call(self, node: AST.Call, env: Environment):
        return self.evaluate(node, env)

    def evaluate(self, node: Any, env: Environment) -> Any:
        if node is None:
            return None
        method = getattr(self, f"eval_{type(node).__name__}", None)
        if method:
            return method(node, env)
        # fallback: execute if statement-like
        if isinstance(node, (AST.Assign, AST.If, AST.While, AST.For, AST.Return)):
            return self.execute(node, env)
        raise ReaRuntimeError(f"평가할 수 없는 노드: {type(node).__name__}", getattr(node, "line", 0))

    def eval_Number(self, node: AST.Number, env: Environment):
        return node.value

    def eval_String(self, node: AST.String, env: Environment):
        return node.value

    def eval_Boolean(self, node: AST.Boolean, env: Environment):
        return node.value

    def eval_Variable(self, node: AST.Variable, env: Environment):
        return env.get(node.name)

    def eval_BinaryOp(self, node: AST.BinaryOp, env: Environment):
        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)
        op = node.op
        try:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right
            if op == "%":
                return left % right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
            if op == "and":
                return self.is_truthy(left) and self.is_truthy(right)
            if op == "or":
                return self.is_truthy(left) or self.is_truthy(right)
        except Exception as e:
            raise ReaRuntimeError(f"연산 오류 '{op}': {e}", node.line)
        raise ReaRuntimeError(f"알 수 없는 연산자: {op}", node.line)

    def eval_UnaryOp(self, node: AST.UnaryOp, env: Environment):
        val = self.evaluate(node.expr, env)
        if node.op == "-":
            return -val
        if node.op in ("not", "아니다"):
            return not self.is_truthy(val)
        raise ReaRuntimeError(f"알 수 없는 단항 연산자: {node.op}", node.line)

    def eval_Call(self, node: AST.Call, env: Environment):
        args = [self.evaluate(a, env) for a in node.args]
        name = node.name
        # Normalize names: original / space<->_ / no separator
        candidates = [
            name,
            name.replace(" ", "_"),
            name.replace("_", " "),
            name.replace(" ", ""),
            name.replace("_", ""),
        ]

        # Builtins first
        for cand in candidates:
            if cand in self.builtins:
                try:
                    return self.builtins[cand](*args)
                except Exception as e:
                    raise ReaRuntimeError(f"내장 함수 '{name}' 오류: {e}", node.line)

        # User functions
        for cand in candidates:
            if cand in self.functions:
                func = self.functions[cand]
                if len(args) != len(func.params):
                    raise ReaRuntimeError(
                        f"함수 '{name}' 인자 개수 불일치 (기대 {len(func.params)}, 받음 {len(args)})",
                        node.line,
                    )
                local = Environment(parent=env)
                for p, a in zip(func.params, args):
                    local.define(p, a)
                try:
                    self.execute_block(func.body, local)
                except ReturnValue as rv:
                    return rv.value
                return None

        raise ReaRuntimeError(f"정의되지 않은 함수: '{name}'", node.line)

    def is_truthy(self, value: Any) -> bool:
        if value is None or value is False:
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        if isinstance(value, str) and value == "":
            return False
        return True

    def run_event(self, object_name: str, event_name: str, env: Environment):
        obj = self.objects.get(object_name)
        if not obj:
            return
        body = obj.events.get(event_name)
        if body:
            try:
                self.execute_block(body, env)
            except ReturnValue:
                pass  # ignore return at event level
            except ReaRuntimeError:
                raise
            except Exception as e:
                raise ReaRuntimeError(f"이벤트 '{event_name}' 실행 중 오류: {e}", 0)
