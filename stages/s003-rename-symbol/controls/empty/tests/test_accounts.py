import unittest

from billing import fetch_user
from billing.accounts import describe
from billing.reports import invoice_header, invoice_lines

DB = {
    "u1": {"name": "Dana", "email": "dana@example.com"},
    "u2": {"name": "Priya", "email": "priya@example.com"},
}


class AccountTest(unittest.TestCase):
    def test_fetch_returns_row(self):
        row = fetch_user(DB, "u1")
        self.assertEqual(row["name"], "Dana")
        self.assertEqual(row["fetched_at"], "2026-11-24T00:00:00Z")

    def test_fetch_unknown(self):
        with self.assertRaises(KeyError):
            fetch_user(DB, "nope")

    def test_describe(self):
        self.assertEqual(describe(DB, "u2"), "Priya <priya@example.com>")

    def test_invoice_header(self):
        self.assertEqual(invoice_header(DB, "u1"), "Invoice for Dana (dana@example.com)")

    def test_invoice_total(self):
        text = invoice_lines(DB, "u1", [(2, 5), (1, 10)])
        self.assertIn("total 20", text)


if __name__ == "__main__":
    unittest.main()
