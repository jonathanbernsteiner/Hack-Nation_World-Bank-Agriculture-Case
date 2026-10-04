"""The `db` fixture must roll back writes made through hotline.db.transaction() (spec §12).

Uses a uniquely named probe table created inside the transaction (Postgres DDL is
transactional), so the test does not depend on which migrations the live DB has applied.
"""

import uuid

import psycopg
import pytest

from hotline import config
from hotline import db as hotline_db

pytestmark = pytest.mark.supabase

PROBE = f"rollback_probe_{uuid.uuid4().hex}"
ROW_COUNT = "select count(*) from information_schema.tables where table_name = %s"


def _probe_table_count(conn) -> int:
    return conn.execute(ROW_COUNT, (PROBE,)).fetchone()[0]


def test_write_through_hotline_db_transaction_is_visible_inside_the_test(db):
    with hotline_db.transaction() as conn:
        conn.execute(f"create table public.{PROBE} (name text)")
        conn.execute(f"insert into public.{PROBE} values ('synthetic village')")
    assert db.execute(f"select count(*) from public.{PROBE}").fetchone()[0] == 1


def test_write_is_gone_on_a_fresh_connection_after_the_fixture_tears_down():
    # Runs after the test above: its fixture has torn down, so only a commit could leave a trace.
    with psycopg.connect(config.settings.database_url, prepare_threshold=None) as fresh:
        assert _probe_table_count(fresh) == 0
