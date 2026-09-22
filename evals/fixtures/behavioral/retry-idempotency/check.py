"""External checks exercise real persisted effects through the delivery entrypoint."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import sys
import tempfile
from pathlib import Path
from threading import Barrier

sys.path.insert(0, sys.argv[1])
import app


def state(path):
    with sqlite3.connect(path) as db:
        return (db.execute('SELECT * FROM accounts ORDER BY id').fetchall(),
                db.execute('SELECT * FROM deliveries ORDER BY event_id').fetchall())


with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / 'payments.sqlite')
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE accounts (id TEXT PRIMARY KEY, balance_cents INTEGER NOT NULL)')
        db.executemany('INSERT INTO accounts VALUES (?, ?)', [('alice', 1700), ('bob', 200)])
        db.execute('CREATE TABLE deliveries (event_id TEXT PRIMARY KEY, source TEXT, destination TEXT, cents INTEGER)')
    before = state(path)
    try:
        app.deliver(path, 'retry', 'alice', 'bob', 319, fail_after_debit=True)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Failure injection must still execute')
    assert state(path) == before, 'Debit and delivery must roll back together'
    assert app.deliver(path, 'retry', 'alice', 'bob', 319) is True
    applied = state(path)
    assert applied[0] == [('alice', 1381), ('bob', 519)]
    assert applied[1] == [('retry', 'alice', 'bob', 319)]
    assert app.deliver(path, 'retry', 'alice', 'bob', 319) is False
    assert state(path) == applied
    for source, destination, cents in [('alice', 'bob', 320), ('bob', 'alice', 319)]:
        try:
            app.deliver(path, 'retry', source, destination, cents)
        except ValueError:
            pass
        else:
            raise AssertionError('Reused event ID with different payload must fail')
        assert state(path) == applied

    barrier = Barrier(2)

    def concurrent_delivery(_):
        barrier.wait(timeout=5)
        return app.deliver(path, 'concurrent', 'bob', 'alice', 73)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(concurrent_delivery, range(2))) == [False, True]
    final = state(path)
    assert final[0] == [('alice', 1454), ('bob', 446)]
    assert len(final[1]) == 2
print('Failure rolls back; retries and concurrent duplicate delivery apply exactly once.')
