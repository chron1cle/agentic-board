"""Checkout pricing for the store.

This module is correct. Your job is not to fix it — your job is to prove that
any future change to it is either intended or caught.
"""

TIER_THRESHOLDS = [(500, 0.10), (200, 0.05), (100, 0.02)]
PROMOS = {"SPRING": 0.15, "VIP": 0.25}
MIN_CHARGE = 1
TAX_RATE = 0.08


def discount_rate(subtotal, promo=None):
    """Best of the tier discount and the promo code. They do not stack."""
    rate = 0.0
    for threshold, value in TIER_THRESHOLDS:
        if subtotal > threshold:
            rate = max(rate, value)
            break
    if promo:
        rate = max(rate, PROMOS.get(promo.upper(), 0.0))
    return rate


def line_total(unit_price, quantity):
    """What one line costs before discounts."""
    return unit_price * quantity


def checkout(items, promo=None, tax=True):
    """Total for a basket. `items` is a list of (unit_price, quantity) pairs."""
    subtotal = sum(line_total(price, qty) for price, qty in items)
    rate = discount_rate(subtotal, promo)
    total = subtotal * (1 - rate)
    if tax:
        total *= (1 + TAX_RATE)
    total = round(total, 2)
    if total < MIN_CHARGE:
        total = MIN_CHARGE
    return total
