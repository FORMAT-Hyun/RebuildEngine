from .lexer import Lexer
from .parser import Parser
from .interpreter import Interpreter, Environment, ReaRuntimeError
from . import ast as AST

def compile_rea(source: str) -> AST.Program:
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()

def create_interpreter() -> Interpreter:
    return Interpreter()
