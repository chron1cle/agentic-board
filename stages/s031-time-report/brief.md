Implement report.py using the standard library. Each stdin line is a separate
JSON object with events and queries. Write one JSON array per line. For example,
{"events":[],"queries":[[0,"2030-01-01"]]} produces [{"count":0,"sum":0}].

An event has a string id, positive integer revision, ISO 8601 timestamp with
an explicit UTC offset, and integer or null value. A query [prefix, day] asks
what was known after the first prefix events arrived (0 through len(events)).
For each id, use the greatest revision received by then. Tied revisions of
an id are exact repeats. A null value deletes the id until a higher revision
restores it. A correction may change its UTC calendar day.

Return {"count":n,"sum":total} for the requested UTC day for each query,
in the original query order, including duplicates. Missing days have count
and sum zero. Up to 20,000 events and 20,000 queries per line. The report
must handle many different prefixes without replaying the whole prefix
for each query.
