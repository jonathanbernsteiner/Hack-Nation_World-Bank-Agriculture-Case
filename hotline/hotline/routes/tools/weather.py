"""POST /api/tools/get_weather_forecast (docs/hotline-spec.md section 6).

Always HTTP 200 with a `status`; 401 only for a bad tool secret. The response carries
the place name and forecast figures only, never farmer identifiers."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hotline import db, security, weather

logger = logging.getLogger(__name__)

router = APIRouter()

_FARMER_LOCATION_SQL = """
select v.village, v.district, v.lat, v.lon
from public.calls c
join public.farmers f on f.id = c.farmer_id
join public.villages v on v.id = f.village_id
where c.conversation_id = %s
"""


class WeatherRequest(BaseModel):
    conversation_id: str | None = None
    call_sid: str | None = None
    district: str | None = None


class Place:
    """A resolved location: coordinates and the label spoken back to the caller."""

    def __init__(self, lat: float, lon: float, label: str):
        self.lat, self.lon, self.label = lat, lon, label


def farmer_place(conversation_id: str | None, conn=None) -> Place | None:
    """The identified farmer's village (or its district centroid). None when the
    conversation has no identified farmer yet. Raises on database errors."""
    if not conversation_id:
        return None
    if conn is not None:
        row = conn.execute(_FARMER_LOCATION_SQL, (conversation_id,)).fetchone()
    else:
        with db.connect() as own:
            row = own.execute(_FARMER_LOCATION_SQL, (conversation_id,)).fetchone()
    if row is None:
        return None
    village, district, lat, lon = row
    if lat is not None and lon is not None:
        return Place(lat, lon, f"{village}, {district}")
    centroid = weather.district_centroid(district)
    return Place(centroid[0], centroid[1], district) if centroid else None


def _resolve(request: WeatherRequest) -> Place | None:
    """The farmer's place, else the request district. A database failure falls through."""
    try:
        place = farmer_place(request.conversation_id)
    except Exception as exc:
        logger.warning("weather: farmer lookup failed: %s", type(exc).__name__)
        place = None
    if place is None:
        centroid = weather.district_centroid(request.district)
        if centroid:
            place = Place(centroid[0], centroid[1], centroid[2])
    return place


@router.post("/api/tools/get_weather_forecast", dependencies=[Depends(security.require_tool_secret)])
def get_weather_forecast(request: WeatherRequest) -> dict:
    place = _resolve(request)
    if place is None:
        return {"status": "unknown_location"}
    result = weather.forecast(place.lat, place.lon)
    if result is None:
        return {"status": "unavailable"}
    return {"status": "ok", "place": place.label, "source": weather.SOURCE, **result}
