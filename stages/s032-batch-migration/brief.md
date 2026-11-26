Implement migrate.py DIR [--interrupt N] with the Python standard library.
Read legacy.json, a UTF-8 JSON object mapping names to integers. An optional
batches.json contains a list of batches. Each batch is a list of [from,to]
pairs that simultaneously rename keys while preserving their values.

Every source must exist at the start of its batch. Sources and destinations
must each be unique within the batch. An occupied destination is legal only
if it is also a source in that batch. Swaps, longer cycles, self-renames,
and empty batches are legal. Apply batches in order. For example, swapping
a and b in one batch permits a later batch to move the new value of a.

Validate all batches first. Any violation exits 2 even with --interrupt.
On success publish current.jsonl in sorted name order, one compact JSON
object per line with keys name then value and a trailing newline. Use ASCII
JSON escaping. With --interrupt N, exit 75 after preparing N output rows and
before publishing, even for N=0 or the full row count. N is in range.

Every unsuccessful run preserves the previous destination byte for byte,
or leaves it absent. Publish the completed file by atomic replacement.
Inputs are immutable, temporary files belong in DIR, retries must succeed,
and stdout stays empty for all outcomes.
