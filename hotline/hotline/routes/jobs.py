"""Admin-only processing endpoints (docs/hotline-spec.md section 7). The work runs inside the
request (at most 5 calls, maxDuration 300), so it does not depend on post-response execution."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from hotline import security
from hotline.pipeline import process

router = APIRouter(dependencies=[Depends(security.require_admin_secret)])

MAX_PENDING_LIMIT = 5


@router.post("/api/jobs/process-pending")
async def process_pending(
    limit: Annotated[int, Query(ge=1, le=MAX_PENDING_LIMIT)] = MAX_PENDING_LIMIT,
) -> dict:
    statuses = await run_in_threadpool(process.process_pending, limit)
    return {"processed": len(statuses), "statuses": statuses}


@router.post("/api/calls/{conversation_id}/process")
async def process_one(conversation_id: str) -> dict:
    status = await run_in_threadpool(process.process_call, conversation_id)
    return {"conversation_id": conversation_id, "status": status}
