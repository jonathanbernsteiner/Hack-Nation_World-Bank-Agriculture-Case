"""Stub router: owner replaces the 501 responses (see docs/hotline-spec.md)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/api/tools/find_farmer_by_location")
def find_farmer_by_location() -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
