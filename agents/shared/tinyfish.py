from __future__ import annotations

import json
import os
import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request


class TinyFishAPIError(RuntimeError):
    """Raised when the TinyFish API returns an error or an invalid payload."""


@dataclass
class TinyFishWebAgentClient:
    """
    Minimal TinyFish Web Agent client using the documented synchronous endpoint.
    """

    api_key: str | None = None
    base_url: str = "https://agent.tinyfish.ai/v1/automation/run"
    browser_profile: str = "lite"
    timeout_seconds: int = 90
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    verify_ssl: bool = True
    ca_bundle_path: str | None = None
    allow_insecure_fallback: bool = True
    default_proxy_config: dict[str, Any] = field(
        default_factory=lambda: {"enabled": False}
    )

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("TINYFISH_API_KEY")
        self.timeout_seconds = self._read_timeout_seconds()
        self.verify_ssl = self._read_verify_ssl_flag()
        self.ca_bundle_path = (
            self.ca_bundle_path
            or os.getenv("TINYFISH_CA_BUNDLE")
            or os.getenv("SSL_CERT_FILE")
            or os.getenv("REQUESTS_CA_BUNDLE")
        )
        self.allow_insecure_fallback = self._read_allow_insecure_fallback_flag()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def run(self, url: str, goal: str) -> dict[str, Any]:
        if not self.api_key:
            raise TinyFishAPIError("TINYFISH_API_KEY is not configured.")

        payload = {
            "url": url,
            "goal": goal,
            "browser_profile": self.browser_profile,
            "proxy_config": self.default_proxy_config,
            "api_integration": "cookedtinyfish",
        }

        req = request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
            },
            method="POST",
        )

        ssl_context = self._build_ssl_context(verify_ssl=self.verify_ssl)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                body = self._execute_request(req, ssl_context)

                parsed = json.loads(body)
                if parsed.get("status") == "FAILED" or parsed.get("error"):
                    raise TinyFishAPIError(f"TinyFish run failed: {parsed.get('error')}")

                return parsed
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

    def _execute_request(
        self,
        req: request.Request,
        ssl_context: ssl.SSLContext,
    ) -> str:
        try:
            with request.urlopen(
                req,
                timeout=self.timeout_seconds,
                context=ssl_context,
            ) as response:
                return response.read().decode("utf-8")
        except error.URLError as exc:
            reason = str(exc.reason)
            if self._is_certificate_error(reason) and self._should_retry_insecure(ssl_context):
                fallback_context = self._build_ssl_context(verify_ssl=False)
                with request.urlopen(
                    req,
                    timeout=self.timeout_seconds,
                    context=fallback_context,
                ) as response:
                    return response.read().decode("utf-8")
            raise

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
        )
