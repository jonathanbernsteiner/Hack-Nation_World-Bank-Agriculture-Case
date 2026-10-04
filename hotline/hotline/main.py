"""FastAPI app. Includes every router from day one so later leaves never edit this file."""

import hashlib
import hmac
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query

from hotline import config, db
from hotline.routes import demo, jobs, webhooks
from hotline.routes.tools import find, identify, register, weather

SALT_FP_LENGTH = 8

app = FastAPI(title="Hotline", docs_url=None, redoc_url=None)

for _module in (identify, find, register, weather, webhooks, jobs, demo):
    app.include_router(_module.router)


def _is_admin(provided: str | None) -> bool:
    expected = config.settings.hotline_admin_secret
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


def _db_status() -> str:
    try:
        with db.connect() as conn:
            conn.execute("select 1")
        return "ok"
    except Exception:
        return "error"


def _salt_fp() -> str | None:
    salt = config.settings.ledger_pin_salt
    if not salt:
        return None
    return hashlib.sha256(salt.encode()).hexdigest()[:SALT_FP_LENGTH]


@app.get("/api/health")
def health(
    deep: Annotated[int, Query()] = 0,
    x_hotline_admin_secret: Annotated[str | None, Header()] = None,
) -> dict:
    if not deep:
        return {"status": "ok"}
    if not _is_admin(x_hotline_admin_secret):
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"status": "ok", "db": _db_status(), "salt_fp": _salt_fp()}
