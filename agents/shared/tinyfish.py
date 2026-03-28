from __future__ import annotations

import asyncio
import json
import os
<<<<<<< HEAD
import socket
import ssl
=======
>>>>>>> f82097e878af2ba4c3a5e6f5998b22a20b02c73a
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request

try:
    from tinyfish import AsyncTinyFish
except ImportError:  # pragma: no cover - SDK is optional at runtime
    AsyncTinyFish = None


class TinyFishAPIError(RuntimeError):
    """Raised when the TinyFish API returns an error or an invalid payload."""


@dataclass(slots=True)
class TinyFishWebAgentClient:
    """
    Minimal TinyFish Web Agent client using the documented synchronous endpoint.
    """

    api_key: str | None = None
    base_url: str = "https://agent.tinyfish.ai/v1/automation/run"
    async_base_url: str = "https://agent.tinyfish.ai/v1/automation/run-async"
    runs_base_url: str = "https://agent.tinyfish.ai/v1/runs"
    browser_profile: str = "lite"
    timeout_seconds: int = 90
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    poll_interval_seconds: float = 10.0
    max_poll_seconds: int = 240
    max_concurrent_runs: int = 4
    default_proxy_config: dict[str, Any] = field(
        default_factory=lambda: {"enabled": False}
    )

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("TINYFISH_API_KEY")
<<<<<<< HEAD
        self.timeout_seconds = self._read_timeout_seconds()
        self.verify_ssl = self._read_verify_ssl_flag()
        self.ca_bundle_path = (
            self.ca_bundle_path
            or os.getenv("TINYFISH_CA_BUNDLE")
            or os.getenv("SSL_CERT_FILE")
            or os.getenv("REQUESTS_CA_BUNDLE")
        )
        self.allow_insecure_fallback = self._read_allow_insecure_fallback_flag()
=======
>>>>>>> f82097e878af2ba4c3a5e6f5998b22a20b02c73a

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def run(self, url: str, goal: str) -> dict[str, Any]:
        if not self.api_key:
            raise TinyFishAPIError("TINYFISH_API_KEY is not configured.")

        payload = self._build_payload(url=url, goal=goal)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                parsed = self._request_json(
                    self.base_url,
                    payload=payload,
                    method="POST",
                )
                if parsed.get("status") == "FAILED" or parsed.get("error"):
                    raise TinyFishAPIError(f"TinyFish run failed: {parsed.get('error')}")

                return parsed
<<<<<<< HEAD
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = TinyFishAPIError(f"TinyFish HTTP {exc.code}: {detail}")
            except error.URLError as exc:
                reason = str(exc.reason)
                last_error = TinyFishAPIError(
                    self._format_network_error(reason, ssl_context)
                )
            except (TimeoutError, socket.timeout):
                last_error = TinyFishAPIError(
                    f"TinyFish read operation timed out after {self.timeout_seconds}s."
                )
                break
            except json.JSONDecodeError:
                last_error = TinyFishAPIError("TinyFish returned invalid JSON.")
=======
            except TinyFishAPIError as exc:
                last_error = exc
>>>>>>> f82097e878af2ba4c3a5e6f5998b22a20b02c73a

            if attempt <= self.max_retries:
                time.sleep(self.retry_backoff_seconds * attempt)

        if last_error is None:
            raise TinyFishAPIError("TinyFish request failed unexpectedly.")
        raise last_error

    def extract_json(self, url: str, goal: str) -> dict[str, Any]:
        response = self.run(url=url, goal=goal)
        result = response.get("result") or response.get("resultJson")
        if not isinstance(result, dict):
            raise TinyFishAPIError("TinyFish result did not contain a JSON object.")
        return result

    def run_many_concurrent(self, tasks: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not self.api_key:
            raise TinyFishAPIError("TINYFISH_API_KEY is not configured.")
        if AsyncTinyFish is None:
            raise TinyFishAPIError("AsyncTinyFish SDK is not installed.")
        return asyncio.run(self._run_many_concurrent(tasks))

<<<<<<< HEAD
    def _build_ssl_context(self, verify_ssl: bool) -> ssl.SSLContext:
        if not verify_ssl:
            return ssl._create_unverified_context()

        if self.ca_bundle_path:
            return ssl.create_default_context(cafile=self.ca_bundle_path)

        try:
            import certifi
        except ImportError:
            return ssl.create_default_context()

        return ssl.create_default_context(cafile=certifi.where())

    def _read_verify_ssl_flag(self) -> bool:
        value = os.getenv("TINYFISH_VERIFY_SSL")
        if value is None:
            insecure_value = os.getenv("TINYFISH_ALLOW_INSECURE_SSL")
            if insecure_value is None:
                return True
            return insecure_value.strip().lower() not in {"1", "true", "yes", "on"}

        return value.strip().lower() not in {"0", "false", "no", "off"}

    def _read_allow_insecure_fallback_flag(self) -> bool:
        value = os.getenv("TINYFISH_ALLOW_INSECURE_SSL_FALLBACK")
        if value is None:
            return True
        return value.strip().lower() not in {"0", "false", "no", "off"}

    def _read_timeout_seconds(self) -> int:
        value = os.getenv("TINYFISH_TIMEOUT_SECONDS")
        if value is None:
            return self.timeout_seconds

        try:
            parsed = int(value)
        except ValueError:
            return self.timeout_seconds

        return max(10, parsed)

    def _format_network_error(
        self,
        reason: str,
        ssl_context: ssl.SSLContext,
    ) -> str:
        if not self._is_certificate_error(reason):
            return f"TinyFish network error: {reason}"

        if not self.verify_ssl:
            return (
                "TinyFish network error: SSL verification is disabled, but the HTTPS "
                f"request still failed ({reason})."
            )

        if self.ca_bundle_path:
            return (
                "TinyFish SSL verification failed using the configured CA bundle "
                f"({self.ca_bundle_path}): {reason}"
            )

        if ssl_context.verify_mode == ssl.CERT_REQUIRED:
            return (
                "TinyFish SSL verification failed. Install or configure a trusted CA bundle, "
                "or set TINYFISH_CA_BUNDLE/SSL_CERT_FILE to your certificate path. "
                "For local demos you can also allow insecure fallback with "
                "TINYFISH_ALLOW_INSECURE_SSL_FALLBACK=1. "
                f"Original error: {reason}"
            )

        return f"TinyFish network error: {reason}"

    def _is_certificate_error(self, reason: str) -> bool:
        return "certificate_verify_failed" in reason.lower()

    def _should_retry_insecure(self, ssl_context: ssl.SSLContext) -> bool:
        return (
            self.verify_ssl
            and self.allow_insecure_fallback
            and ssl_context.verify_mode == ssl.CERT_REQUIRED
=======
    async def _run_many_concurrent(self, tasks: list[dict[str, str]]) -> list[dict[str, Any]]:
        client = AsyncTinyFish(
            api_key=self.api_key,
            base_url=self.base_url.removesuffix("/v1/automation/run"),
            timeout=float(self.timeout_seconds),
            max_retries=self.max_retries,
>>>>>>> f82097e878af2ba4c3a5e6f5998b22a20b02c73a
        )
        semaphore = asyncio.Semaphore(max(1, self.max_concurrent_runs))

        async def run_task(task: dict[str, str]) -> dict[str, Any]:
            async with semaphore:
                try:
                    response = await client.agent.run(
                        url=task["url"],
                        goal=task["goal"],
                        browser_profile=self.browser_profile,
                    )
                except Exception as exc:  # noqa: BLE001
                    return {
                        "status": "FAILED",
                        "run_id": None,
                        "result": None,
                        "error": {"message": str(exc)},
                    }
                return self._normalize_sdk_response(response)

        try:
            return await asyncio.gather(*(run_task(task) for task in tasks))
        finally:
            await self._close_async_client(client)

    def start_async(self, url: str, goal: str) -> str:
        if not self.api_key:
            raise TinyFishAPIError("TINYFISH_API_KEY is not configured.")

        parsed = self._request_json(
            self.async_base_url,
            payload=self._build_payload(url=url, goal=goal),
            method="POST",
        )
        run_id = parsed.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise TinyFishAPIError("TinyFish async run did not return a run_id.")
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any]:
        if not self.api_key:
            raise TinyFishAPIError("TINYFISH_API_KEY is not configured.")

        return self._request_json(
            f"{self.runs_base_url}/{run_id}",
            payload=None,
            method="GET",
        )

    def wait_for_runs(
        self,
        run_ids: list[str],
        timeout_seconds: int | None = None,
    ) -> dict[str, dict[str, Any]]:
        pending = set(run_ids)
        completed: dict[str, dict[str, Any]] = {}
        deadline = time.monotonic() + (timeout_seconds or self.max_poll_seconds)
        terminal_statuses = {"COMPLETED", "FAILED", "CANCELLED"}

        while pending and time.monotonic() < deadline:
            with ThreadPoolExecutor(max_workers=min(8, len(pending))) as executor:
                future_to_run_id = {
                    executor.submit(self.get_run, run_id): run_id for run_id in pending
                }
                for future in as_completed(future_to_run_id):
                    run_id = future_to_run_id[future]
                    try:
                        item = future.result()
                    except TinyFishAPIError:
                        continue
                    status = item.get("status")
                    if status in terminal_statuses:
                        completed[run_id] = item
                        pending.discard(run_id)

            if pending:
                time.sleep(self.poll_interval_seconds)

        return completed

    def _build_payload(self, url: str, goal: str) -> dict[str, Any]:
        return {
            "url": url,
            "goal": goal,
            "browser_profile": self.browser_profile,
            "proxy_config": self.default_proxy_config,
            "api_integration": "cookedtinyfish",
        }

    def _request_json(
        self,
        url: str,
        payload: dict[str, Any] | None,
        method: str,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key or "",
            },
            method=method,
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TinyFishAPIError(f"TinyFish HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise TinyFishAPIError(f"TinyFish network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TinyFishAPIError("TinyFish request timed out.") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise TinyFishAPIError("TinyFish returned invalid JSON.") from exc

        return parsed

    def _normalize_sdk_response(self, response: Any) -> dict[str, Any]:
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="python", by_alias=True)
        if isinstance(response, dict):
            return response
        return {
            "status": getattr(response, "status", None),
            "run_id": getattr(response, "run_id", None),
            "result": getattr(response, "result", None),
            "error": getattr(response, "error", None),
        }

    async def _close_async_client(self, client: Any) -> None:
        for method_name in ("aclose", "close"):
            method = getattr(client, method_name, None)
            if method is None:
                continue
            result = method()
            if asyncio.iscoroutine(result):
                await result
            return
