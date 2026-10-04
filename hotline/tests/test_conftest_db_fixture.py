"""Regression tests for the `db` fixture in conftest.py (spec §12: rolled back, never committed).

The offline tests drive the fixture with a fake connection that follows the psycopg 3 rules
the fixture depends on. The `supabase` tests check the same promise against the live database
in a way that does not depend on test order.
"""

import ast
import uuid
from contextlib import contextmanager, suppress
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from psycopg import sql
from psycopg.pq import TransactionStatus

from hotline import config, main
from hotline import db as hotline_db

FRESH_TIMEOUT_SECS = 5
TABLE_EXISTS = "select count(*) from information_schema.tables where table_schema = 'public' and table_name = %s"
PACKAGE_DIR = Path(__file__).resolve().parents[1] / "hotline"
PATCHED_DB_NAMES = {"connect", "transaction", "*"}
VILLAGE_COUNT = "select count(*) from public.villages where village = %s"
INSERT_VILLAGE = """insert into public.villages (region, district, sub_county, parish, village, is_synthetic)
                    values ('Central', 'Masaka', 'T76', 'T76', %s, true)"""
REMOVE_PROBE_VILLAGE = "delete from public.villages where village = %s and village like 'rollback_probe_%%'"


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


def test_with_connect_block_from_main_works_and_neither_commits_nor_closes(fake_conn, db):
    # main._db_status() uses `with db.connect() as conn:`; psycopg's own __exit__ commits and closes.
    with hotline_db.connect() as conn:
        conn.execute("select 2")
    assert "commit" not in fake_conn.calls
    assert "close" not in fake_conn.calls
    assert main._db_status() == "ok"


def test_commit_from_code_under_test_does_not_commit_the_fixture_transaction(fake_conn, db):
    with suppress(Exception):
        hotline_db.connect().commit()
    assert "commit" not in fake_conn.calls


def test_rollback_from_code_under_test_cannot_turn_the_next_block_into_a_commit(fake_conn, db):
    with suppress(Exception):
        hotline_db.connect().rollback()
    with hotline_db.transaction() as conn:
        conn.execute("insert probe")
    assert "begin" not in fake_conn.calls
    assert "commit" not in fake_conn.calls


def test_transaction_block_on_the_handed_out_connection_is_a_savepoint(checked_fake_conn, db):
    # The psycopg idiom `with conn.transaction():` on the connection from hotline.db.connect().
    with hotline_db.connect() as conn, conn.transaction():
        conn.execute("insert probe")
    assert "savepoint" in checked_fake_conn.calls


def test_rollback_then_transaction_on_the_handed_out_connection_cannot_commit(fake_conn, db):
    # rollback() leaves the connection idle, so conn.transaction() (forwarded by the proxy) would be
    # an outermost block that COMMITS. Same rule as the hotline.db.transaction() case above.
    conn = hotline_db.connect()
    conn.rollback()
    with conn.transaction():
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


def _temp_table_exists(conn, name: str) -> bool:
    return conn.execute("select to_regclass(%s)", (f"pg_temp.{name}",)).fetchone()[0] is not None


@pytest.fixture
def temp_probe():
    """A session-local temp table name: even if the fixture commits, nothing reaches other sessions,
    and the table disappears when the fixture closes its connection. Only a commit survives rollback()."""
    return f"rollback_probe_{uuid.uuid4().hex}"


@pytest.mark.supabase
def test_with_connect_commit_and_exit_never_commit_live(temp_probe, db):
    with hotline_db.connect() as conn:
        conn.execute(sql.SQL("create temp table {} (x int)").format(sql.Identifier(temp_probe)))
        conn.commit()
    assert _temp_table_exists(db, temp_probe)
    db.rollback()
    assert not _temp_table_exists(db, temp_probe), "the db fixture committed"


@pytest.mark.supabase
def test_rollback_then_transaction_on_the_handed_out_connection_never_commits_live(temp_probe, db):
    conn = hotline_db.connect()
    conn.rollback()
    with conn.transaction():
        conn.execute(sql.SQL("create temp table {} (x int)").format(sql.Identifier(temp_probe)))
    conn.rollback()
    assert not _temp_table_exists(conn, temp_probe), "the db fixture committed"


@pytest.mark.supabase
def test_db_error_inside_connect_block_does_not_poison_the_shared_transaction(db):
    with pytest.raises(Exception):
        with hotline_db.connect() as conn:
            conn.execute("select * from table_that_does_not_exist_76")
    with hotline_db.transaction() as conn:
        assert conn.execute("select 1").fetchone()[0] == 1


# --- Regression tests from review cycle 3 (#76). ---


def _fixture_bypasses(path: Path) -> list[str]:
    """Ways to reach the database that the fixture's monkeypatch of hotline.db attributes cannot see."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
            from_db = node.module == "hotline.db" or (node.level > 0 and node.module == "db")
            if from_db and names & PATCHED_DB_NAMES:
                found.append(f"{path.name}:{node.lineno} from-imports {sorted(names & PATCHED_DB_NAMES)}")
            if node.module == "psycopg" and node.level == 0 and names & {"connect", "*"}:
                found.append(f"{path.name}:{node.lineno} from-imports psycopg.connect")
        elif isinstance(node, ast.Attribute) and node.attr == "connect":
            if isinstance(node.value, ast.Name) and node.value.id == "psycopg":
                found.append(f"{path.name}:{node.lineno} calls psycopg.connect")
    return found


def test_no_hotline_module_can_bypass_the_db_fixture():
    # `from hotline.db import transaction` binds the real function at import time, so the fixture's
    # monkeypatch never reaches it and a RUN_SUPABASE test would COMMIT to the live database.
    sources = [p for p in PACKAGE_DIR.rglob("*.py") if p != PACKAGE_DIR / "db.py"]
    assert sources, PACKAGE_DIR
    bypasses = [hit for path in sources for hit in _fixture_bypasses(path)]
    assert not bypasses, f"use `from hotline import db` and call db.connect()/db.transaction(): {bypasses}"


def test_every_supabase_test_runs_inside_the_db_fixture(request):
    # Spec §12: database tests always run inside the rolled-back fixture. A supabase test without `db`
    # reaches the real hotline.db and commits whatever the code under test writes.
    unguarded = [
        item.nodeid
        for item in request.session.items
        if item.get_closest_marker("supabase") and "db" not in getattr(item, "fixturenames", ())
    ]
    assert not unguarded, f"request the `db` fixture in: {unguarded}"


@pytest.mark.supabase
def test_failing_hotline_db_transaction_keeps_rows_the_test_seeded_live(temp_probe, db):
    # Route tests seed rows through `db`, then call code that fails inside hotline.db.transaction().
    # Only that block may roll back (a savepoint), as its own connection would in production.
    table = sql.Identifier(temp_probe)
    db.execute(sql.SQL("create temp table {} (x int)").format(table))
    db.execute(sql.SQL("insert into {} values (1)").format(table))
    with pytest.raises(psycopg.errors.UndefinedTable), hotline_db.transaction() as conn:
        conn.execute(sql.SQL("insert into {} values (2)").format(table))
        conn.execute("select * from table_that_does_not_exist_76")
    assert db.execute(sql.SQL("select x from {} order by x").format(table)).fetchall() == [(1,)]


@pytest.fixture
def village_guard():
    """Request before `db`: after the fixture's rollback, a fresh connection must not see the
    village. If a commit leaked it, remove that one probe row again and fail."""
    village = f"rollback_probe_{uuid.uuid4().hex}"
    yield village
    with _fresh_connection() as fresh:
        leaked = fresh.execute(VILLAGE_COUNT, (village,)).fetchone()[0]
        if leaked:
            fresh.execute(REMOVE_PROBE_VILLAGE, (village,))
    assert not leaked, "the db fixture committed a village to the live database"


@pytest.mark.supabase
def test_synthetic_village_written_through_hotline_db_is_gone_after_teardown(village_guard, db):
    # The acceptance criterion of #76, now that public.villages exists in the live database.
    with hotline_db.transaction() as conn:
        conn.execute(INSERT_VILLAGE, (village_guard,))
    assert db.execute(VILLAGE_COUNT, (village_guard,)).fetchone()[0] == 1
    with _fresh_connection() as fresh:
        assert fresh.execute(VILLAGE_COUNT, (village_guard,)).fetchone()[0] == 0
