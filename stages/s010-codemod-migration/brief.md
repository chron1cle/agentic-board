Migrate this service from the deprecated `messenger.legacy.Bus` to
`messenger.v2`. The v2 SDK is already vendored in `messenger/v2.py`; read it,
it is short. The legacy module stays in the tree but **nothing may import it
when you are done**.

The migration changes semantics, not just names. Get these right:

**Config.** Replace `settings.ini` with `config.yaml` and delete the `.ini`
file. The keys are renamed: `bus.host` → `broker.host`, `bus.port` →
`broker.port`, and `bus.timeout` (seconds, float) → `broker.timeout_ms`
(**milliseconds, integer**). Keep `[app]` as `app.name` and `app.region`.
`settings.bus_settings()` must keep existing and return the dict
`{"broker_host", "broker_port", "timeout_ms"}` read from the YAML.

**Publishing.** `bus.send(kind, payload)` becomes `client.publish(Event(...))`.
`publish` returns `None` and **raises `DeliveryError` on failure** — there is no
`False` any more. Every event carries a `key` equal to the user id when there is
one, so ordering per user is preserved.

- `app.notifier.notify(user_id, message, client=None)` publishes
  `Event(kind="user.notify", body={"user": user_id, "text": message}, key=user_id)`
  and returns `True`.
- `app.billing.charge(user_id, cents, client=None)` publishes
  `Event(kind="billing.charge", body={"user": user_id, "cents": cents}, key=user_id)`.
- `app.ingest.ingest(records, client=None)` publishes one
  `Event(kind="ingest.record", body=record)` per record and returns how many
  were published.

All three must let `DeliveryError` reach the caller. Silently returning `False`
is the bug this migration exists to remove.

**Client ownership.** Each function takes an optional `client`. When it is
`None`, build one with `Client()` (which reads `config.yaml`). When a caller
passes one, use it and **do not close it** — the caller owns it. Functions that
create their own client must close it.

**Retry.** Rewrite `app.retry.with_retry(fn, attempts=3, delay=0.0)` for the new
semantics: call `fn`; if it raises `DeliveryError`, retry up to `attempts`
times; after the last failure **re-raise that error**. A success returns
whatever `fn` returned. `app.billing.charge` uses it, so a flaky broker is
retried three times and then the error propagates.

**Tests.** `tests/test_app.py` is written against the v1 bus and will not pass
after the migration. Rewrite it so
`python3 -m unittest discover -s tests -t . -q` passes against the new code, and
make it actually exercise the new behaviour: that events are `Event` objects with
the right `kind`, `body` and `key`; that a client passed in is used and left
open; that a `DeliveryError` propagates; that retry happens three times before
it does.

Constraints: standard library plus `PyYAML` only. No `import` of
`messenger.legacy` anywhere outside that file itself.
