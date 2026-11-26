A failed upgrade left a pipeline with old checkpoints and partially processed
input. Repair pipeline.py, state.py, and checkpoint.py. Keep the public CLI
and use the standard library.

Run python3 pipeline.py DIR [--steps N]. DIR has events.jsonl and may have
state.json. Input is append-only JSON Lines with {id,revision,account,amount}.
Ids/accounts are strings, revisions are positive integers, and amount is an
integer or null. Equal revisions for an id are exact repeats. Keep each id's
highest revision, including null tombstones. Revisions may move an item to
another account. Totals sum active amounts per account, retaining zero totals
for accounts with active items and omitting accounts with none.

An old checkpoint has {"cursor":n,"items":{id:{revision,account,amount}}}.
A current one has {"version":2,"offset":n,"items":{...},"totals":{...}}.
Both offsets count input lines already committed, including ignored revisions.
With no checkpoint use offset zero and no items. Process the unread suffix.
Write current-format checkpoints atomically in DIR until done. Preserve the
input file. The current checkpoint must represent exactly its recorded prefix.
If --steps N is given and unread events remain after at most N more commits,
exit 75 with the last committed state. N=0 on an interrupted run preserves
the old file or its absence byte for byte. On completion exit zero, even on
already processed input. Identical completed runs produce identical bytes.
Print no output.
