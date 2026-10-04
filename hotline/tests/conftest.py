import os

import pytest

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


@pytest.fixture
def db():
    """A connection inside a transaction that is always rolled back."""
    conn = hotline_db.connect()
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
