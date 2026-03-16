from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from weather_core import ApiError, collect_forecasts


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        address = (params.get("address") or [""])[0].strip()

        if not address:
            self._write_json({"error": "address is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            self._write_json(collect_forecasts(address))
        except ApiError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._write_json(
                {"error": f"unexpected error: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _write_json(self, payload, status=HTTPStatus.OK):
        body = self._encode_json(payload)
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _encode_json(payload):
        import json

        return json.dumps(payload, ensure_ascii=False).encode("utf-8")
