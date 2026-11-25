"""Invoice rendering. Uses the account lookup."""

from billing.accounts import fetch_user


def invoice_header(db, user_id):
    account = fetch_user(db, user_id)
    return f"Invoice for {account['name']} ({account['email']})"


def invoice_lines(db, user_id, items):
    header = invoice_header(db, user_id)
    body = [f"  {qty} x {price}" for qty, price in items]
    total = sum(qty * price for qty, price in items)
    return "\n".join([header] + body + [f"total {total}"])
