Repair pipeline.py, state.py and checkpoint.py. Run python3 pipeline.py DIR
[--steps N] using only the standard library. Multiple clients share an
append-only UTF-8 events.jsonl journal. An optional base.txt integer counts
lines compacted from its front (default 0). Offsets are absolute line counts.

An old state.json has {"cursor":n,"items":{...}} or
{"version":2,"offset":n,"items":{...},"totals":{...}}. Both imply no open
transactions and zero rejected commits. With no checkpoint start at offset
zero with empty items. A current checkpoint has exactly version (3), offset,
items, totals, open, rejected. Each item is {"revision":r,"account":a,"amount":v}.
The open object maps transaction ids to ordered lists of staged write records,
including each record's op and tx fields. Rejected is a cumulative count.

Read the uncommitted suffix. Each complete line is one of:
* {"op":"begin","tx":t} opens an empty transaction.
* {"op":"write","tx":t,"id":k,"expect":r,"account":a,"amount":v} stages a
  write. Amount is integer or null. It stays invisible until commit.
* {"op":"abort","tx":t} discards the staged writes.
* {"op":"commit","tx":t} applies all staged writes in order to the currently
  committed items. For each write, the current revision must equal expect
  (zero for a missing id). On a match set revision to expect+1, account to a
  and amount to v. A later write in this transaction sees the earlier write.
  If any precondition fails, discard the entire transaction and increment
  rejected once. Aborts and successful commits do not increment it.

Different transactions may interleave. Closed transaction ids may be reused.
Begin/write/close records are well-formed. A null amount is a tombstone that
retains its revision. Totals sum active items by account, include zero for
accounts with active items and omit empty accounts.

Atomically replace state.json after each consumed line. Preserve inputs and
write temporary files in DIR. A trailing fragment without a newline has
not been published yet, even if it looks like valid JSON. Stop before it and
exit 75. Also exit 75 if N additional lines have been consumed and more input
remains. Stopping before consuming anything preserves the checkpoint bytes
or absence. With no unread input, exit 0 and ensure a current checkpoint
exists. Repeating a completed run must preserve its bytes. If the checkpoint
offset falls outside [base, base + number of complete lines], exit 2 and
preserve the checkpoint. Produce no stdout in any case.
