`config/app.json` was hand-edited and is no longer valid JSON. Repair it so that
`python3 -c "import json;json.load(open('config/app.json'))"` succeeds.

The repaired file must carry exactly this configuration and nothing more:

| key            | value                              |
| -------------- | ---------------------------------- |
| `name`         | `"ledger"`                         |
| `version`      | `"2.1.0"`                          |
| `port`         | `8080` (a number, not a string)    |
| `features`     | `["retry", "metrics", "tracing"]`  |
| `retry_budget` | `30` (a number, not a string)      |

JSON has no comments, so the explanatory comment has to go. Keep the file small:
do not add keys, and do not reformat the parts that are already correct.
