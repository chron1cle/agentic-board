"""Charge a customer through the bus."""

from app.retry import with_retry
from messenger.v2 import Client, Event


def charge(user_id, cents, client=None):
    own = client is None
    client = client or Client()
    try:
        with_retry(lambda: client.publish(Event(kind="billing.charge",
                                                 body={"user": user_id, "cents": cents},
                                                 key=user_id)))
        return True
    finally:
        if own:
            client.close()
