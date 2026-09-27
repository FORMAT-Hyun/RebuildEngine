"""AST nodes for Rea language."""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Node:
    line: int = 0


@dataclass
class Program(Node):
    objects: List["ObjectDef"] = field(default_factory=list)
    functions: List["FunctionDef"] = field(default_factory=list)
    statements: List[Any] = field(default_factory=list)


@dataclass
class ObjectDef(Node):
    name: str = ""
    events: dict = field(default_factory=dict)


@dataclass
class FunctionDef(Node):
    name: str = ""
    params: List[str] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)


@dataclass
class Assign(Node):
    name: str = ""
    value: Any = None


@dataclass
class BinaryOp(Node):
    op: str = ""
    left: Any = None
    right: Any = None


@dataclass
class UnaryOp(Node):
    op: str = ""
    expr: Any = None


@dataclass
class Number(Node):
    value: float = 0.0


@dataclass
class String(Node):
    value: str = ""


@dataclass
class Boolean(Node):
    value: bool = False


@dataclass
class Variable(Node):
    name: str = ""


@dataclass
class Call(Node):
    name: str = ""
    args: List[Any] = field(default_factory=list)


@dataclass
class If(Node):
    condition: Any = None
    then_body: List[Any] = field(default_factory=list)
    else_body: Optional[List[Any]] = None


@dataclass
class While(Node):
    condition: Any = None
    body: List[Any] = field(default_factory=list)


@dataclass
class For(Node):
    var: str = ""
    start: Any = None
    end: Any = None
    body: List[Any] = field(default_factory=list)


@dataclass
class Return(Node):
    value: Optional[Any] = None


@dataclass
class Block(Node):
    statements: List[Any] = field(default_factory=list)
