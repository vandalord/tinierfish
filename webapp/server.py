from __future__ import annotations

import argparse
import json
import os
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agents.pipeline_service import run_demo_pipeline


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
STATIC_DIR = ROOT / "static"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REFRESH_LOG_PATH = OUTPUTS_DIR / "refresh.log"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_refresh_log(message: str) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with REFRESH_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now_iso()}] {message}\n")


def read_cached_dashboard_payload() -> dict[str, object] | None:
    latest_path = OUTPUTS_DIR / "latest_dashboard.json"
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def run_dashboard_refresh() -> dict[str, object]:
    return run_demo_pipeline(output_dir=str(OUTPUTS_DIR), write_files=True)


def build_empty_payload() -> dict[str, object]:
    now = utc_now_iso()
    return {
        "batch_root": None,
        "generated_at": None,
        "source_mode": "awaiting_initial_scrape",
        "source_batch": {
            "batch_id": None,
            "created_at": now,
            "metadata": {"accepted_count": 0, "candidate_count": 0, "rejected_count": 0},
            "sources": [],
        },
        "issue_batch": {
            "batch_id": None,
            "created_at": now,
            "metadata": {"live_issue_count": 0},
            "issues": [],
        },
        "recommendation_batch": {
            "batch_id": None,
            "created_at": now,
            "metadata": {},
            "recommendations": [],
        },
        "visualization_batch": {
            "batch_id": None,
            "created_at": now,
            "html_path": None,
            "geojson_path": None,
            "geojson": {
                "type": "FeatureCollection",
                "features": [],
            },
        },
    }


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def payload_age_seconds(payload: dict[str, object] | None) -> float | None:
    if not payload:
        return None
    generated_at = parse_iso_datetime(str(payload.get("generated_at") or ""))
    if generated_at is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - generated_at).total_seconds())


def next_refresh_due_at(payload: dict[str, object] | None, interval_seconds: int) -> float | None:
    age = payload_age_seconds(payload)
    if age is None:
        return None
    generated_at = parse_iso_datetime(str(payload.get("generated_at") or ""))
    if generated_at is None:
        return None
    return (generated_at.timestamp() + interval_seconds)


def format_due_at_iso(payload: dict[str, object] | None, interval_seconds: int) -> str | None:
    due_epoch = next_refresh_due_at(payload, interval_seconds)
    if due_epoch is None:
        return None
    return datetime.fromtimestamp(due_epoch, tz=timezone.utc).isoformat()


def should_refresh_payload(payload: dict[str, object] | None, interval_seconds: int) -> bool:
    if payload is None:
        return True
    age = payload_age_seconds(payload)
    if age is None:
        return True
    return age >= interval_seconds


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
                "next_refresh_due_at": format_due_at_iso(self.payload, self.refresh.auto_refresh_interval_seconds),
            }
            return {
                "has_payload": self.payload is not None,
                "refresh": refresh_payload,
            }

    def get_payload(self) -> dict[str, object]:
        self.reload_cached_payload()
        with self.lock:
            payload = dict(self.payload or build_empty_payload())
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
                "next_refresh_due_at": format_due_at_iso(self.payload, self.refresh.auto_refresh_interval_seconds),
            }
            return payload

    def reload_cached_payload(self) -> None:
        cached_payload = read_cached_dashboard_payload()
        if cached_payload is None:
            return
        with self.lock:
            if self.refresh.status == "refreshing":
                return
            self._apply_payload_locked(cached_payload, increment_run_count=False)

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
            append_refresh_log(f"refresh queued: reason={reason}")

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
        append_refresh_log(f"refresh started: reason={reason}")
        try:
            payload = run_dashboard_refresh()
        except Exception as exc:  # noqa: BLE001
            append_refresh_log(f"refresh failed: {exc}")
            append_refresh_log(traceback.format_exc().rstrip())
            with self.lock:
                self.refresh.status = "error"
                self.refresh.last_error = str(exc)
                self.refresh.last_completed_at = utc_now_iso()
            return

        with self.lock:
            self._apply_payload_locked(payload, increment_run_count=True)

    def _apply_payload_locked(self, payload: dict[str, object], increment_run_count: bool) -> None:
        generated_at = str(payload.get("generated_at") or utc_now_iso())
        self.payload = payload
        self.refresh.status = "idle"
        self.refresh.last_completed_at = generated_at
        self.refresh.last_source_mode = str(payload.get("source_mode", "unknown"))
        self.refresh.last_error = None
        live_error = summarize_live_error(payload)
        if self.refresh.last_source_mode == "tinyfish_web":
            self.refresh.last_live_success_at = generated_at
            self.refresh.last_live_success_summary = summarize_live_success(payload)
            self.refresh.last_live_error = None
        elif live_error:
            self.refresh.last_live_error_at = generated_at
            self.refresh.last_live_error = live_error
        if increment_run_count:
            self.refresh.run_count += 1
        append_refresh_log(
            "refresh completed: "
            f"source_mode={payload.get('source_mode')} "
            f"issues={payload.get('issue_batch', {}).get('metadata', {}).get('issue_count')} "
            f"recommendations={payload.get('recommendation_batch', {}).get('metadata', {}).get('recommendation_count')}"
        )

    def initialize_from_cache(self) -> None:
        cached_payload = read_cached_dashboard_payload()
        if cached_payload is None:
            return
        with self.lock:
            self._apply_payload_locked(cached_payload, increment_run_count=False)

    def ensure_hourly_refresh(self) -> None:
        with self.lock:
            should_queue = self.refresh.status != "refreshing" and should_refresh_payload(
                self.payload,
                self.refresh.auto_refresh_interval_seconds,
            )
        if should_queue:
            reason = "initial_scrape" if self.payload is None else "scheduled_refresh"
            self.queue_refresh(reason=reason)


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
            RUNTIME.ensure_hourly_refresh()
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
        time.sleep(min(interval_seconds, 30))
        RUNTIME.reload_cached_payload()
        RUNTIME.ensure_hourly_refresh()


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
    RUNTIME.initialize_from_cache()
    RUNTIME.ensure_hourly_refresh()
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
