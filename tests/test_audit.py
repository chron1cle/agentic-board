"""The secret audit is the repo's only guardrail. Test the guardrail.

No fake credential appears literally in this file. The samples come from the
tool's own runtime-assembled corpus, for the same reason the tool assembles it
that way: a contiguous fake credential in a committed file is indistinguishable
from a real one to a push-protection scanner.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "tools" / "audit-secrets.py"


def _load():
    spec = importlib.util.spec_from_file_location("audit_secrets", SPEC_PATH)
    module = importlib.util.module_from_spec(spec)
    # dataclasses looks the module up in sys.modules while the class bodies run
    sys.modules["audit_secrets"] = module
    spec.loader.exec_module(module)
    return module


audit = _load()


def sample(rule_id: str) -> str:
    """A line that must trip `rule_id`, borrowed from the tool's own corpus."""
    return audit.SELF_TEST[rule_id][0]


class SelfTestTest(unittest.TestCase):
    def test_the_tools_own_self_test_passes(self):
        self.assertEqual(audit.self_test(), 0)

    def test_every_rule_has_a_sample(self):
        covered = set(audit.SELF_TEST)
        for rule in audit.RULES:
            self.assertIn(rule.rid, covered, f"{rule.rid} is untested")


class ScanContentTest(unittest.TestCase):
    def scan(self, text, name="a.py"):
        return audit.scan_content(ROOT / name, text, "worktree")

    def test_provider_tokens_are_found(self):
        for rule in ("github-token", "aws-access-key", "openai-key", "anthropic-key",
                     "slack-token", "npm-token", "gitlab-token"):
            hits = {f.rule for f in self.scan(sample(rule))}
            self.assertIn(rule, hits)

    def test_private_key_block_is_found(self):
        self.assertIn("private-key-block", {f.rule for f in self.scan(sample("private-key-block"))})

    def test_bearer_jwt_is_found(self):
        self.assertIn("jwt", {f.rule for f in self.scan(sample("jwt"))})

    def test_secret_assignment_is_found(self):
        self.assertTrue(self.scan(sample("generic-assignment")))

    def test_a_named_secret_file_is_flagged_by_name_alone(self):
        hits = self.scan("nothing inside", name="id_rsa")
        self.assertIn("ssh-key-file", {f.rule for f in hits})

    def test_prose_is_not_flagged(self):
        for line in audit.SELF_TEST_NEGATIVE:
            self.assertEqual(self.scan(line, name="docs.md"), [], line)

    def test_identifier_camel_case_is_not_flagged(self):
        """Long all-letter identifiers are not credentials; flagging them is noise."""
        self.assertEqual(self.scan("h = functools.partial(http.server.SimpleHTTPRequestHandler,"), [])

    def test_a_content_hash_is_not_flagged(self):
        digest = "f" * 3 + "0123456789abcdef0123456789abcdef0123"
        self.assertEqual(self.scan(f"image: repo@sha256:{digest}"), [])

    def test_placeholder_values_are_not_flagged(self):
        self.assertEqual(self.scan("OPENAI_API_KEY=your-key-here"), [])

    def test_redaction_hides_most_of_the_match(self):
        finding = self.scan(sample("github-token"))[0]
        self.assertNotIn(sample("github-token")[10:40], finding.redacted())

    def test_fingerprint_is_stable_and_path_scoped(self):
        line = sample("github-token")
        first = self.scan(line, name="a.py")[0].fingerprint
        again = self.scan(line, name="a.py")[0].fingerprint
        elsewhere = self.scan(line, name="b.py")[0].fingerprint
        self.assertEqual(first, again)
        self.assertNotEqual(first, elsewhere)

    def test_history_scan_does_not_raise_without_git(self):
        self.assertIsInstance(audit.scan_history(), list)


class AllowlistTest(unittest.TestCase):
    def test_allowlist_file_parses_comments_and_blanks(self):
        entries = audit.load_allowlist()
        self.assertIsInstance(entries, set)
        for entry in entries:
            self.assertIn(":", entry)


class RepoCleanTest(unittest.TestCase):
    def test_the_working_tree_has_no_unallowlisted_findings(self):
        allowed = audit.load_allowlist()
        findings = [f for f in audit.scan_worktree() if f.fingerprint not in allowed]
        self.assertEqual(
            [f.as_dict() for f in findings][:5], [],
            "the working tree contains findings; run python3 tools/audit-secrets.py")


if __name__ == "__main__":
    unittest.main()
