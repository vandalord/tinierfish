from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request


class TinyFishAPIError(RuntimeError):
    """Raised when the TinyFish API returns an error or an invalid payload."""


@dataclass(slots=True)
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
    default_proxy_config: dict[str, Any] = field(
        default_factory=lambda: {"enabled": False}
    )

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("TINYFISH_API_KEY")

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

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")

                parsed = json.loads(body)
                if parsed.get("status") == "FAILED" or parsed.get("error"):
                    raise TinyFishAPIError(f"TinyFish run failed: {parsed.get('error')}")

                return parsed
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = TinyFishAPIError(f"TinyFish HTTP {exc.code}: {detail}")
            except error.URLError as exc:
                last_error = TinyFishAPIError(f"TinyFish network error: {exc.reason}")
            except TimeoutError as exc:
                last_error = TinyFishAPIError("TinyFish request timed out.")
            except json.JSONDecodeError as exc:
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
