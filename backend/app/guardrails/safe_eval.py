"""Evaluate arithmetic expressions from the LLM without eval/exec (AST whitelist)."""
import ast
import operator

import numpy as np

MAX_LEN = 500
MAX_EXPONENT = 100
BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
FUNCS = {
    "abs": np.abs,
    "round": np.round,
    "sqrt": np.sqrt,
    "log": np.log,
    "exp": np.exp,
    "min": np.minimum,
    "max": np.maximum,
}


class UnsafeExpressionError(ValueError):
    pass


def safe_eval(expr: str, names: dict[str, object]):
    if len(expr) > MAX_LEN:
        raise UnsafeExpressionError("Expression is too long.")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"Invalid expression: {exc.msg}") from exc
    return _eval(tree.body, names)


def _eval(node: ast.AST, names: dict[str, object]):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError("Only numeric constants are allowed.")
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in names:
            raise UnsafeExpressionError(f"Unknown name '{node.id}'.")
        return names[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
        left = _eval(node.left, names)
        right = _eval(node.right, names)
        if isinstance(node.op, ast.Pow) and np.any(np.abs(np.asarray(right, dtype=float)) > MAX_EXPONENT):
            raise UnsafeExpressionError("Exponent too large.")
        return BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](_eval(node.operand, names))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FUNCS
        and not node.keywords
        and 1 <= len(node.args) <= 2
    ):
        return FUNCS[node.func.id](*[_eval(a, names) for a in node.args])
    raise UnsafeExpressionError(f"Disallowed expression element: {type(node).__name__}.")
