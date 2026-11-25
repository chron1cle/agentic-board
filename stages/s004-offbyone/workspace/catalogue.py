"""Counting and paging helpers for the catalogue service.

Several of these are wrong by one. The intended behaviour is written in
SPEC.md next to this file; the code is what someone actually shipped.
"""


def page_count(total, per_page):
    """How many pages are needed to hold `total` items at `per_page` each."""
    return total // per_page


def page_items(items, page, per_page):
    """Items on 1-based `page`."""
    start = page * per_page
    return items[start:start + per_page]


def top_n(items, n):
    """The `n` largest items, largest first. Fewer if there are not enough."""
    return sorted(items, reverse=True)[:n + 1]


def running_totals(values):
    """Cumulative sums, one entry per input value."""
    out = []
    total = 0
    for value in values[:-1]:
        total += value
        out.append(total)
    return out


def span_length(low, high):
    """How many integers are in the inclusive range low..high."""
    return high - low
