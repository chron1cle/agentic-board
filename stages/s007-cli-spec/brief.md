Build `budget.py`, a personal budget CLI, in the project root. It keeps its
state in `ledger.json` in the **current working directory** and prints to stdout.
No third-party packages.

    python3 budget.py add 12.50 --note salary --date 2026-11-01
    python3 budget.py spend 4.75 --note coffee
    python3 budget.py balance
    python3 budget.py report --by month
    python3 budget.py report --by note

## Entries

An entry has an amount (money, two decimals), an optional note, and a date
(`YYYY-MM-DD`, defaulting to `2026-11-24`). `add` stores a positive amount,
`spend` stores the same magnitude as a negative amount. Amounts are exact:
`0.10 + 0.20` must print `0.30`, never `0.30000000000000004`. Store them so
that is true.

## Commands

- `add AMOUNT [--note TEXT] [--date D]` → appends and prints `added #N`, where
  `N` is the 1-based position of the new entry.
- `spend AMOUNT [--note TEXT] [--date D]` → same, stored negative.
- `balance` → prints `balance: X.XX` (two decimals, may be negative). With no
  ledger file at all, prints `balance: 0.00`.
- `report --by month` → one line per month, `YYYY-MM X.XX`, sorted by month
  ascending, only months that have entries.
- `report --by note` → one line per distinct note, `NOTE X.XX`, sorted by amount
  descending, then by note ascending. Entries with no note are grouped under the
  literal note `(none)`.

## Errors

Bad input must exit with code **2** and print a line starting `error: ` to
**stderr** (nothing on stdout): a non-numeric amount, an amount with more than
two decimals, a negative or zero amount, a malformed `--date`, an unknown
subcommand, or a missing amount.

If `ledger.json` exists but is not readable as a valid ledger, exit with code
**3** and print `error: ledger unreadable` to stderr.

## State file

`ledger.json` is a JSON object with one key `entries`, a list of objects each
having `amount` (string, two decimals), `note` (string or null) and `date`.
Other tools may read it, so keep those keys exactly.
