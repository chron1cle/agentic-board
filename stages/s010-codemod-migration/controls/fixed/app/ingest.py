"""Bulk ingest of raw records onto the bus."""

from messenger.v2 import Client, Event


def ingest(records, client=None):
    """Publish every record, return how many were published. Raises on failure."""
    own = client is None
    client = client or Client()
    published = 0
    try:
        for record in records:
            client.publish(Event(kind="ingest.record", body=record))
            published += 1
        return published
    finally:
        if own:
            client.close()
