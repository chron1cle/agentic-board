"""The viewer catalog should cover all shipped stages and expose only public metadata."""

import unittest

from engine.catalog import public_catalog
from engine.cli import DEFAULT_BOARD
from engine.harness import REGISTRY
from engine.spec import load_board

class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.board = load_board(DEFAULT_BOARD)
        self.catalog = public_catalog(self.board)

    def test_catalog_matches_the_board_and_adapter_registry(self):
        stages = self.catalog["board"]["stages"]
        self.assertEqual([row["id"] for row in stages], [stage.id for stage in self.board.stages])
        self.assertTrue(all(row["description"] and row["measurement"] for row in stages))
        self.assertEqual([(row["world"], row["level"]) for row in stages],
                         [(world, level) for world in (1, 2, 3) for level in range(1, 11)])
        self.assertEqual({row["id"] for row in self.catalog["connectors"]}, set(REGISTRY))

    def test_routing_tests_have_distinct_explanations_in_three_groups(self):
        routing = [row for row in self.catalog["board"]["stages"] if row["routingGroup"]]
        self.assertEqual(len(routing), 10)
        self.assertEqual(len({row["measurement"] for row in routing}), 10)
        self.assertEqual({row["routingGroup"] for row in routing}, {"gates", "prices", "signals"})

    def test_check_metadata_excludes_checker_paths_and_answers(self):
        for stage in self.catalog["board"]["stages"]:
            for check in stage["checks"]:
                self.assertLessEqual(
                    set(check), {"kind", "maxChangedLines", "minKillRate", "mutantCount"}
                )
        mutation_stage = next(row for row in self.catalog["board"]["stages"]
                              if row["id"] == "s009-tests-that-test")
        self.assertIn({"kind": "mutation", "minKillRate": 0.75, "mutantCount": 10},
                      mutation_stage["checks"])
