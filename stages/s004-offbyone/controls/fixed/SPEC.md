# catalogue.py — intended behaviour

`page_count(total, per_page)`
: Number of pages needed to hold `total` items at `per_page` per page, rounding
**up**. `page_count(0, 10) == 0`, `page_count(10, 10) == 1`,
`page_count(11, 10) == 2`.

`page_items(items, page, per_page)`
: The slice of `items` belonging to page `page`, where pages are **1-based**.
`page_items([1..25], 1, 10) == [1..10]` and `page_items([1..25], 3, 10) == [21..25]`.
An out-of-range page returns `[]`.

`top_n(items, n)`
: The `n` largest items, largest first, and **exactly** `n` of them when there
are that many. `top_n([3, 1, 2], 2) == [3, 2]`. `top_n([], 3) == []`.

`running_totals(values)`
: Cumulative sums with **one output per input**.
`running_totals([1, 2, 3]) == [1, 3, 6]` and `running_totals([]) == []`.

`span_length(low, high)`
: How many integers lie in the inclusive range `low..high`.
`span_length(1, 1) == 1`, `span_length(0, 10) == 11`.

Fix the functions so they match this document. Do not rename them, do not change
their signatures, and do not add dependencies.
