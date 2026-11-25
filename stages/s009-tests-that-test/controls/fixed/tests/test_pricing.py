"""Reference test suite for the mutation-scored stage."""

import unittest

from pricing import checkout, discount_rate, line_total


class LineTotalTest(unittest.TestCase):
    def test_multiplies(self):
        self.assertEqual(line_total(2, 3), 6)

    def test_zero_quantity(self):
        self.assertEqual(line_total(9.99, 0), 0)


class DiscountRateTest(unittest.TestCase):
    def test_below_first_tier(self):
        self.assertEqual(discount_rate(100), 0.0)

    def test_just_over_first_tier(self):
        self.assertAlmostEqual(discount_rate(100.01), 0.02)

    def test_middle_tier(self):
        self.assertAlmostEqual(discount_rate(250), 0.05)

    def test_top_tier_boundary(self):
        self.assertEqual(discount_rate(500), 0.05)

    def test_above_top_tier(self):
        self.assertAlmostEqual(discount_rate(500.01), 0.10)

    def test_promo_beats_tier(self):
        self.assertAlmostEqual(discount_rate(150, "VIP"), 0.25)

    def test_tier_survives_unknown_promo(self):
        self.assertAlmostEqual(discount_rate(600, "NOPE"), 0.10)

    def test_promo_is_case_insensitive(self):
        self.assertAlmostEqual(discount_rate(0, "spring"), 0.15)

    def test_unknown_promo_ignored(self):
        self.assertEqual(discount_rate(0, "NOPE"), 0.0)


class CheckoutTest(unittest.TestCase):
    def test_no_discount_with_tax(self):
        self.assertEqual(checkout([(100, 1)]), 108.0)

    def test_tax_can_be_disabled(self):
        self.assertEqual(checkout([(100, 1)], tax=False), 100.0)

    def test_tier_applies_over_boundary(self):
        self.assertEqual(checkout([(100.01, 1)]), 105.85)

    def test_multi_line_basket(self):
        self.assertEqual(checkout([(50, 10)]), 513.0)

    def test_top_tier(self):
        self.assertEqual(checkout([(500.01, 1)]), 486.01)

    def test_promo_case_insensitive_end_to_end(self):
        self.assertEqual(checkout([(100, 1)], promo="vip"), 81.0)

    def test_unknown_promo_is_no_op(self):
        self.assertEqual(checkout([(100, 1)], promo="NOPE"), 108.0)

    def test_rounds_to_two_decimals(self):
        self.assertEqual(checkout([(33.33, 1)]), 36.0)

    def test_minimum_charge_floor(self):
        self.assertEqual(checkout([(0.5, 1)], tax=False), 1)

    def test_just_over_minimum_charge(self):
        self.assertEqual(checkout([(1.5, 1)], tax=False), 1.5)

    def test_empty_basket_hits_floor(self):
        self.assertEqual(checkout([]), 1)


if __name__ == "__main__":
    unittest.main()
