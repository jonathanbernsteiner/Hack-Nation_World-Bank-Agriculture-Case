"""FastAPI app. Includes every router from day one so later leaves never edit this file."""

from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query

from hotline import db, pins, security
from hotline.routes import demo, farmer, jobs, webhooks
from hotline.routes.tools import find, identify, register, weather

app = FastAPI(title="Hotline", docs_url=None, redoc_url=None)

for _module in (identify, find, register, weather, webhooks, jobs, demo, farmer):
    app.include_router(_module.router)


def _db_status() -> str:
    try:
        with db.connect() as conn:
            conn.execute("select 1")
        return "ok"
    except Exception:
        return "error"


@app.get("/api/health")
def health(
    deep: Annotated[int, Query()] = 0,
    x_hotline_admin_secret: Annotated[str | None, Header()] = None,
) -> dict:
    if not deep:
        return {"status": "ok"}
    if not security.is_admin_secret(x_hotline_admin_secret):
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"status": "ok", "db": _db_status(), "salt_fp": pins.salt_fingerprint()}
