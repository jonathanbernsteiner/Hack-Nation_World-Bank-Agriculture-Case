"""Stub router: owner replaces the 501 responses (see docs/hotline-spec.md)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/api/jobs/process-pending")
def process_pending() -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.post("/api/calls/{conversation_id}/process")
def process_call(conversation_id: str) -> JSONResponse:
    del conversation_id  # stub
    return JSONResponse({"status": "not_implemented"}, status_code=501)
