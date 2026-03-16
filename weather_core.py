from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


REQUEST_TIMEOUT_SECONDS = 12
TIMELINE_POINT_COUNT = 8
FIXED_LOCATION_LABEL = "경기 연천군 장남면 장백로278번길 4"
DEFAULT_CONTACT = "jin0424@hanmail.net"
DEFAULT_LATITUDE = 37.9851297299633
DEFAULT_LONGITUDE = 126.886246142811
KST = timezone(timedelta(hours=9))
KMA_MID_LAND_REG_ID = os.getenv("KMA_MID_LAND_REG_ID", "11B00000")
KMA_MID_TA_REG_ID = os.getenv("KMA_MID_TA_REG_ID", "11B10101")


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


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset("utf-8")
            return response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        charset = exc.headers.get_content_charset("utf-8") if exc.headers else "utf-8"
        body = exc.read().decode(charset, errors="replace")
        snippet = " ".join(body.split())[:180]
        raise ApiError(f"{exc.code} {exc.reason}: {snippet}") from exc
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


def kma_grid_from_lat_lon(latitude: float, longitude: float) -> tuple[int, int]:
    re_value = 6371.00877 / 5.0
    grid = math.pi / 180.0
    slat1 = 30.0 * grid
    slat2 = 60.0 * grid
    olon = 126.0 * grid
    olat = 38.0 * grid
    xo = 43.0
    yo = 136.0

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re_value * sf / math.pow(ro, sn)
    ra = math.tan(math.pi * 0.25 + latitude * grid * 0.5)
    ra = re_value * sf / math.pow(ra, sn)
    theta = longitude * grid - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    x = int(math.floor(ra * math.sin(theta) + xo + 0.5))
    y = int(math.floor(ro - ra * math.cos(theta) + yo + 0.5))
    return x, y


def latest_kma_base_datetime(now: datetime | None = None) -> tuple[str, str]:
    current = now.astimezone(KST) if now else datetime.now(KST)
    issue_hours = [23, 20, 17, 14, 11, 8, 5, 2]
    for hour in issue_hours:
        candidate = current.replace(hour=hour, minute=0, second=0, microsecond=0)
        if current >= candidate + timedelta(minutes=10):
            return candidate.strftime("%Y%m%d"), candidate.strftime("%H%M")

    previous_day = (current - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
    return previous_day.strftime("%Y%m%d"), previous_day.strftime("%H%M")


def kma_sky_text(code: str | None) -> str | None:
    mapping = {
        "1": "맑음",
        "3": "구름 많음",
        "4": "흐림",
    }
    return mapping.get(str(code)) if code is not None else None


def kma_pty_text(code: str | None) -> str | None:
    mapping = {
        "0": None,
        "1": "비",
        "2": "비/눈",
        "3": "눈",
        "4": "소나기",
        "5": "빗방울",
        "6": "빗방울/눈날림",
        "7": "눈날림",
    }
    return mapping.get(str(code)) if code is not None else None


def kma_condition_text(sky: str | None, pty: str | None) -> str | None:
    precipitation = kma_pty_text(pty)
    if precipitation:
        return precipitation
    return kma_sky_text(sky)


def latest_kma_mid_base_datetime(now: datetime | None = None) -> str:
    current = now.astimezone(KST) if now else datetime.now(KST)
    if current.hour >= 18:
        candidate = current.replace(hour=18, minute=0, second=0, microsecond=0)
    elif current.hour >= 6:
        candidate = current.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        previous = current - timedelta(days=1)
        candidate = previous.replace(hour=18, minute=0, second=0, microsecond=0)
    return candidate.strftime("%Y%m%d%H00")


def fetch_data_go_kr_payload(service_path: str, params: str, service_key: str) -> dict[str, Any]:
    candidate_urls = [
        f"http://apis.data.go.kr{service_path}?serviceKey={service_key}{params}",
        f"https://apis.data.go.kr{service_path}?serviceKey={service_key}{params}",
        f"http://apis.data.go.kr{service_path}?serviceKey={urllib.parse.quote(service_key, safe='')}{params}",
        f"https://apis.data.go.kr{service_path}?serviceKey={urllib.parse.quote(service_key, safe='')}{params}",
    ]

    last_error: Exception | None = None
    for url in candidate_urls:
        try:
            return json.loads(fetch_text(url))
        except Exception as exc:
            last_error = exc
    raise ApiError(str(last_error) if last_error else "data.go.kr request failed")


def group_kma_forecast_rows(items: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = {}
    for item in items:
        forecast_time = f"{item.get('fcstDate', '')}T{str(item.get('fcstTime', '')).zfill(4)[:2]}:{str(item.get('fcstTime', '')).zfill(4)[2:]}:00"
        grouped.setdefault(forecast_time, {})
        grouped[forecast_time][item.get("category", "")] = str(item.get("fcstValue", ""))
    return grouped


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
        "time_label": "예보 시각",
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


def kma_short_forecast(location: Location) -> dict[str, Any]:
    service_key = data_go_kr_service_key()
    if not service_key:
        raise ApiError("DATA_GO_KR_SERVICE_KEY is not configured")

    nx, ny = kma_grid_from_lat_lon(location.latitude, location.longitude)
    base_date, base_time = latest_kma_base_datetime()
    base_params = (
        f"&pageNo=1"
        f"&numOfRows=1000"
        f"&dataType=JSON"
        f"&base_date={base_date}"
        f"&base_time={base_time}"
        f"&nx={nx}"
        f"&ny={ny}"
    )
    payload = fetch_data_go_kr_payload(
        "/1360000/VilageFcstInfoService_2.0/getVilageFcst",
        base_params,
        service_key,
    )

    header = payload.get("response", {}).get("header", {})
    if header.get("resultCode") not in (None, "00"):
        raise ApiError(f"{header.get('resultCode')} {header.get('resultMsg')}")

    body = payload.get("response", {}).get("body", {})
    items = body.get("items", {}).get("item", [])
    if not items:
        raise ApiError("KMA short forecast returned no items")

    grouped = group_kma_forecast_rows(items)
    ordered_times = sorted(grouped.keys())
    timeline_rows = []
    for forecast_time in ordered_times[:24]:
        bucket = grouped[forecast_time]
        timeline_rows.append(
            timeline_entry(
                time_value=forecast_time,
                temperature_c=coerce_float(bucket.get("TMP")),
                precip_probability=coerce_float(bucket.get("POP")),
                condition=kma_condition_text(bucket.get("SKY"), bucket.get("PTY")),
            )
        )

    first_bucket = grouped[ordered_times[0]]
    min_candidates = [coerce_float(item.get("fcstValue")) for item in items if item.get("category") == "TMN"]
    max_candidates = [coerce_float(item.get("fcstValue")) for item in items if item.get("category") == "TMX"]
    min_candidates = [value for value in min_candidates if value is not None]
    max_candidates = [value for value in max_candidates if value is not None]

    return {
        "provider": "기상청 단기예보",
        "source_url": "https://www.data.go.kr/data/15084084/openapi.do",
        "current_temp_c": format_number(coerce_float(first_bucket.get("TMP"))),
        "feels_like_c": None,
        "condition": kma_condition_text(first_bucket.get("SKY"), first_bucket.get("PTY")),
        "next_6h_precip_probability": format_number(
            summarize_window([coerce_float(grouped[key].get("POP")) for key in ordered_times[:6]])
        ),
        "next_24h_low_c": format_number(min(min_candidates)) if min_candidates else None,
        "next_24h_high_c": format_number(max(max_candidates)) if max_candidates else None,
        "forecast_time": f"{base_date}T{base_time[:2]}:{base_time[2:]}:00+09:00",
        "time_label": "발표 시각",
        "timeline": sample_every_n_rows(timeline_rows),
        "humidity": first_bucket.get("REH"),
        "wind_speed_ms": first_bucket.get("WSD"),
    }


def kma_mid_forecast() -> dict[str, Any]:
    service_key = data_go_kr_service_key()
    if not service_key:
        raise ApiError("DATA_GO_KR_SERVICE_KEY is not configured")

    tm_fc = latest_kma_mid_base_datetime()
    land_params = (
        f"&pageNo=1"
        f"&numOfRows=10"
        f"&dataType=JSON"
        f"&regId={urllib.parse.quote(KMA_MID_LAND_REG_ID, safe='')}"
        f"&tmFc={tm_fc}"
    )
    ta_params = (
        f"&pageNo=1"
        f"&numOfRows=10"
        f"&dataType=JSON"
        f"&regId={urllib.parse.quote(KMA_MID_TA_REG_ID, safe='')}"
        f"&tmFc={tm_fc}"
    )
    land_payload = fetch_data_go_kr_payload(
        "/1360000/MidFcstInfoService/getMidLandFcst",
        land_params,
        service_key,
    )
    ta_payload = fetch_data_go_kr_payload(
        "/1360000/MidFcstInfoService/getMidTa",
        ta_params,
        service_key,
    )

    land_header = land_payload.get("response", {}).get("header", {})
    ta_header = ta_payload.get("response", {}).get("header", {})
    if land_header.get("resultCode") not in (None, "00"):
        raise ApiError(f"{land_header.get('resultCode')} {land_header.get('resultMsg')}")
    if ta_header.get("resultCode") not in (None, "00"):
        raise ApiError(f"{ta_header.get('resultCode')} {ta_header.get('resultMsg')}")

    land_items = land_payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    ta_items = ta_payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if not land_items or not ta_items:
        raise ApiError("KMA mid forecast returned no items")

    land = land_items[0]
    ta = ta_items[0]
    days = []
    for day in range(3, 11):
        am_key = f"wf{day}Am"
        pm_key = f"wf{day}Pm"
        low_key = f"taMin{day}"
        high_key = f"taMax{day}"
        am_text = land.get(am_key) or None
        pm_text = land.get(pm_key) or am_text
        low = ta.get(low_key)
        high = ta.get(high_key)
        if am_text is None and pm_text is None and low is None and high is None:
            continue
        days.append(
            {
                "day_offset": day,
                "am_condition": translate_condition_text(am_text) if am_text else None,
                "pm_condition": translate_condition_text(pm_text) if pm_text else None,
                "low_c": format_number(coerce_float(low)),
                "high_c": format_number(coerce_float(high)),
            }
        )

    return {
        "provider": "기상청 중기예보",
        "source_url": "https://www.data.go.kr/data/15059468/openapi.do",
        "forecast_time": f"{tm_fc[:4]}-{tm_fc[4:6]}-{tm_fc[6:8]}T{tm_fc[8:10]}:00:00+09:00",
        "time_label": "발표 시각",
        "days": days,
    }


def active_providers() -> list[tuple[str, Any]]:
    providers = [
        ("Open-Meteo", open_meteo_forecast),
    ]
    if data_go_kr_service_key():
        providers.append(("기상청 단기예보", kma_short_forecast))
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
        "mid_forecast": (
            kma_mid_forecast()
            if data_go_kr_service_key()
            else None
        ),
        "consensus": build_consensus(providers),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
