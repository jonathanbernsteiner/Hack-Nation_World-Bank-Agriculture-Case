"""Stub router: owner replaces the 501 responses (see docs/hotline-spec.md)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/api/tools/get_weather_forecast")
def get_weather_forecast() -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
