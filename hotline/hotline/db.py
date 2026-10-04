"""Short-lived psycopg 3 connections. prepare_threshold=None keeps the Supabase
transaction pooler (port 6543) happy. The URL is never logged or put in errors."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from hotline import config

CONNECT_TIMEOUT_SECS = 5


def connect() -> psycopg.Connection:
    url = config.settings.database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(
        url,
        prepare_threshold=None,
        connect_timeout=CONNECT_TIMEOUT_SECS,
        autocommit=False,
    )


@contextmanager
def transaction() -> Iterator[psycopg.Connection]:
    """Open a connection; commit on success, roll back on error, always close."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
