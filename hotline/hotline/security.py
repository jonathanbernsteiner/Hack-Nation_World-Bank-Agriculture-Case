"""Request authentication shared by every route. All checks fail closed: an unset
server secret rejects every request. Secrets are read at call time and never put
in exceptions or logs."""

import hashlib
import hmac
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from hotline import config

SIGNATURE_TOLERANCE_S = 1800

_basic = HTTPBasic(auto_error=False)


def _secrets_match(provided: str | None, expected: str | None) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


def _unauthorized(headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(status_code=401, detail="unauthorized", headers=headers)


def is_tool_secret(provided: str | None) -> bool:
    return _secrets_match(provided, config.settings.hotline_tool_secret)


def is_admin_secret(provided: str | None) -> bool:
    return _secrets_match(provided, config.settings.hotline_admin_secret)


def require_tool_secret(x_hotline_tool_secret: Annotated[str | None, Header()] = None) -> None:
    if not is_tool_secret(x_hotline_tool_secret):
        raise _unauthorized()


def require_admin_secret(x_hotline_admin_secret: Annotated[str | None, Header()] = None) -> None:
    if not is_admin_secret(x_hotline_admin_secret):
        raise _unauthorized()


def require_demo_basic_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
) -> None:
    expected_user = config.settings.demo_user
    expected_password = config.settings.demo_password
    if credentials is None or not expected_user or not expected_password:
        raise _unauthorized({"WWW-Authenticate": "Basic"})
    # Evaluate both comparisons so timing does not reveal which one failed.
    user_ok = _secrets_match(credentials.username, expected_user)
    password_ok = _secrets_match(credentials.password, expected_password)
    if not (user_ok and password_ok):
        raise _unauthorized({"WWW-Authenticate": "Basic"})


def _parse_signature_header(header: str) -> tuple[int, str] | None:
    fields: dict[str, str] = {}
    for part in header.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            return None
        fields[key] = value
    try:
        return int(fields["t"]), fields["v0"]
    except (KeyError, ValueError):
        return None


def verify_elevenlabs_signature(
    raw_body: bytes,
    header: str | None,
    secret: str | None,
    now: float | None = None,
    tolerance_s: int = SIGNATURE_TOLERANCE_S,
) -> bool:
    """Check `ElevenLabs-Signature: t=<ts>,v0=<hex>` over the raw request bytes.
    Never raises: any malformed input returns False."""
    if not secret or not header:
        return False
    parsed = _parse_signature_header(header)
    if parsed is None:
        return False
    timestamp, provided = parsed
    current = time.time() if now is None else now
    try:
        if abs(current - timestamp) > tolerance_s:
            return False
    except OverflowError:  # absurdly large t cannot be within tolerance
        return False
    signed = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided.encode(), expected.encode())
