"""Small deterministic tools used by the AgentTrace demonstration agent."""

import ast
import operator
from typing import Any


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_calculate(expression: str) -> str:
    """Evaluate arithmetic expressions without exposing Python evaluation."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
        if abs(result) > 1e15:
            return "Calculation exceeds the supported numeric range."
        return f"{expression} = {result:g}"
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return "No valid arithmetic expression was supplied."


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Exponent is too large")
        return float(_OPERATORS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return float(_OPERATORS[type(node.op)](_evaluate(node.operand)))
    raise ValueError("Unsupported expression")


def run_tool(expression: str | None) -> str:
    if not expression:
        return "No calculation requested."
    return safe_calculate(expression)
