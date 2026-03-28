from __future__ import annotations

import argparse
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agents.pipeline_service import run_demo_pipeline


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
STATIC_DIR = ROOT / "static"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dashboard_payload(force_refresh: bool = False) -> dict[str, object]:
    latest_path = OUTPUTS_DIR / "latest_dashboard.json"
    if force_refresh or not latest_path.exists():
        return run_demo_pipeline(output_dir=str(OUTPUTS_DIR), write_files=True)
    return json.loads(latest_path.read_text(encoding="utf-8"))


@dataclass
class RefreshState:
    status: str = "idle"
    last_started_at: str | None = None
    last_completed_at: str | None = None
    last_error: str | None = None
    last_source_mode: str | None = None
    last_live_success_at: str | None = None
    last_live_success_summary: str | None = None
    last_live_error_at: str | None = None
    last_live_error: str | None = None
    run_count: int = 0
    auto_refresh_interval_seconds: int = 3600


@dataclass
class DashboardRuntime:
    payload: dict[str, object] | None = None
    refresh: RefreshState = field(default_factory=RefreshState)
    lock: threading.Lock = field(default_factory=threading.Lock)
    refresh_thread: threading.Thread | None = None

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            refresh_payload = {
                "status": self.refresh.status,
                "last_started_at": self.refresh.last_started_at,
                "last_completed_at": self.refresh.last_completed_at,
                "last_error": self.refresh.last_error,
                "last_source_mode": self.refresh.last_source_mode,
                "last_live_success_at": self.refresh.last_live_success_at,
                "last_live_success_summary": self.refresh.last_live_success_summary,
                "last_live_error_at": self.refresh.last_live_error_at,
                "last_live_error": self.refresh.last_live_error,
                "run_count": self.refresh.run_count,
                "auto_refresh_interval_seconds": self.refresh.auto_refresh_interval_seconds,
            }
            return {
                "has_payload": self.payload is not None,
                "refresh": refresh_payload,
            }

    def get_payload(self) -> dict[str, object]:
        with self.lock:
            if self.payload is None:
                self.payload = load_dashboard_payload(force_refresh=False)
                self.refresh.last_source_mode = str(self.payload.get("source_mode", "unknown"))
            elif self.refresh.status != "refreshing":
                self.payload = load_dashboard_payload(force_refresh=False)
                self.refresh.last_source_mode = str(self.payload.get("source_mode", "unknown"))
            payload = dict(self.payload)
            payload["runtime"] = {
                "status": self.refresh.status,
                "last_started_at": self.refresh.last_started_at,
                "last_completed_at": self.refresh.last_completed_at,
                "last_error": self.refresh.last_error,
                "last_source_mode": self.refresh.last_source_mode,
                "last_live_success_at": self.refresh.last_live_success_at,
                "last_live_success_summary": self.refresh.last_live_success_summary,
                "last_live_error_at": self.refresh.last_live_error_at,
                "last_live_error": self.refresh.last_live_error,
                "run_count": self.refresh.run_count,
                "auto_refresh_interval_seconds": self.refresh.auto_refresh_interval_seconds,
            }
            return payload

    def queue_refresh(self, reason: str = "manual") -> dict[str, object]:
        with self.lock:
            if self.refresh_thread and self.refresh_thread.is_alive():
                return {
                    "queued": False,
                    "status": self.refresh.status,
                    "reason": reason,
                    "message": "Refresh already in progress.",
                }

            self.refresh.status = "refreshing"
            self.refresh.last_started_at = utc_now_iso()
            self.refresh.last_error = None

            thread = threading.Thread(
                target=self._run_refresh,
                args=(reason,),
                daemon=True,
            )
            self.refresh_thread = thread
            thread.start()

            return {
                "queued": True,
                "status": self.refresh.status,
                "reason": reason,
            }

    def _run_refresh(self, reason: str) -> None:
        try:
            payload = load_dashboard_payload(force_refresh=True)
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.refresh.status = "error"
                self.refresh.last_error = str(exc)
                self.refresh.last_completed_at = utc_now_iso()
            return

        with self.lock:
            self.payload = payload
            self.refresh.status = "idle"
            self.refresh.last_completed_at = utc_now_iso()
            self.refresh.last_source_mode = str(payload.get("source_mode", "unknown"))
            self.refresh.last_error = None
            live_error = summarize_live_error(payload)
            if self.refresh.last_source_mode == "tinyfish_web":
                self.refresh.last_live_success_at = self.refresh.last_completed_at
                self.refresh.last_live_success_summary = summarize_live_success(payload)
                self.refresh.last_live_error = None
            elif live_error:
                self.refresh.last_live_error_at = self.refresh.last_completed_at
                self.refresh.last_live_error = live_error
            self.refresh.run_count += 1

    def ensure_seed_payload(self) -> None:
        with self.lock:
            if self.payload is not None:
                return
        try:
            payload = load_dashboard_payload(force_refresh=False)
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.refresh.status = "error"
                self.refresh.last_error = str(exc)
                self.refresh.last_completed_at = utc_now_iso()
            return
        with self.lock:
            self.payload = payload
            self.refresh.last_source_mode = str(payload.get("source_mode", "unknown"))


def summarize_live_success(payload: dict[str, object]) -> str:
    source_batch = payload.get("source_batch", {})
    issue_batch = payload.get("issue_batch", {})
    source_count = source_batch.get("metadata", {}).get("accepted_count", 0)
    live_issue_count = issue_batch.get("metadata", {}).get("live_issue_count", 0)
    return f"{source_count} live sources ingested, {live_issue_count} live article analyses completed."


def summarize_live_error(payload: dict[str, object]) -> str | None:
    source_metadata = payload.get("source_batch", {}).get("metadata", {})
    issue_metadata = payload.get("issue_batch", {}).get("metadata", {})
    source_errors = source_metadata.get("live_errors") or []
    if source_errors:
        return str(source_errors[0])
    issue_errors = issue_metadata.get("live_errors") or []
    if issue_errors:
        return str(issue_errors[0])
    if payload.get("source_mode") != "tinyfish_web":
        return "Live source discovery did not return valid TinyFish candidates, so the batch stayed on fallback data."
    return None


RUNTIME = DashboardRuntime()


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "TinyFishDashboard/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path == "/app.js":
            self._serve_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return

        if path == "/styles.css":
            self._serve_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
            return

        if path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "runtime": RUNTIME.snapshot()["refresh"],
                }
            )
            return

        if path == "/api/dashboard":
            if "refresh" in query:
                self._send_json(RUNTIME.queue_refresh(reason="query_refresh"))
                return
            self._send_json(RUNTIME.get_payload())
            return

        if path == "/api/status":
            self._send_json(RUNTIME.snapshot())
            return

        if path.startswith("/outputs/"):
            file_path = PROJECT_ROOT / path.lstrip("/")
            if file_path.is_file():
                content_type = "application/json; charset=utf-8"
                if file_path.suffix == ".html":
                    content_type = "text/html; charset=utf-8"
                elif file_path.suffix == ".geojson":
                    content_type = "application/geo+json; charset=utf-8"
                self._serve_file(file_path, content_type)
                return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/refresh":
            self._send_json(RUNTIME.queue_refresh(reason="button_refresh"), status=HTTPStatus.ACCEPTED)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(
        self,
        payload: dict[str, object],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def auto_refresh_loop(interval_seconds: int) -> None:
    while True:
        time.sleep(interval_seconds)
        RUNTIME.queue_refresh(reason="scheduled_refresh")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the TinyFish supply-chain dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--auto-refresh-interval",
        type=int,
        default=int(os.getenv("TINYFISH_REFRESH_INTERVAL_SECONDS", "3600")),
    )
    args = parser.parse_args()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME.refresh.auto_refresh_interval_seconds = args.auto_refresh_interval
    RUNTIME.ensure_seed_payload()
    threading.Thread(
        target=auto_refresh_loop,
        args=(args.auto_refresh_interval,),
        daemon=True,
    ).start()

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Serving TinyFish dashboard at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
