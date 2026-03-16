from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


REQUEST_TIMEOUT_SECONDS = 12
TIMELINE_POINT_COUNT = 8


def default_user_agent() -> str:
    contact = os.getenv("WEATHERCHECK_CONTACT", "set-WEATHERCHECK_CONTACT@example.com")
    return f"weathercheck/0.1 ({contact})"


USER_AGENT = default_user_agent()


class ApiError(Exception):
    pass


@dataclass
class Location:
    query: str
    display_name: str
    latitude: float
    longitude: float


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset("utf-8")
            return json.loads(response.read().decode(charset))
    except urllib.error.HTTPError as exc:
        raise ApiError(f"{exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(str(exc.reason)) from exc
    except TimeoutError as exc:
        raise ApiError("request timed out") from exc


def parse_lat_lon(value: str) -> tuple[float, float] | None:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def geocode_address(query: str) -> Location:
    parsed = parse_lat_lon(query)
    if parsed:
        lat, lon = parsed
        return Location(
            query=query,
            display_name=f"Coordinates {lat:.4f}, {lon:.4f}",
            latitude=lat,
            longitude=lon,
        )

    open_meteo_location = geocode_with_open_meteo(query)
    if open_meteo_location:
        return open_meteo_location

    nominatim_location = geocode_with_nominatim(query)
    if nominatim_location:
        return nominatim_location

    raise ApiError("address could not be geocoded")


def geocode_with_open_meteo(query: str) -> Location | None:
    for candidate in geocode_query_candidates(query):
        encoded = urllib.parse.urlencode(
            {
                "name": candidate,
                "count": 1,
                "language": "ko",
                "format": "json",
            }
        )
        try:
            payload = fetch_json(f"https://geocoding-api.open-meteo.com/v1/search?{encoded}")
        except ApiError:
            continue

        results = payload.get("results") or []
        if not results:
            continue

        match = results[0]
        name_parts = [match.get("name"), match.get("admin1"), match.get("country")]
        display_name = ", ".join(part for part in name_parts if part)
        return Location(
            query=query,
            display_name=display_name or candidate,
            latitude=float(match["latitude"]),
            longitude=float(match["longitude"]),
        )

    return None


def geocode_with_nominatim(query: str) -> Location | None:
    encoded = urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
    )
    try:
        payload = fetch_json(f"https://nominatim.openstreetmap.org/search?{encoded}")
    except ApiError:
        return None

    if not payload:
        return None

    match = payload[0]
    return Location(
        query=query,
        display_name=match["display_name"],
        latitude=float(match["lat"]),
        longitude=float(match["lon"]),
    )


def geocode_query_candidates(query: str) -> list[str]:
    compact = " ".join(query.split())
    if not compact:
        return []

    province_aliases = {
        "경기": "경기도",
        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "세종": "세종특별자치시",
        "강원": "강원특별자치도",
        "충북": "충청북도",
        "충남": "충청남도",
        "전북": "전북특별자치도",
        "전남": "전라남도",
        "경북": "경상북도",
        "경남": "경상남도",
        "제주": "제주특별자치도",
    }

    candidates: list[str] = [compact]
    parts = compact.split(" ")
    if parts and parts[0] in province_aliases:
        expanded = " ".join([province_aliases[parts[0]], *parts[1:]])
        candidates.append(expanded)

    for base in list(candidates):
        base_parts = base.split(" ")
        for end in range(len(base_parts) - 1, 1, -1):
            shortened = " ".join(base_parts[:end])
            candidates.append(shortened)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def format_number(value: float | None) -> str | None:
    if value is None or math.isnan(value):
        return None
    return f"{value:.1f}"


def normalize_condition_from_wmo(code: int | None) -> str | None:
    mapping = {
        0: "Clear",
        1: "Mostly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Heavy rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Severe thunderstorm with hail",
    }
    return mapping.get(code, "Unknown")


def summarize_window(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    return max(numeric) if numeric else None


def summarize_temperature(values: list[float | None]) -> tuple[float | None, float | None]:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None, None
    return min(numeric), max(numeric)


def numeric_spread(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if len(numeric) < 2:
        return None
    return max(numeric) - min(numeric)


def timeline_entry(
    time_value: str | None,
    temperature_c: float | None = None,
    precip_probability: float | None = None,
    condition: str | None = None,
) -> dict[str, Any]:
    return {
        "time": time_value,
        "temperature_c": format_number(temperature_c),
        "precip_probability": format_number(precip_probability),
        "condition": condition,
    }


def coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sample_every_n_rows(rows: list[dict[str, Any]], target_count: int = TIMELINE_POINT_COUNT) -> list[dict[str, Any]]:
    if len(rows) <= target_count:
        return rows
    step = max(1, len(rows) // target_count)
    return rows[::step][:target_count]


def open_meteo_forecast(location: Location) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "timezone": "auto",
            "forecast_days": 2,
        }
    )
    payload = fetch_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])[:24]
    temperatures = hourly.get("temperature_2m", [])[:24]
    precip_probabilities = hourly.get("precipitation_probability", [])[:24]
    weather_codes = hourly.get("weather_code", [])[:24]

    timeline_rows = [
        timeline_entry(
            time_value=times[index] if index < len(times) else None,
            temperature_c=coerce_float(temperatures[index]) if index < len(temperatures) else None,
            precip_probability=coerce_float(precip_probabilities[index]) if index < len(precip_probabilities) else None,
            condition=normalize_condition_from_wmo(weather_codes[index]) if index < len(weather_codes) else None,
        )
        for index in range(min(len(times), 24))
    ]
    low, high = summarize_temperature([coerce_float(value) for value in temperatures])
    precip = summarize_window([coerce_float(value) for value in precip_probabilities[:6]])
    current = payload.get("current", {})
    return {
        "provider": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "current_temp_c": format_number(coerce_float(current.get("temperature_2m"))),
        "feels_like_c": format_number(coerce_float(current.get("apparent_temperature"))),
        "condition": normalize_condition_from_wmo(current.get("weather_code")),
        "next_6h_precip_probability": format_number(precip),
        "next_24h_low_c": format_number(low),
        "next_24h_high_c": format_number(high),
        "forecast_time": current.get("time"),
        "timeline": sample_every_n_rows(timeline_rows),
    }


def met_norway_forecast(location: Location) -> dict[str, Any]:
    query = urllib.parse.urlencode({"lat": location.latitude, "lon": location.longitude})
    payload = fetch_json(
        f"https://api.met.no/weatherapi/locationforecast/2.0/compact?{query}",
        headers={"Accept": "application/json"},
    )
    timeseries = payload["properties"]["timeseries"]
    current = timeseries[0]
    next_day = timeseries[:24]

    temps = [
        coerce_float(entry["data"]["instant"]["details"].get("air_temperature"))
        for entry in next_day
    ]
    low, high = summarize_temperature(temps)
    precip_candidates: list[float | None] = []
    timeline_rows = []
    for entry in next_day:
        one_hour = entry["data"].get("next_1_hours") or {}
        six_hours = entry["data"].get("next_6_hours") or {}
        precip_probability = coerce_float(one_hour.get("details", {}).get("probability_of_precipitation"))
        if precip_probability is None:
            precip_probability = coerce_float(six_hours.get("details", {}).get("probability_of_precipitation"))
        precip_candidates.append(precip_probability)
        timeline_rows.append(
            timeline_entry(
                time_value=entry.get("time"),
                temperature_c=coerce_float(entry["data"]["instant"]["details"].get("air_temperature")),
                precip_probability=precip_probability,
                condition=(
                    one_hour.get("summary", {}).get("symbol_code", "")
                    or six_hours.get("summary", {}).get("symbol_code", "")
                ).replace("_", " ")
                or None,
            )
        )

    details = current["data"]["instant"]["details"]
    return {
        "provider": "MET Norway",
        "source_url": "https://www.met.no/en",
        "current_temp_c": format_number(coerce_float(details.get("air_temperature"))),
        "feels_like_c": None,
        "condition": (
            current["data"].get("next_1_hours", {})
            .get("summary", {})
            .get("symbol_code", "")
            .replace("_", " ")
            or None
        ),
        "next_6h_precip_probability": format_number(summarize_window(precip_candidates[:6])),
        "next_24h_low_c": format_number(low),
        "next_24h_high_c": format_number(high),
        "forecast_time": current.get("time"),
        "timeline": sample_every_n_rows(timeline_rows),
    }


def wttr_forecast(location: Location) -> dict[str, Any]:
    url = f"https://wttr.in/{location.latitude:.4f},{location.longitude:.4f}?format=j1"
    payload = fetch_json(url)
    current = payload.get("current_condition", [{}])[0]
    weather_days = payload.get("weather", [])[:2]
    hourly_rows: list[dict[str, Any]] = []
    precip_candidates: list[float | None] = []
    daily_min_temps: list[float | None] = []
    daily_max_temps: list[float | None] = []

    for day in weather_days:
        daily_min_temps.append(coerce_float(day.get("mintempC")))
        daily_max_temps.append(coerce_float(day.get("maxtempC")))
        date_text = day.get("date", "")
        for slot in day.get("hourly", []):
            time_code = str(slot.get("time", "0")).zfill(4)
            time_value = f"{date_text}T{time_code[:2]}:{time_code[2:]}:00"
            precip_probability = coerce_float(slot.get("chanceofrain"))
            if len(precip_candidates) < 6:
                precip_candidates.append(precip_probability)
            hourly_rows.append(
                timeline_entry(
                    time_value=time_value,
                    temperature_c=coerce_float(slot.get("tempC")),
                    precip_probability=precip_probability,
                    condition=(
                        slot.get("weatherDesc", [{}])[0].get("value")
                        if slot.get("weatherDesc")
                        else None
                    ),
                )
            )

    min_candidates = [value for value in daily_min_temps if value is not None]
    max_candidates = [value for value in daily_max_temps if value is not None]
    return {
        "provider": "wttr.in",
        "source_url": "https://wttr.in/:help",
        "current_temp_c": format_number(coerce_float(current.get("temp_C"))),
        "feels_like_c": format_number(coerce_float(current.get("FeelsLikeC"))),
        "condition": (
            current.get("weatherDesc", [{}])[0].get("value")
            if current.get("weatherDesc")
            else None
        ),
        "next_6h_precip_probability": format_number(summarize_window(precip_candidates)),
        "next_24h_low_c": format_number(min(min_candidates)) if min_candidates else None,
        "next_24h_high_c": format_number(max(max_candidates)) if max_candidates else None,
        "forecast_time": datetime.now(timezone.utc).isoformat(),
        "timeline": sample_every_n_rows(hourly_rows[:24]),
    }


PROVIDERS = [
    ("Open-Meteo", open_meteo_forecast),
    ("MET Norway", met_norway_forecast),
    ("wttr.in", wttr_forecast),
]


def build_consensus(providers: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [provider for provider in providers if not provider.get("error")]
    current_spread = numeric_spread(
        [coerce_float(provider.get("current_temp_c")) for provider in successful]
    )
    precip_spread = numeric_spread(
        [coerce_float(provider.get("next_6h_precip_probability")) for provider in successful]
    )

    timeline_by_index: list[dict[str, Any]] = []
    for index in range(TIMELINE_POINT_COUNT):
        time_value = None
        temp_values: list[float | None] = []
        precip_values: list[float | None] = []
        provider_count = 0
        for provider in successful:
            rows = provider.get("timeline", [])
            if index >= len(rows):
                continue
            row = rows[index]
            time_value = time_value or row.get("time")
            temp_values.append(coerce_float(row.get("temperature_c")))
            precip_values.append(coerce_float(row.get("precip_probability")))
            provider_count += 1
        timeline_by_index.append(
            {
                "time": time_value,
                "temperature_spread_c": format_number(numeric_spread(temp_values)),
                "precip_spread_probability": format_number(numeric_spread(precip_values)),
                "provider_count": provider_count,
            }
        )

    return {
        "successful_provider_count": len(successful),
        "failed_provider_count": len(providers) - len(successful),
        "current_temp_spread_c": format_number(current_spread),
        "next_6h_precip_spread_probability": format_number(precip_spread),
        "timeline": timeline_by_index,
    }


def collect_forecasts(address: str) -> dict[str, Any]:
    location = geocode_address(address)
    providers = []
    for provider_name, provider in PROVIDERS:
        try:
            providers.append(provider(location))
        except Exception as exc:
            providers.append(
                {
                    "provider": provider_name,
                    "error": str(exc),
                }
            )

    return {
        "location": {
            "query": location.query,
            "display_name": location.display_name,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "providers": providers,
        "consensus": build_consensus(providers),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
