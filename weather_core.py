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
FIXED_LOCATION_LABEL = "경기 연천군 장남면 장백로278번길 4"
DEFAULT_CONTACT = "jin0424@hanmail.net"
DEFAULT_LATITUDE = 37.9851297299633
DEFAULT_LONGITUDE = 126.886246142811
KMA_BULLETIN_STN_ID = os.getenv("KMA_BULLETIN_STN_ID", "109")


def default_user_agent() -> str:
    contact = os.getenv("WEATHERCHECK_CONTACT", DEFAULT_CONTACT)
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


def configured_location() -> Location:
    latitude_text = os.getenv("WEATHERCHECK_LATITUDE", str(DEFAULT_LATITUDE))
    longitude_text = os.getenv("WEATHERCHECK_LONGITUDE", str(DEFAULT_LONGITUDE))

    try:
        latitude = float(latitude_text)
        longitude = float(longitude_text)
    except ValueError as exc:
        raise ApiError("fixed coordinates are invalid") from exc

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ApiError("fixed coordinates are out of range")

    return Location(
        query=FIXED_LOCATION_LABEL,
        display_name=FIXED_LOCATION_LABEL,
        latitude=latitude,
        longitude=longitude,
    )


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


def data_go_kr_service_key() -> str | None:
    return os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("SERVICE_KEY")


def format_number(value: float | None) -> str | None:
    if value is None or math.isnan(value):
        return None
    return f"{value:.1f}"


def coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def normalize_condition_from_wmo(code: int | None) -> str | None:
    mapping = {
        0: "맑음",
        1: "대체로 맑음",
        2: "구름 조금",
        3: "흐림",
        45: "안개",
        48: "착빙 안개",
        51: "약한 이슬비",
        53: "이슬비",
        55: "강한 이슬비",
        61: "약한 비",
        63: "비",
        65: "강한 비",
        71: "약한 눈",
        73: "눈",
        75: "강한 눈",
        80: "소나기",
        81: "강한 소나기",
        82: "매우 강한 소나기",
        95: "뇌우",
        96: "우박 동반 뇌우",
        99: "강한 우박 동반 뇌우",
    }
    return mapping.get(code, "알 수 없음")


def translate_met_symbol(symbol_code: str | None) -> str | None:
    if not symbol_code:
        return None

    base = symbol_code.split("_")[0]
    mapping = {
        "clearsky": "맑음",
        "fair": "대체로 맑음",
        "partlycloudy": "구름 조금",
        "cloudy": "흐림",
        "fog": "안개",
        "lightrain": "약한 비",
        "rain": "비",
        "heavyrain": "강한 비",
        "lightrainshowers": "약한 소나기",
        "rainshowers": "소나기",
        "heavyrainshowers": "강한 소나기",
        "lightsleet": "약한 진눈깨비",
        "sleet": "진눈깨비",
        "heavysleet": "강한 진눈깨비",
        "lightsnow": "약한 눈",
        "snow": "눈",
        "heavysnow": "강한 눈",
        "lightsnowshowers": "약한 눈 소나기",
        "snowshowers": "눈 소나기",
        "heavysnowshowers": "강한 눈 소나기",
        "rainandthunder": "비와 천둥",
        "rainshowersandthunder": "소나기와 천둥",
        "sleetandthunder": "진눈깨비와 천둥",
        "snowandthunder": "눈과 천둥",
        "snowshowersandthunder": "눈 소나기와 천둥",
    }
    return mapping.get(base, translate_condition_text(base.replace("_", " ")))


def translate_condition_text(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip().lower().replace("_", " ")
    exact_mapping = {
        "sunny": "맑음",
        "clear": "맑음",
        "mostly clear": "대체로 맑음",
        "partly cloudy": "구름 조금",
        "cloudy": "흐림",
        "overcast": "흐림",
        "mist": "박무",
        "fog": "안개",
        "freezing fog": "어는 안개",
        "patchy rain nearby": "주변에 비 가능성",
        "light drizzle": "약한 이슬비",
        "drizzle": "이슬비",
        "light rain": "약한 비",
        "moderate rain": "비",
        "heavy rain": "강한 비",
        "light rain shower": "약한 소나기",
        "moderate or heavy rain shower": "강한 소나기",
        "patchy light rain": "약한 비",
        "patchy light drizzle": "약한 이슬비",
        "light sleet": "약한 진눈깨비",
        "moderate or heavy sleet": "강한 진눈깨비",
        "light snow": "약한 눈",
        "patchy snow nearby": "주변에 눈 가능성",
        "moderate snow": "눈",
        "heavy snow": "강한 눈",
        "thundery outbreaks nearby": "주변에 뇌우 가능성",
        "thunderstorm": "뇌우",
    }
    if normalized in exact_mapping:
        return exact_mapping[normalized]

    contains_mapping = [
        ("thunder", "천둥"),
        ("sleet", "진눈깨비"),
        ("snow", "눈"),
        ("drizzle", "이슬비"),
        ("shower", "소나기"),
        ("rain", "비"),
        ("fog", "안개"),
        ("mist", "박무"),
        ("cloud", "흐림"),
        ("clear", "맑음"),
        ("sun", "맑음"),
    ]
    for token, translated in contains_mapping:
        if token in normalized:
            return translated

    return value


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


def sample_every_n_rows(rows: list[dict[str, Any]], target_count: int = TIMELINE_POINT_COUNT) -> list[dict[str, Any]]:
    if len(rows) <= target_count:
        return rows
    step = max(1, len(rows) // target_count)
    return rows[::step][:target_count]


def summarize_korean_bulletin(value: str | None, limit: int = 36) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split())
    for separator in [".", "다.", "\n"]:
        if separator in normalized:
            candidate = normalized.split(separator)[0].strip()
            if candidate:
                normalized = candidate
                break
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


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
    temperatures = [
        coerce_float(entry["data"]["instant"]["details"].get("air_temperature"))
        for entry in next_day
    ]
    low, high = summarize_temperature(temperatures)

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
                    translate_met_symbol(
                        one_hour.get("summary", {}).get("symbol_code", "")
                        or six_hours.get("summary", {}).get("symbol_code", "")
                    )
                ),
            )
        )

    details = current["data"]["instant"]["details"]
    return {
        "provider": "MET Norway",
        "source_url": "https://www.met.no/en",
        "current_temp_c": format_number(coerce_float(details.get("air_temperature"))),
        "feels_like_c": None,
        "condition": (
            translate_met_symbol(
                current["data"].get("next_1_hours", {})
                .get("summary", {})
                .get("symbol_code", "")
            )
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
                        translate_condition_text(slot.get("weatherDesc", [{}])[0].get("value"))
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
            translate_condition_text(current.get("weatherDesc", [{}])[0].get("value"))
            if current.get("weatherDesc")
            else None
        ),
        "next_6h_precip_probability": format_number(summarize_window(precip_candidates)),
        "next_24h_low_c": format_number(min(min_candidates)) if min_candidates else None,
        "next_24h_high_c": format_number(max(max_candidates)) if max_candidates else None,
        "forecast_time": datetime.now(timezone.utc).isoformat(),
        "timeline": sample_every_n_rows(hourly_rows[:24]),
    }


def kma_bulletin_forecast(location: Location) -> dict[str, Any]:
    service_key = data_go_kr_service_key()
    if not service_key:
        raise ApiError("DATA_GO_KR_SERVICE_KEY is not configured")

    query = urllib.parse.urlencode(
        {
            "serviceKey": service_key,
            "pageNo": 1,
            "numOfRows": 10,
            "dataType": "JSON",
            "stnId": KMA_BULLETIN_STN_ID,
        }
    )
    payload = fetch_json(f"https://apis.data.go.kr/1360000/VilageFcstMsgService/getWthrSituation?{query}")
    body = payload.get("response", {}).get("body", {})
    items = body.get("items", {}).get("item", [])
    if not items:
        raise ApiError("KMA bulletin returned no items")

    entry = items[0]
    overview = entry.get("wfSv1") or ""
    notice = entry.get("wn") or ""
    reserve_notice = entry.get("wr") or ""
    summary = summarize_korean_bulletin(overview) or summarize_korean_bulletin(notice) or "기상 통보문"
    if notice and notice != "없음":
        summary = f"{summary} / 특보 {summarize_korean_bulletin(notice, 18)}"

    return {
        "provider": "기상청 통보문",
        "source_url": "https://www.data.go.kr/data/15058629/openapi.do",
        "current_temp_c": None,
        "feels_like_c": None,
        "condition": summary,
        "next_6h_precip_probability": None,
        "next_24h_low_c": None,
        "next_24h_high_c": None,
        "forecast_time": entry.get("tmFc"),
        "timeline": [],
        "bulletin_overview": overview or None,
        "bulletin_notice": notice or None,
        "bulletin_preliminary_notice": reserve_notice or None,
    }


def active_providers() -> list[tuple[str, Any]]:
    providers = [
        ("Open-Meteo", open_meteo_forecast),
        ("MET Norway", met_norway_forecast),
        ("wttr.in", wttr_forecast),
    ]
    if data_go_kr_service_key():
        providers.append(("기상청 통보문", kma_bulletin_forecast))
    return providers


def build_consensus(providers: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [provider for provider in providers if not provider.get("error")]
    current_spread = numeric_spread([coerce_float(provider.get("current_temp_c")) for provider in successful])
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


def collect_fixed_location_forecasts() -> dict[str, Any]:
    location = configured_location()
    providers = []
    for provider_name, provider in active_providers():
        try:
            providers.append(provider(location))
        except Exception as exc:
            providers.append({"provider": provider_name, "error": str(exc)})

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
