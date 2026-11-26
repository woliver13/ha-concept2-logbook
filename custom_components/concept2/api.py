"""Thin async client for the Concept2 Logbook API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import API_BASE_URL, ROWER_RESULT_TYPE


class Concept2ApiError(Exception):
    """Base error for the Concept2 API client."""


class Concept2AuthError(Concept2ApiError):
    """Raised when the access token is invalid or expired."""


class Concept2ConnectionError(Concept2ApiError):
    """Raised when the Concept2 API can't be reached."""


@dataclass
class Concept2Result:
    """A single logged rowing result."""

    result_id: int
    date: datetime
    distance_meters: float
    duration_seconds: float
    calories_total: int | None
    stroke_count: int | None
    stroke_rate: int | None
    drag_factor: int | None
    heart_rate_avg: int | None = None
    heart_rate_ending: int | None = None


def pace_500m_seconds(result: Concept2Result) -> float | None:
    """Return a result's pace in seconds per 500m, or None for a zero-distance result."""
    if not result.distance_meters:
        return None
    return result.duration_seconds / (result.distance_meters / 500)


class Concept2ApiClient:
    """Async client for the Concept2 Logbook API's `/users/me` endpoints."""

    def __init__(self, hass: HomeAssistant, access_token: str) -> None:
        """Set up the client using HA's shared aiohttp session."""
        self._session = async_get_clientsession(hass)
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self.last_response: dict[str, Any] | None = None

    async def async_get_user_id(self) -> str:
        """Validate the token and return the Concept2 user id."""
        payload = await self._request("/users/me")
        return str(payload["data"]["id"])

    async def async_get_recent_rower_results(self) -> list[Concept2Result]:
        """Return recent rower results, sorted ascending by date; empty if there are none.

        Only page 1 is fetched, on the assumption a user logs far fewer results between
        polls than a page holds.
        """
        payload = await self._request("/users/me/results")
        self.last_response = payload
        results = [
            _parse_result(item)
            for item in payload.get("data", [])
            if item.get("type") == ROWER_RESULT_TYPE
        ]
        results.sort(key=lambda result: result.date)
        return results

    async def _request(self, path: str) -> dict[str, Any]:
        """Make an authenticated GET request and return the parsed JSON body."""
        try:
            async with self._session.get(
                f"{API_BASE_URL}{path}", headers=self._headers
            ) as response:
                if response.status == 401:
                    raise Concept2AuthError("Invalid or expired access token")
                if response.status >= 400:
                    raise Concept2ConnectionError(
                        f"Concept2 API returned status {response.status}"
                    )
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise Concept2ConnectionError(str(err) or type(err).__name__) from err


def _parse_result(raw: dict[str, Any]) -> Concept2Result:
    """Turn one raw API result into a Concept2Result."""
    heart_rate_avg, heart_rate_ending = _parse_heart_rate_summary(raw)
    return Concept2Result(
        result_id=raw["id"],
        date=_parse_timestamp(raw["date"]),
        distance_meters=float(raw["distance"]),
        duration_seconds=float(raw["time"]) / 10,
        calories_total=raw.get("calories_total"),
        stroke_count=raw.get("stroke_count"),
        stroke_rate=raw.get("stroke_rate"),
        drag_factor=raw.get("drag_factor"),
        heart_rate_avg=heart_rate_avg,
        heart_rate_ending=heart_rate_ending,
    )


def _parse_heart_rate_summary(raw: dict[str, Any]) -> tuple[int | None, int | None]:
    """Return (average, ending) heart rate across a result's splits, or (None, None).

    The API has no result-level heart-rate summary, only a `heart_rate` object per
    split (`workout.splits[].heart_rate`), so this averages the splits' own averages
    and takes the last split's ending reading.
    """
    splits = raw.get("workout", {}).get("splits", [])
    averages = [
        split["heart_rate"]["average"]
        for split in splits
        if isinstance(split.get("heart_rate"), dict) and "average" in split["heart_rate"]
    ]
    endings = [
        split["heart_rate"]["ending"]
        for split in splits
        if isinstance(split.get("heart_rate"), dict) and "ending" in split["heart_rate"]
    ]
    average = round(sum(averages) / len(averages)) if averages else None
    ending = endings[-1] if endings else None
    return average, ending


def _parse_timestamp(raw_date: str) -> datetime:
    """Parse the API's date string, assuming HA's local timezone if none is given.

    The Concept2 API does not include timezone info on result timestamps. HA's
    configured local timezone is the best available proxy for "the rower's local
    time," and downstream day-boundary math (days-since-last-workout) depends on
    every result having a consistent, aware timestamp.
    """
    parsed = dt_util.parse_datetime(raw_date)
    if parsed is None:
        raise Concept2ApiError(f"Unrecognized date format from Concept2 API: {raw_date!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed
