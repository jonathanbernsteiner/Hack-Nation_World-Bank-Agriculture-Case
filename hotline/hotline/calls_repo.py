"""Writes to the `calls` row that links a phone conversation to a farmer (spec section 6).
The key is conversation_id, so a caller cannot reset the PIN lock by changing call_sid.
The caller owns the connection and its transaction."""

from typing import Any

SOURCE_ELEVENLABS = "elevenlabs"
STATUS_IN_CALL = "in_call"

_UPSERT_IDENTITY_SQL = """
insert into calls (conversation_id, farmer_id, identified_by, status, is_synthetic, source)
values (%s, %s, %s, %s, %s, %s)
on conflict (conversation_id) do update
   set farmer_id = excluded.farmer_id,
       identified_by = excluded.identified_by,
       is_synthetic = excluded.is_synthetic
"""

# A late tool call must never move a received/processing/processed row back, so status is
# only set on insert; the update branch leaves it alone.

_BUMP_SQL = """
insert into calls (conversation_id, status, source, pin_attempts)
values (%s, %s, %s, 1)
on conflict (conversation_id) do update set pin_attempts = calls.pin_attempts + 1
returning pin_attempts
"""

_ATTEMPTS_SQL = "select pin_attempts from calls where conversation_id = %s"


def upsert_call_identity(
    conn: Any,
    conversation_id: str,
    *,
    farmer_id: int,
    identified_by: str,
    is_synthetic: bool,
) -> None:
    conn.execute(
        _UPSERT_IDENTITY_SQL,
        (conversation_id, farmer_id, identified_by, STATUS_IN_CALL, is_synthetic, SOURCE_ELEVENLABS),
    )


def pin_attempts(conn: Any, conversation_id: str) -> int:
    row = conn.execute(_ATTEMPTS_SQL, (conversation_id,)).fetchone()
    return int(row[0]) if row else 0


def bump_pin_attempts(conn: Any, conversation_id: str) -> int:
    """Count one failed PIN attempt (creating the call row if needed); returns the new total."""
    row = conn.execute(_BUMP_SQL, (conversation_id, STATUS_IN_CALL, SOURCE_ELEVENLABS)).fetchone()
    return int(row[0])
