Implement report.py as a JSON Lines program. Input is an array of records
{id, revision, timestamp, value}. id is a string, revision is a positive
integer, value is an integer or null, and timestamp is an ISO 8601 timestamp
with an explicit UTC offset. Per id keep only its greatest revision. Highest
revisions tied for an id are exact duplicates. A null value deletes that id.
Bucket surviving values by UTC calendar day. Output an object mapping YYYY-MM-DD
to {"count": integer, "sum": integer}. Days with no surviving events are absent.
Events can arrive in any order, and a correction can move an event to another
day. Standard library only.
