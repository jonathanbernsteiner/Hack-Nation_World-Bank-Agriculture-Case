"""The `db` fixture must roll back writes made through hotline.db.transaction() (spec §12).

Uses a uniquely named probe table created inside the transaction (Postgres DDL is
transactional), so the test does not depend on which migrations the live DB has applied.
"""

import uuid

import pytest

from hotline import db as hotline_db

pytestmark = pytest.mark.supabase

PROBE = f"rollback_probe_{uuid.uuid4().hex}"


def test_write_through_hotline_db_transaction_is_visible_inside_the_test(db):
    with hotline_db.transaction() as conn:
        conn.execute(f"create table public.{PROBE} (name text)")
        conn.execute(f"insert into public.{PROBE} values ('synthetic village')")
    assert db.execute(f"select count(*) from public.{PROBE}").fetchone()[0] == 1
