"""External acceptance checks: preserved data, mixed versions, failed upgrade."""
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import app


def seed(path, balance=1739):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE accounts (id TEXT PRIMARY KEY, balance_cents INTEGER NOT NULL)')
        db.execute('INSERT INTO accounts VALUES (?, ?)', ('existing', balance))
        db.execute('PRAGMA user_version = 1')


with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / 'ledger.sqlite')
    seed(path)
    app.start(path)
    assert app.account(path, 'existing') == {'balance_cents': 1739, 'currency': 'USD'}
    assert app.account(path, 'absent') is None
    with sqlite3.connect(path) as old_client:
        assert old_client.execute('PRAGMA user_version').fetchone()[0] == 2
        # An old application must continue using its existing write/read contract.
        old_client.execute('INSERT INTO accounts (id, balance_cents) VALUES (?, ?)', ('old-writer', 4281))
        old_client.execute('UPDATE accounts SET balance_cents = ? WHERE id = ?', (1801, 'existing'))
        assert old_client.execute('SELECT balance_cents FROM accounts WHERE id = ?', ('existing',)).fetchone() == (1801,)
    assert app.account(path, 'old-writer') == {'balance_cents': 4281, 'currency': 'USD'}
    with sqlite3.connect(path) as new_client:
        new_client.execute('INSERT INTO accounts VALUES (?, ?, ?)', ('euro', 915, 'EUR'))
    app.start(path)
    app.start(path)
    assert app.account(path, 'existing') == {'balance_cents': 1801, 'currency': 'USD'}
    assert app.account(path, 'euro') == {'balance_cents': 915, 'currency': 'EUR'}

    invalid = str(Path(directory) / 'invalid.sqlite')
    seed(invalid, -5)
    with sqlite3.connect(invalid) as db:
        before = list(db.iterdump())
    try:
        app.start(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('Negative legacy balances must reject migration')
    with sqlite3.connect(invalid) as db:
        assert list(db.iterdump()) == before, 'Failed migration changed schema or rows'
        assert db.execute('PRAGMA user_version').fetchone()[0] == 1
print('Upgrade preserves persisted data, old writers, repeated startup and failed-upgrade state.')
