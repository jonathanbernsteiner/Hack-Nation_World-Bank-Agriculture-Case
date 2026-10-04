import os
from contextlib import contextmanager

import pytest
from psycopg.pq import TransactionStatus

from hotline import db as hotline_db


def pytest_configure(config):
    config.addinivalue_line("markers", "supabase: needs the real Supabase database (RUN_SUPABASE=1)")
    config.addinivalue_line("markers", "live: calls live Anthropic/ElevenLabs APIs (RUN_LIVE=1)")


def pytest_collection_modifyitems(config, items):
    gates = {"supabase": "RUN_SUPABASE", "live": "RUN_LIVE"}
    for item in items:
        for marker, env_name in gates.items():
            if marker in item.keywords and os.environ.get(env_name) != "1":
                item.add_marker(pytest.mark.skip(reason=f"set {env_name}=1 to run"))


class _NoCloseConnection:
    """Proxy for the fixture connection: close() is a no-op so code under test cannot end it."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def commit(self):
        pass  # the fixture owns the outer transaction; only teardown ends it, with a rollback

    # Python looks dunders up on the class, so __getattr__ cannot supply them. Do not delegate to
    # psycopg's __exit__: it commits and closes.
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture
def db(monkeypatch):
    """One connection inside a transaction that is always rolled back (never committed).

    hotline.db.connect() and hotline.db.transaction() are patched to hand out this same
    connection, so code under test that opens its own connection also rolls back.
    """
    conn = hotline_db.connect()
    # psycopg 3 only makes conn.transaction() a savepoint when a transaction is already open;
    # otherwise it would start and COMMIT its own. Open the outer transaction first.
    conn.execute("select 1")
    shared = _NoCloseConnection(conn)

    @contextmanager
    def rolled_back_transaction():
        # Code under test may have called rollback(), leaving the connection idle; a block would
        # then be outermost and commit. Re-open the outer transaction first.
        if conn.info.transaction_status == TransactionStatus.IDLE:
            conn.execute("select 1")
        with conn.transaction():  # a savepoint inside the outer transaction
            yield shared

    monkeypatch.setattr(hotline_db, "connect", lambda: shared)
    monkeypatch.setattr(hotline_db, "transaction", rolled_back_transaction)
    try:
        yield shared
    finally:
        conn.rollback()
        conn.close()
