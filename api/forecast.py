from __future__ import annotations

import json
from http import HTTPStatus

from weather_core import ApiError, collect_forecasts


def handler(request):
    address = (request.args.get("address") or "").strip()
    if not address:
        return _json_response({"error": "address is required"}, status=HTTPStatus.BAD_REQUEST)

    try:
        return _json_response(collect_forecasts(address))
    except ApiError as exc:
        return _json_response({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
    except Exception as exc:
        return _json_response({"error": f"unexpected error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def _json_response(payload, status=HTTPStatus.OK):
    return {
        "statusCode": int(status),
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(payload, ensure_ascii=False),
    }
