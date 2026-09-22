"""Local SQLite transfers; delivery may retry after a process failure."""
import sqlite3


def transfer(path, event_id, source, destination, cents, fail_after_debit=False):
    with sqlite3.connect(path) as db:
        db.execute('UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?', (cents, source))
        db.commit()
        if fail_after_debit:
            raise RuntimeError('simulated failure after debit')
        db.execute('UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?', (cents, destination))
        db.execute('INSERT INTO deliveries VALUES (?, ?, ?, ?)', (event_id, source, destination, cents))
    return True
