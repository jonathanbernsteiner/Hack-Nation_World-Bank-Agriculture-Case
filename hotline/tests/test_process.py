import contextlib
import os
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hotline import cli, config, db as hotline_db
from hotline.pipeline import process
from hotline.pipeline.run import RunResult
from hotline.routes import jobs

CALL = {
    "id": 1,
    "conversation_id": "conv-1",
    "farmer_id": 7,
    "identified_by": "pin",
    "received_at": datetime(2026, 10, 3, 22, 30, tzinfo=timezone.utc),  # 01:30 next day in Kampala
    "transcript_lines": [{"i": 0, "role": "farmer", "sw": "x"}],
    "tool_results": [],
    "processing_started_at": datetime(2026, 10, 4, tzinfo=timezone.utc),
    "is_synthetic": True,
}


def result(status="processed", consent="yes", entries=None):
    return RunResult([], "", {}, consent, entries if entries is not None else [{"kind": "sale"}], status)


class Refused(Exception):
    category = "cbrn"


Refused.__name__ = "TranslationRefused"


@pytest.fixture
def fake_db(monkeypatch):
    calls = {"saved": [], "finished": []}

    @contextlib.contextmanager
    def tx():
        yield "conn"

    monkeypatch.setattr(hotline_db, "transaction", tx)
    monkeypatch.setattr(process, "_claim", lambda conn, cid=None: dict(CALL))
    monkeypatch.setattr(process, "_save", lambda conn, call, res: calls["saved"].append(res) or True)
    monkeypatch.setattr(process, "_finish", lambda conn, call, *rest: calls["finished"].append(rest))
    return calls


def test_success_saves_and_uses_kampala_date(fake_db, monkeypatch):
    seen = {}

    def fake_run(lines, call_date, **kwargs):
        seen.update(call_date=call_date, **kwargs)
        return result()

    monkeypatch.setattr(process, "run_call", fake_run)
    assert process.process_call("conv-1") == "processed"
    assert seen["call_date"] == date(2026, 10, 4) and seen["identified_by"] == "pin"
    assert len(fake_db["saved"]) == 1 and fake_db["finished"] == []


def test_refusal_goes_to_needs_review(fake_db, monkeypatch):
    def boom(*a, **k):
        raise Refused("secret farmer words")

    monkeypatch.setattr(process, "run_call", boom)
    assert process.process_call("conv-1") == "needs_review"
    status, error = fake_db["finished"][0]
    assert status == "needs_review" and "secret" not in error


def test_generic_error_fails_with_class_name_only(fake_db, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("payload text " * 100)

    monkeypatch.setattr(process, "run_call", boom)
    assert process.process_call("conv-1") == "failed"
    status, error = fake_db["finished"][0]
    assert status == "failed" and error == "RuntimeError" and len(error) <= 500


def test_lost_claim_is_reported(fake_db, monkeypatch):
    monkeypatch.setattr(process, "run_call", lambda *a, **k: result())
    monkeypatch.setattr(process, "_save", lambda *a: False)
    assert process.process_call("conv-1") == "lost_claim"


def test_unclaimable_returns_current_status(monkeypatch):
    @contextlib.contextmanager
    def tx():
        class Conn:
            def execute(self, *a):
                return type("C", (), {"fetchone": lambda s: ("processed",)})()

        yield Conn()

    monkeypatch.setattr(hotline_db, "transaction", tx)
    monkeypatch.setattr(process, "_claim", lambda conn, cid=None: None)
    assert process.process_call("conv-1") == "processed"


def test_process_pending_runs_each_claim(fake_db, monkeypatch):
    queue = [dict(CALL, id=1), dict(CALL, id=2)]
    monkeypatch.setattr(process, "_claim", lambda conn, cid=None: queue.pop() if queue else None)
    monkeypatch.setattr(process, "run_call", lambda *a, **k: result())
    assert process.process_pending(5) == ["processed", "processed"]
    assert process.process_pending(5) == []


def test_claim_consumes_an_attempt_and_finish_does_not():
    # A run killed by maxDuration never reaches _finish; if only _finish counted attempts, the
    # sweeper would reclaim that stale call every 5 minutes forever (and pay Anthropic each time).
    claim_sql = " ".join(process._CLAIM_SQL.split())
    assert "attempts = c.attempts + 1" in claim_sql
    assert "attempts" not in process._FINISH_SQL


def test_entry_params_only_known_columns():
    params = process._entry_params(CALL, {"kind": "sale", "needs_review": True, "kg_per_unit": 3})
    assert params["call_id"] == 1 and params["farmer_id"] == 7 and params["kind"] == "sale"
    assert "needs_review" not in params and "kg_per_unit" not in params


class FakeConn:
    def __init__(self):
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(sql.split()[0] + " " + sql.split()[1])
        return type("C", (), {"fetchone": lambda s: (1,)})()


def test_save_consent_no_inserts_nothing():
    conn = FakeConn()
    assert process._save(conn, CALL, result(consent="no")) is True
    assert not any(s.startswith("insert") for s in conn.sql) and "delete from" in conn.sql


def test_save_deletes_before_insert():
    conn = FakeConn()
    process._save(conn, CALL, result())
    assert conn.sql.index("delete from") < conn.sql.index("insert into")


def test_cli_exit_codes(monkeypatch, capsys):
    monkeypatch.setattr(process, "process_call", lambda cid: "failed")
    monkeypatch.setattr(process, "process_pending", lambda limit: ["processed", "needs_review"])
    assert cli.main(["process", "conv-1"]) == 1
    assert cli.main(["process", "--pending"]) == 0
    with pytest.raises(SystemExit):
        cli.main(["process"])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "settings", config.settings.__class__(**{**config.settings.__dict__, "hotline_admin_secret": "adm"}))
    monkeypatch.setattr(process, "process_pending", lambda limit: ["processed"])
    monkeypatch.setattr(process, "process_call", lambda cid: "processed")
    app = FastAPI()
    app.include_router(jobs.router)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/api/jobs/process-pending", "/api/calls/c1/process"])
def test_jobs_require_admin_secret(client, path):
    assert client.post(path).status_code == 401
    assert client.post(path, headers={"X-Hotline-Admin-Secret": "bad"}).status_code == 401
    ok = client.post(path, headers={"X-Hotline-Admin-Secret": "adm"})
    assert ok.status_code == 200


@pytest.mark.supabase
def test_claim_semantics_on_real_db(db):
    farmer = db.execute(
        "insert into farmers (name, pin_hash, is_synthetic) values ('t', 'test-hash-64', true) returning id"
    ).fetchone()[0]

    def add(cid, status, attempts=0, started=None):
        db.execute(
            "insert into calls (conversation_id, farmer_id, status, attempts, processing_started_at, "
            "transcript_lines, tool_results) values (%s,%s,%s,%s,%s,'[]','[]')",
            (cid, farmer, status, attempts, started),
        )

    add("t-stale", "processing", started=datetime(2020, 1, 1, tzinfo=timezone.utc))
    add("t-exhausted", "failed", attempts=3)
    add("t-fresh", "processing", started=datetime.now(timezone.utc))
    assert process._claim(db, "t-exhausted") is None
    assert process._claim(db, "t-fresh") is None
    claimed = process._claim(db, "t-stale")
    assert claimed["is_synthetic"] is True
    attempts = db.execute("select attempts from calls where id = %s", (claimed["id"],)).fetchone()[0]
    assert attempts == 1  # the reclaim of a crashed run counts as an attempt
    assert process._save(db, claimed, result()) is True
    assert process._save(db, claimed, result()) is False  # claim consumed: a second save is refused
    db.execute("update calls set status = 'failed' where id = %s", (claimed["id"],))
    again = process._claim(db, "t-stale")
    assert process._save(db, again, result()) is True  # re-process: still one entry
    first = db.execute("select count(*) from entries where call_id = %s", (claimed["id"],)).fetchone()[0]
    assert first == 1
