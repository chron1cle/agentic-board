"""A fixture git will not hand over is a fixture that does not exist.

`*.log` is in .gitignore for tool noise, and it silently swallowed the log files
that stages s005 and s006 are built on: the board validated on the author's
machine and was unplayable from a clone. This test is that lesson, enforced.
"""

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def git(*args):
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


class FixturesAreTrackedTest(unittest.TestCase):
    def setUp(self):
        if not (REPO / ".git").exists():
            self.skipTest("not a git checkout")

    def test_nothing_under_stages_is_hidden_by_gitignore(self):
        code, out = git("ls-files", "-o", "-i", "--exclude-standard", "stages/")
        self.assertEqual(code, 0)
        hidden = [line for line in out.splitlines() if "__pycache__" not in line]
        self.assertEqual(
            hidden, [],
            "these stage files exist on disk but .gitignore hides them, so a fresh "
            f"clone cannot play them: {hidden}")

    def test_every_stage_ships_its_files_in_git(self):
        """Not just un-ignored: actually committed, workspace and oracle included."""
        code, tracked = git("ls-files", "stages/")
        self.assertEqual(code, 0)
        tracked = set(tracked.splitlines())
        for stage_yaml in sorted((REPO / "stages").glob("*/stage.yaml")):
            stage = stage_yaml.parent.name
            for part in ("workspace", "oracle", "controls"):
                on_disk = {str(p.relative_to(REPO))
                           for p in (REPO / "stages" / stage / part).rglob("*")
                           if p.is_file() and "__pycache__" not in p.parts}
                missing = sorted(on_disk - tracked)
                self.assertEqual(missing, [], f"{stage}/{part}: not committed: {missing}")


if __name__ == "__main__":
    unittest.main()
