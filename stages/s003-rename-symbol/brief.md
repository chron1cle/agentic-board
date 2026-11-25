Renames are only finished when the last caller is updated.

The `billing` package looks accounts up with a function called `fetch_user`.
The team decided the domain word is *account*, not *user*, so the public name
must become `get_account`.

Rename it everywhere it appears in this project: the definition, the package
exports, every caller, and the tests.

Two constraints that matter:

- **No compatibility shim.** Do not leave `fetch_user = get_account` behind, and
  do not keep the old name in `__all__`. The old name must be gone.
- **The test suite must still pass:**
  `python3 -m unittest discover -s tests -t . -q`

Do not change what any function does, and do not rename anything else.
