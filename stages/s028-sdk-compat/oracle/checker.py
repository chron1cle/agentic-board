import ast
from pathlib import Path
from support import batch, emit, rng

try:
    modules = {name: ast.parse(Path(f"{name}.py").read_text())
               for name in ("app", "reader", "aggregate")}
except (OSError, SyntaxError, UnicodeError):
    emit("public-api", False, "unreadable application module")
    raise SystemExit(0)

emit("legacy-imports-removed", not any(
    isinstance(node, ast.ImportFrom) and node.module == "sensor_legacy"
    or isinstance(node, ast.Import) and any(alias.name == "sensor_legacy" for alias in node.names)
    for tree in modules.values() for node in ast.walk(tree)
))
for module, name, arguments in [
    ("reader", "collect", ["sensor", "key"]),
    ("aggregate", "report", ["sensor", "keys"]),
]:
    functions = [node for node in modules[module].body
                 if isinstance(node, ast.FunctionDef) and node.name == name]
    emit(f"public-{name}", bool(functions)
         and [arg.arg for arg in functions[0].args.args] == arguments)
random = rng()
cases = []
for i in range(25):
    value = random.randint(-100, 100)
    records = {"a": [value, "whole"], "b": [i, "milli"], "c": "offline", "d": [1, "unknown"]}
    keys = ["missing", "a", "a", "d", "c", "b", "b"]
    random.shuffle(keys)
    rows = {"missing": {"status": "missing"}, "a": {"status": "ok", "milli": value * 1000},
            "b": {"status": "ok", "milli": i}, "c": {"status": "offline"}, "d": {"status": "invalid"}}
    cases.append((f"migration-contract-{i}", {"records": records, "keys": keys},
                  {"rows": [dict(rows[key], id=key) for key in keys],
                   "total_milli": 2000 * value + 2 * i, "calls": keys}))
batch("app.py", cases)
