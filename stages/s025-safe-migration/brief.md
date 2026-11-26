Implement migrate.py DIR [--interrupt N]. DIR contains legacy.json, a JSON
object mapping names to integers. The migration writes one compact JSON
object {"name":name,"value":integer} per line into current.jsonl, in sorted
name order. Preserve legacy.json byte for byte. All temporary files must live
inside DIR. Import is idempotent and an already valid destination can be
rebuilt with identical bytes.

To simulate interruption, exit 75 just before committing current.jsonl after
preparing N records, where 0 <= N <= the input count. Until a successful
commit the destination must stay byte-identical, or absent if it was absent.
Retrying without --interrupt must succeed even if temporary files remain.
Print no output. Use Python's standard library.
