"""Tool registry + a few safe example tools."""
import ast
import inspect
import operator
from pathlib import Path

TOOLS = {}
SANDBOX = Path(__file__).resolve().parent.parent / "sandbox"


def tool(fn):
    """Register a function as a tool. Its signature becomes the arg schema."""
    TOOLS[fn.__name__] = fn
    return fn


def describe_tools():
    """One line per tool, fed to the model in the system prompt."""
    lines = []
    for name, fn in TOOLS.items():
        doc = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""
        lines.append(f"- {name}{inspect.signature(fn)}: {doc}")
    return "\n".join(lines)


def validate_args(name, args):
    """Return an error string if the call doesn't match the tool, else None."""
    if name not in TOOLS:
        return f"unknown tool '{name}'. available: {', '.join(TOOLS)}"
    if not isinstance(args, dict):
        return "args must be a JSON object"
    try:
        inspect.signature(TOOLS[name]).bind(**args)
    except TypeError as e:
        return f"bad args: {e}. expected {name}{inspect.signature(TOOLS[name])}"
    return None


# --- example tools -----------------------------------------------------------

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("only numbers and + - * / ** allowed")


@tool
def calculator(expr: str):
    """Evaluate arithmetic like '32 * 2.49 * 730'. No eval(), just math."""
    result = _eval(ast.parse(expr, mode="eval").body)
    return round(result, 4)


@tool
def read_file(path: str):
    """Read a text file from the sandbox/ directory."""
    p = (SANDBOX / path).resolve()
    if SANDBOX not in p.parents:
        raise PermissionError("path escapes the sandbox")
    return p.read_text()


_KB = {
    "h100 hourly rate": "H100 on-demand (example cloud): $2.49/hr",
    "hours per month": "~730 hours in an average month",
    "applied logic": "Applied Logic (a-l.studio) builds agents for businesses.",
}


@tool
def lookup(query: str):
    """Look up a fact in a tiny local knowledge base (no web)."""
    q = query.lower()
    hits = [v for k, v in _KB.items() if k in q or q in k]
    return hits[0] if hits else f"no entry for '{query}'. known: {', '.join(_KB)}"
