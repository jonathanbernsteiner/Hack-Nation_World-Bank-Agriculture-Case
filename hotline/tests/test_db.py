"""Regression tests for hotline.db: pooler-safe connect() and transaction() semantics."""

import dataclasses

import pytest

from hotline import config, db

FAKE_URL = "postgresql://user:hunter2@pooler.example:6543/postgres"


def patch_settings(monkeypatch, **overrides):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, **overrides))


class FakeConnection:
    def __init__(self):
        self.calls: list[str] = []

    def commit(self):
        self.calls.append("commit")

    def rollback(self):
        self.calls.append("rollback")

    def close(self):
        self.calls.append("close")


def test_connect_disables_prepared_statements_and_sets_timeout(monkeypatch):
    patch_settings(monkeypatch, database_url=FAKE_URL)
    captured = {}

    def fake_connect(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeConnection()

    monkeypatch.setattr(db.psycopg, "connect", fake_connect)
    db.connect()
    assert captured["url"] == FAKE_URL
    # The Supabase transaction pooler (port 6543) breaks on server-side prepared statements.
    assert "prepare_threshold" in captured and captured["prepare_threshold"] is None
    assert 0 < captured["connect_timeout"] <= 10
    assert captured["autocommit"] is False


def test_connect_without_database_url_raises_without_leaking(monkeypatch):
    patch_settings(monkeypatch, database_url=None)
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        db.connect()


def test_transaction_commits_and_closes_on_success(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda: conn)
    with db.transaction() as yielded:
        assert yielded is conn
    assert conn.calls == ["commit", "close"]


def test_transaction_rolls_back_and_closes_on_error(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda: conn)
    with pytest.raises(ValueError), db.transaction():
        raise ValueError("boom")
    assert conn.calls == ["rollback", "close"]
