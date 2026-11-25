"""Stage and board loading."""

import tempfile
import unittest
from pathlib import Path

from engine.scoring import stage_value
from engine.spec import Board, SpecError, load_board, load_stage

ROOT = Path(__file__).resolve().parent.parent
BOARDS = ROOT / "boards"
STAGES = ROOT / "stages"


class StageLoadingTest(unittest.TestCase):
    def test_every_board_stage_loads(self):
        board = load_board(BOARDS / "v1.yaml")
        self.assertEqual(len(board.stages), 10)
        self.assertEqual([s.tier for s in board.stages], [1, 1, 2, 2, 2, 3, 3, 4, 5, 6])

    def test_stage_paths_are_absolute(self):
        """Oracles run with a different cwd; a relative path would miss them."""
        for stage in load_board(BOARDS / "v1.yaml").stages:
            self.assertTrue(stage.path.is_absolute())
            self.assertTrue(stage.oracle_dir.is_absolute())

    def test_every_stage_has_both_controls(self):
        for stage in load_board(BOARDS / "v1.yaml").stages:
            self.assertTrue((stage.path / "controls" / "fixed").is_dir(), stage.id)
            self.assertTrue((stage.path / "controls" / "empty").is_dir(), stage.id)

    def test_stage_value_rises_with_tier(self):
        self.assertEqual(load_stage(STAGES / "s001-exact-edit" / "stage.yaml").value(), 100)
        self.assertEqual(load_stage(STAGES / "s010-codemod-migration" / "stage.yaml").value(), 350)
        self.assertEqual(stage_value(4), 250)

    def test_brief_is_loaded_from_file(self):
        stage = load_stage(STAGES / "s001-exact-edit" / "stage.yaml")
        self.assertIn("2026-11-24", stage.brief)

    def test_missing_stage_raises(self):
        with self.assertRaises(SpecError):
            load_stage(STAGES / "no-such-stage" / "stage.yaml")

    def test_unknown_oracle_kind_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stage.yaml"
            path.write_text("id: x\nbrief: hi\noracles:\n  - kind: vibes\n")
            with self.assertRaises(SpecError) as ctx:
                load_stage(path)
            self.assertIn("unknown oracle kind", str(ctx.exception))

    def test_stage_without_oracles_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stage.yaml"
            (Path(tmp) / "workspace").mkdir()
            path.write_text("id: x\nbrief: hi\noracles: []\n")
            with self.assertRaises(SpecError) as ctx:
                load_stage(path)
            self.assertIn("no oracles", str(ctx.exception))

    def test_missing_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stage.yaml"
            path.write_text("id: x\nbrief: hi\noracles:\n  - kind: command\n    cmd: true\n")
            with self.assertRaises(SpecError) as ctx:
                load_stage(path)
            self.assertIn("workspace", str(ctx.exception))

    def test_bad_reveal_level_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stage.yaml"
            (Path(tmp) / "workspace").mkdir()
            path.write_text("id: x\nbrief: hi\noracles:\n  - kind: command\n"
                            "    cmd: true\n    reveal: everything\n")
            with self.assertRaises(SpecError):
                load_stage(path)

    def test_mutation_oracle_needs_its_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stage.yaml"
            (Path(tmp) / "workspace").mkdir()
            path.write_text("id: x\nbrief: hi\noracles:\n  - kind: mutation\n")
            with self.assertRaises(SpecError) as ctx:
                load_stage(path)
            self.assertIn("mutation", str(ctx.exception))

    def test_board_with_unknown_stage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "board.yaml"
            path.write_text("id: b\nstages:\n  - not-a-stage\n")
            with self.assertRaises(SpecError):
                load_board(path)

    def test_board_is_a_board(self):
        board = load_board(BOARDS / "smoke.yaml")
        self.assertIsInstance(board, Board)
        self.assertEqual(board.size, 1)
        self.assertEqual(len({s.id for s in board.stages}), board.size)


if __name__ == "__main__":
    unittest.main()
