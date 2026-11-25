"""Account lookups for the billing service."""

from .clock import now_iso


def fetch_user(db, user_id):
    """Return the account row for ``user_id``.

    Raises KeyError when the account does not exist.
    """
    if user_id not in db:
        raise KeyError(f"no account {user_id!r}")
    row = dict(db[user_id])
    row["fetched_at"] = now_iso()
    return row


def describe(db, user_id):
    row = fetch_user(db, user_id)
    return f"{row['name']} <{row['email']}>"
