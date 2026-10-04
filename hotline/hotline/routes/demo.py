"""Stub router: owner replaces the 501 responses (see docs/hotline-spec.md)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/demo")
def demo_page() -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
