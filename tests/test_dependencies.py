"""The engine's dependency surface is one package wide, and that is a feature.

A benchmark that changes behaviour when a transitive dependency updates is not a
benchmark. `sys.stdlib_module_names` makes this check exact rather than a list
someone has to remember to maintain.
"""

import ast
import sys
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / "engine"
ALLOWED_THIRD_PARTY = {"yaml"}


def imported_modules():
    """Every top-level module imported anywhere under engine/, with its file."""
    found = []
    for path in sorted(ENGINE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] if node.level == 0 else []
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                if top and top not in sys.stdlib_module_names and top != "engine":
                    found.append((top, path.name))
    return found


class DependencySurfaceTest(unittest.TestCase):
    def test_only_yaml_is_not_standard_library(self):
        unexpected = sorted(set(imported_modules()) - {("yaml", "spec.py")})
        self.assertEqual(
            unexpected, [],
            f"new third-party import in the engine: {unexpected}. If it is really "
            f"needed, add it to requirements.txt and to ALLOWED_THIRD_PARTY here, "
            f"and say why in the commit message.")

    def test_requirements_txt_lists_exactly_what_is_imported(self):
        text = (ENGINE.parent / "requirements.txt").read_text(encoding="utf-8")
        lines = [l.strip().lower() for l in text.splitlines()
                 if l.strip() and not l.startswith("#")]
        self.assertEqual([l.split(">")[0].split("=")[0].strip() for l in lines],
                         ["pyyaml"])


if __name__ == "__main__":
    unittest.main()
