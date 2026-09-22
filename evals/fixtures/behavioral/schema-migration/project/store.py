"""SQLite ledger used by old and new application versions during deployment."""
import sqlite3


def migrate(path):
    """Upgrade an existing v1 ledger; currently the deployment forgets migration."""
    return None


def read_account(path, account_id):
    with sqlite3.connect(path) as db:
        row = db.execute(
            'SELECT balance_cents, currency FROM accounts WHERE id = ?',
            (account_id,),
        ).fetchone()
    return None if row is None else {'balance_cents': row[0], 'currency': row[1]}
