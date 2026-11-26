The intake service and dispatch worker exchange orders with a local simulated
gateway. Incident reports say customer totals drift after retries, and
a permanent rejection is retried. Debug the existing modules and preserve
their named functions. Use only the standard library.

app.py reads JSON Lines. Each request has messages, max_attempts (positive
integer), and responses. A message has string id, string customer, and integer
amount. Process messages in input order and take only the first occurrence
of each id, even when its delivery fails. For each unique message the gateway
returns its next outcome from responses[id] or ok if the list is exhausted.
Retry only retry, up to max_attempts calls total per message. Stop immediately
on ok or reject. Add successful messages to delivered (ids in input order) and
sum their amounts by customer. List other messages in undelivered with id and
reason rejected or exhausted. Output {delivered,undelivered,totals,calls},
where calls is each gateway call's id in order, including retries.
