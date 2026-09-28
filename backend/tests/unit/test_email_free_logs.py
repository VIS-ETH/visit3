import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}
EMAIL_NAMES = {"email", "username"}


def _names_in(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            names.add(child.attr)
        elif isinstance(child, ast.Name):
            names.add(child.id)
    return names


def _email_log_calls() -> list[str]:
    offenders: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if "generated" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in LOG_METHODS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "logger"
            ):
                continue
            arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
            if any(_names_in(argument) & EMAIL_NAMES for argument in arguments):
                offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno}")
    return offenders


def test_no_log_statement_writes_an_email_address():
    assert _email_log_calls() == []
