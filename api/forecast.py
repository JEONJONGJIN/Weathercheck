from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from weather_core import ApiError, collect_fixed_location_forecasts


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self._write_json(collect_fixed_location_forecasts())
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
