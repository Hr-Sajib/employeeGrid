import ast
import operator
from decimal import Decimal
from langchain_core.tools import tool

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        return OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval(node.operand))
    raise ValueError("only numbers and + - * / % ** ( ) are allowed")


def evaluate(expression: str) -> str:
    try:
        result = _eval(ast.parse(expression.replace(",", ""), mode="eval").body)
    except ZeroDivisionError:
        return "error: division by zero"
    except (ValueError, SyntaxError, ArithmeticError) as e:
        return f"error: {e}"
    return format(round(result, 6).normalize(), "f")


@tool
def calculate(expression: str) -> str:
    """Exact arithmetic on plain numbers, for example '5200 * 0.10'. Supports + - * / % ** and parentheses."""
    return evaluate(expression)
