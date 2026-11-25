"""Counting and paging helpers for the catalogue service."""


def page_count(total, per_page):
    """How many pages are needed to hold `total` items at `per_page` each."""
    return -(-total // per_page)


def page_items(items, page, per_page):
    """Items on 1-based `page`."""
    start = (page - 1) * per_page
    return items[start:start + per_page]


def top_n(items, n):
    """The `n` largest items, largest first. Fewer if there are not enough."""
    return sorted(items, reverse=True)[:n]


def running_totals(values):
    """Cumulative sums, one entry per input value."""
    out = []
    total = 0
    for value in values:
        total += value
        out.append(total)
    return out


def span_length(low, high):
    """How many integers are in the inclusive range low..high."""
    return high - low + 1
