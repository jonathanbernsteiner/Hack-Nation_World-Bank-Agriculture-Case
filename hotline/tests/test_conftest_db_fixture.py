"""Regression tests for the `db` fixture in conftest.py (spec §12: rolled back, never committed).

The offline tests drive the fixture with a fake connection that follows the psycopg 3 rules
the fixture depends on. The `supabase` tests check the same promise against the live database
in a way that does not depend on test order.
"""

import uuid
from contextlib import contextmanager, suppress
from types import SimpleNamespace

import psycopg
import pytest
from psycopg import sql
from psycopg.pq import TransactionStatus

from hotline import config, main
from hotline import db as hotline_db

FRESH_TIMEOUT_SECS = 5
TABLE_EXISTS = "select count(*) from information_schema.tables where table_schema = 'public' and table_name = %s"


class FakeConnection:
    """psycopg 3 rules: execute() opens a transaction when idle; commit()/rollback() end it;
    transaction() is a savepoint inside an open transaction, but on an idle connection it is
    an outermost block that COMMITS on exit; `with conn:` commits and closes on exit."""

    def __init__(self):
        self.calls: list[str] = []
        self.info = SimpleNamespace(transaction_status=TransactionStatus.IDLE)

    def _set(self, status):
        self.info.transaction_status = status

    def execute(self, query, params=None):
        self.calls.append(f"execute {query}")
        if self.info.transaction_status == TransactionStatus.IDLE:
            self._set(TransactionStatus.INTRANS)

    def commit(self):
        self.calls.append("commit")
        self._set(TransactionStatus.IDLE)

    def rollback(self):
        self.calls.append("rollback")
        self._set(TransactionStatus.IDLE)

    def close(self):
        self.calls.append("close")

    @contextmanager
    def transaction(self):
        if self.info.transaction_status != TransactionStatus.IDLE:
            self.calls.append("savepoint")
            try:
                yield
            except BaseException:
                self.calls.append("rollback to savepoint")
                raise
            self.calls.append("release savepoint")
            return
        self.calls.append("begin")
        self._set(TransactionStatus.INTRANS)
        try:
            yield
        except BaseException:
            self.rollback()
            raise
        self.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


@pytest.fixture
def fake_conn(monkeypatch):
    """Must be requested before `db` so the fixture opens this fake instead of a real connection."""
    conn = FakeConnection()
    monkeypatch.setattr(hotline_db, "connect", lambda: conn)
    return conn


@pytest.fixture
def checked_fake_conn(fake_conn):
    """Like fake_conn, and after `db` tears down: never committed, rolled back, closed once."""
    yield fake_conn
    assert "commit" not in fake_conn.calls
    assert "begin" not in fake_conn.calls
    assert fake_conn.calls[-2:] == ["rollback", "close"]
    assert fake_conn.calls.count("close") == 1


def test_outer_transaction_is_open_before_the_first_savepoint(checked_fake_conn, db):
    with hotline_db.transaction() as conn:
        assert conn is db
        conn.execute("insert probe")
    assert checked_fake_conn.calls == ["execute select 1", "savepoint", "execute insert probe", "release savepoint"]


def test_failing_block_rolls_back_to_its_savepoint_and_the_next_block_is_still_a_savepoint(checked_fake_conn, db):
    with pytest.raises(ValueError), hotline_db.transaction():
        raise ValueError("boom")
    with hotline_db.transaction() as conn:
        conn.execute("insert probe")
    assert checked_fake_conn.calls.count("savepoint") == 2
    assert "rollback to savepoint" in checked_fake_conn.calls


def test_close_from_code_under_test_does_not_close_the_fixture_connection(checked_fake_conn, db):
    hotline_db.connect().close()
    assert "close" not in checked_fake_conn.calls


@pytest.mark.xfail(strict=True, raises=TypeError, reason="PR #78 review finding 1: proxy has no __enter__/__exit__")
def test_with_connect_block_from_main_works_and_neither_commits_nor_closes(fake_conn, db):
    # main._db_status() uses `with db.connect() as conn:`; psycopg's own __exit__ commits and closes.
    with hotline_db.connect() as conn:
        conn.execute("select 2")
    assert "commit" not in fake_conn.calls
    assert "close" not in fake_conn.calls
    assert main._db_status() == "ok"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="PR #78 review finding 2: proxy forwards commit()")
def test_commit_from_code_under_test_does_not_commit_the_fixture_transaction(fake_conn, db):
    with suppress(Exception):
        hotline_db.connect().commit()
    assert "commit" not in fake_conn.calls


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="PR #78 review finding 2: idle conn makes block outermost")
def test_rollback_from_code_under_test_cannot_turn_the_next_block_into_a_commit(fake_conn, db):
    with suppress(Exception):
        hotline_db.connect().rollback()
    with hotline_db.transaction() as conn:
        conn.execute("insert probe")
    assert "begin" not in fake_conn.calls
    assert "commit" not in fake_conn.calls


def _fresh_connection() -> psycopg.Connection:
    return psycopg.connect(
        config.settings.database_url,
        prepare_threshold=None,
        autocommit=True,
        connect_timeout=FRESH_TIMEOUT_SECS,
    )


def _table_exists(conn, name: str) -> bool:
    return conn.execute(TABLE_EXISTS, (name,)).fetchone()[0] > 0


@pytest.fixture
def leak_guard():
    """Request before `db`: its teardown runs after the fixture's rollback, checks on a fresh
    connection that the probe table is gone, and drops it if a commit leaked it."""
    probe = f"rollback_probe_{uuid.uuid4().hex}"
    yield probe
    with _fresh_connection() as fresh:
        leaked = _table_exists(fresh, probe)
        if leaked:
            fresh.execute(sql.SQL("drop table if exists public.{}").format(sql.Identifier(probe)))
    assert not leaked, "the db fixture committed a write to the live database"


@pytest.mark.supabase
def test_writes_through_hotline_db_are_never_visible_outside_the_fixture(leak_guard, db):
    table = sql.Identifier(leak_guard)
    with hotline_db.transaction() as conn:
        conn.execute(sql.SQL("create table public.{} (name text)").format(table))
        conn.execute(sql.SQL("insert into public.{} values ('synthetic village')").format(table))
    with pytest.raises(psycopg.errors.UndefinedColumn), hotline_db.transaction() as conn:
        conn.execute(sql.SQL("insert into public.{} (missing) values (1)").format(table))
    with hotline_db.transaction() as conn:
        conn.execute(sql.SQL("insert into public.{} values ('second village')").format(table))
    assert db.execute(sql.SQL("select count(*) from public.{}").format(table)).fetchone()[0] == 2
    with _fresh_connection() as fresh:
        assert not _table_exists(fresh, leak_guard)
