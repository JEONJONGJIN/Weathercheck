from __future__ import annotations

import json
import sys
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from weather_core import ApiError, collect_forecasts


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
HOST = "127.0.0.1"
PORT = 8000


def content_type_for(path: Path) -> str:
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    return "text/html; charset=utf-8"


class WeatherCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.serve_file(BASE_DIR / "index.html")
            return
        if parsed.path.startswith("/static/"):
            local = STATIC_DIR / parsed.path.removeprefix("/static/")
            self.serve_file(local)
            return
        if parsed.path == "/api/forecast":
            self.serve_forecast(parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(path))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_forecast(self, query_string: str) -> None:
        params = urllib.parse.parse_qs(query_string)
        address = (params.get("address") or [""])[0].strip()
        if not address:
            self.write_json({"error": "address is required"}, status=HTTPStatus.BAD_REQUEST)
            return
        try:
            payload = collect_forecasts(address)
            self.write_json(payload)
        except ApiError as exc:
            self.write_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self.write_json({"error": f"unexpected error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def run() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WeatherCheckHandler)
    print(f"Serving weathercheck at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
