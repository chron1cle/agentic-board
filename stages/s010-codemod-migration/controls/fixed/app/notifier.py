"""Push user-visible notifications."""

from messenger.v2 import Client, Event


def notify(user_id, message, client=None):
    """Tell a user something. Raises DeliveryError if the broker refuses."""
    own = client is None
    client = client or Client()
    try:
        client.publish(Event(kind="user.notify",
                             body={"user": user_id, "text": message},
                             key=user_id))
        return True
    finally:
        if own:
            client.close()
