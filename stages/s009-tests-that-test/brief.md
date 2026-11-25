`pricing.py` is correct and **must not be modified**. Write a test suite for it.

Put the tests in the `tests/` directory so this command passes from the project
root:

    python3 -m unittest discover -s tests -t . -q

Use `unittest` from the standard library. Cover `checkout`, `discount_rate` and
`line_total`.

Here is how this stage is actually scored, so you know what "good tests" means
here: after you finish, the grader makes **copies** of your workspace, injects a
small deliberate bug into `pricing.py` in each copy, and re-runs your test
command. Every injected bug your suite fails to catch counts against you. A
suite that asserts three happy-path totals will score near zero even though it
is green.

So write tests that would notice:

- the exact boundary where a tier discount starts to apply, and just below it
- which discount wins when a promo and a tier compete
- promo codes given in lower case, and codes that do not exist
- what `tax=False` changes, and the exact tax arithmetic
- the rounding rule at two decimal places
- the minimum-charge floor, including a basket that lands under it and one that
  lands just over it
- multi-line baskets, and an empty basket

Aim for one focused assertion per behaviour rather than one giant snapshot.
You need to catch at least 75% of the injected bugs.
