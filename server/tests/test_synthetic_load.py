"""Offline tests for the synthetic loader (#44): a fake connection records the SQL."""

import hashlib
from contextlib import contextmanager

import pytest

from synthetic import supabase as loader
from synthetic.__main__ import main
from synthetic.generate import generate_season

SALT = "test-salt-not-real"
SECRET = "test-admin-secret"


class FakeCursor:
    def __init__(self, row=(0,), rowcount=0):
        self.row, self.rowcount = row, rowcount

    def fetchone(self):
        return self.row


class FakeConn:
    """Records every statement; keeps per-table row counts so reset+load can be checked."""

    def __init__(self, blockers=0, tables=None):
        self.sql, self.params = [], []
        self.blockers = blockers
        self.tables = dict(tables or {"villages": 0, "farmers": 0, "calls": 0, "entries": 0})
        self.in_tx = False
        self.next_id = 0

    @contextmanager
    def transaction(self):
        self.in_tx = True
        try:
            yield
        finally:
            self.in_tx = False

    def execute(self, sql, params=()):
        assert self.in_tx or sql.startswith("select count"), "write outside a transaction"
        self.sql.append(sql)
        self.params.append(params)
        if sql.startswith("select count(*) from"):
            return FakeCursor((self.blockers,))
        if sql.startswith("percentile") or "percentile_cont" in sql:
            return FakeCursor((5900.0, 28, 5))
        if sql.startswith("delete from"):
            table = sql.split()[2]
            removed, self.tables[table] = self.tables[table], 0
            return FakeCursor(rowcount=removed)
        if sql.startswith("insert into"):
            self.tables[sql.split()[2]] += 1
            self.next_id += 1
            return FakeCursor((self.next_id,))
        raise AssertionError(sql)

    def writes(self):
        return [s for s in self.sql if s.startswith(("insert", "delete"))]


def _fp(salt):
    return hashlib.sha256(salt.encode()).hexdigest()[:8]


def test_salt_gate_passes_on_match():
    assert loader.check_salt_gate(SALT, SECRET, fetch=lambda _s: _fp(SALT)) == _fp(SALT)


def test_salt_gate_aborts_on_mismatch():
    with pytest.raises(loader.SaltGateError, match="mismatch") as info:
        loader.check_salt_gate(SALT, SECRET, fetch=lambda _s: "00000000")
    assert SALT not in str(info.value) and SECRET not in str(info.value)


def test_salt_gate_aborts_when_unreachable():
    def unreachable(_secret):
        raise loader.SaltGateError("production health check unreachable (URLError)")

    with pytest.raises(loader.SaltGateError, match="unreachable"):
        loader.check_salt_gate(SALT, SECRET, fetch=unreachable)


def test_fetch_wraps_network_errors(monkeypatch):
    def boom(*_a, **_k):
        raise OSError("down")

    monkeypatch.setattr(loader.urllib.request, "urlopen", boom)
    with pytest.raises(loader.SaltGateError, match="unreachable"):
        loader.fetch_production_fingerprint(SECRET)


@pytest.mark.parametrize("salt,secret", [(None, SECRET), ("", SECRET), (SALT, None)])
def test_salt_gate_aborts_when_salt_unset(salt, secret):
    with pytest.raises(loader.SaltGateError, match="not set"):
        loader.check_salt_gate(salt, secret, fetch=lambda _s: pytest.fail("must not fetch"))


def test_cli_writes_nothing_when_gate_fails(monkeypatch):
    monkeypatch.setenv("LEDGER_PIN_SALT", SALT)
    monkeypatch.setenv("HOTLINE_ADMIN_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example.test/postgres")
    monkeypatch.setattr(loader, "fetch_production_fingerprint", lambda _s: "00000000")
    monkeypatch.setattr("synthetic.__main__._connect", lambda _u: pytest.fail("connected before gate"))
    assert main(["--reset"]) == 1


def test_reset_deletes_only_synthetic_in_order():
    conn = FakeConn(tables={"villages": 6, "farmers": 21, "calls": 313, "entries": 313})
    with conn.transaction():
        deleted = loader.reset_synthetic(conn)
    deletes = [s for s in conn.sql if s.startswith("delete")]
    assert [s.split()[2] for s in deletes] == ["entries", "calls", "farmers", "villages"]
    assert all("is_synthetic" in s for s in deletes)
    assert deleted == {"villages": 6, "farmers": 21, "calls": 313, "entries": 313}


def test_reset_refuses_when_real_row_references_synthetic():
    conn = FakeConn(blockers=2)
    with conn.transaction(), pytest.raises(loader.ResetRefused):
        loader.reset_synthetic(conn)
    assert conn.writes() == []


def test_load_inserts_villages_before_farmers():
    conn = FakeConn()
    season = generate_season()
    counts = loader.run_load(conn, SALT, reset=False, season=season)["inserted"]
    order = [s.split()[2] for s in conn.writes()]
    assert order.index("farmers") > max(i for i, t in enumerate(order) if t == "villages")
    assert order.index("calls") > max(i for i, t in enumerate(order) if t == "farmers")
    assert counts == {"villages": 6, "farmers": 21, "calls": 313, "entries": 313}
    assert conn.tables == counts


def test_load_rows_are_synthetic_uganda():
    conn = FakeConn()
    loader.run_load(conn, SALT, reset=False)
    call_params = [p for s, p in zip(conn.sql, conn.params) if s.startswith("insert into calls")]
    assert all(p[5:9] == ("synthetic", "processed", "pin", "yes") for p in call_params)
    cols = loader.ENTRY_COLUMNS
    entry_params = [p[2:] for s, p in zip(conn.sql, conn.params) if s.startswith("insert into entries")]
    assert {p[cols.index("currency")] for p in entry_params} - {None} == {"UGX"}
    sales = [p for p in entry_params if p[cols.index("kind")] == "sale"]
    assert sales and all(p[cols.index("coffee_form")] for p in sales)


def test_load_is_idempotent_with_reset():
    conn = FakeConn()
    season = generate_season()
    first = loader.run_load(conn, SALT, reset=True, season=season)
    second = loader.run_load(conn, SALT, reset=True, season=season)
    assert conn.tables == first["inserted"] == second["inserted"]
    assert second["deleted"] == first["inserted"]


def test_pin_hash_matches_hotline_formula():
    assert loader.hash_pin(SALT, "9001") == hashlib.sha256(f"{SALT}:9001".encode()).hexdigest()
    conn = FakeConn()
    loader.run_load(conn, SALT, reset=False)
    hashes = [p[1] for s, p in zip(conn.sql, conn.params) if s.startswith("insert into farmers")]
    assert loader.hash_pin(SALT, "9001") in hashes and len(set(hashes)) == 21


@pytest.mark.parametrize("url,expected", [
    ("postgresql://u:p@aws-0-eu-west-1.pooler.supabase.com:5432/postgres", True),
    ("postgresql://u:p@db.abcd.supabase.co:5432/postgres", True),
    ("postgresql://u:p@localhost:5432/postgres", False),
    (None, False),
])
def test_is_production_database(url, expected):
    assert loader.is_production_database(url) is expected


def test_skip_salt_check_refused_for_production_host(monkeypatch):
    monkeypatch.setenv("LEDGER_PIN_SALT", SALT)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@aws-0-eu-west-1.pooler.supabase.com:5432/postgres")
    monkeypatch.setattr("synthetic.__main__._connect", lambda _u: pytest.fail("connected"))
    assert main(["--skip-salt-check"]) == 1


def test_dry_run_prints_counts_and_needs_no_env(capsys, monkeypatch):
    for name in ("LEDGER_PIN_SALT", "DATABASE_URL", "HOTLINE_ADMIN_SECRET"):
        monkeypatch.delenv(name, raising=False)
    assert main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "villages=6, farmers=21, calls=313, entries=313" in out and "UGX" in out
