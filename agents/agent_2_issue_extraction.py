from __future__ import annotations

from dataclasses import dataclass, field
import os

from agents.shared.models import (
    IssueBatch,
    IssueRecord,
    IssueSeverity,
    KeywordExtraction,
    RiskType,
    SourceBatch,
)
from agents.shared.tinyfish import TinyFishAPIError, TinyFishWebAgentClient
from tinyfish import AsyncTinyFish


REGION_COORDINATES: dict[str, tuple[float, float]] = {
    "Singapore": (1.3521, 103.8198),
    "Malaysia": (4.2105, 101.9758),
    "Indonesia": (-0.7893, 113.9213),
    "Thailand": (15.87, 100.9925),
    "Vietnam": (14.0583, 108.2772),
    "Australia": (-25.2744, 133.7751),
    "India": (20.5937, 78.9629),
    "China": (35.8617, 104.1954),
}


@dataclass(slots=True)
class TinyFishAPIClient:
    """
    TinyFish-backed issue extraction with a local heuristic fallback.
    """

    api_key: str | None = None
    browser_profile: str = "lite"
    web_client: TinyFishWebAgentClient = field(init=False)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("TINYFISH_API_KEY")
        self.web_client = TinyFishWebAgentClient(
            api_key=self.api_key,
            browser_profile=self.browser_profile,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def extract_keywords(
        self,
        title: str,
        summary: str,
        article_url: str | None = None,
        region_hint: str | None = None,
    ) -> dict[str, object]:
        if self.web_client.is_configured and article_url:
            try:
                result = self.web_client.extract_json(
                    url=article_url,
                    goal=self.build_extraction_goal(),
                )
                normalized = self._normalize_tinyfish_result(result, title, summary, region_hint)
                normalized["engine"] = "tinyfish_web"
                normalized["live_error"] = None
                return normalized
            except TinyFishAPIError as exc:
                fallback = self._heuristic_extract(title, summary, region_hint)
                fallback["engine"] = "heuristic_fallback"
                fallback["live_error"] = str(exc)
                return fallback

        fallback = self._heuristic_extract(title, summary, region_hint)
        fallback["engine"] = "heuristic_fallback"
        fallback["live_error"] = None
        return fallback

    def build_extraction_goal(self) -> str:
        return (
            "Read this article and extract supply-chain disruption intelligence. "
            "Respond only as JSON with the exact shape "
            '{"summary":"","keywords":[],"negative_signals":[],"affected_products":[],"affected_regions":[],"risk_type":"weather","severity":"high","confidence":0.0}. '
            "Use risk_type from: weather, port_disruption, strike, conflict, policy, "
            "price_shock, disease, other. Use severity from: low, medium, high, critical. "
            "Focus on logistics bottlenecks, food imports, agriculture disruption, port issues, "
            "weather shocks, and operational impacts relevant to Singapore or Asia."
        )

    def _normalize_tinyfish_result(
        self,
        result: dict[str, object],
        title: str,
        summary: str,
        region_hint: str | None,
    ) -> dict[str, object]:
        keywords = self._coerce_string_list(result.get("keywords"))
        negative_signals = self._coerce_string_list(result.get("negative_signals"))
        affected_products = self._coerce_string_list(result.get("affected_products"))
        affected_regions = self._coerce_string_list(result.get("affected_regions"))

        risk_value = str(result.get("risk_type", "other")).lower()
        severity_value = str(result.get("severity", "medium")).lower()
        confidence_value = result.get("confidence", 0.7)
        narrative = str(result.get("summary", "")).strip() or summary

        if region_hint and region_hint not in affected_regions:
            affected_regions.insert(0, region_hint)

        return {
            "keywords": keywords or self._coerce_keywords_from_text(title, summary),
            "negative_signals": negative_signals,
            "affected_products": affected_products or ["mixed food supply"],
            "affected_regions": affected_regions or [region_hint or "Singapore"],
            "risk_type": self._to_risk_type(risk_value),
            "severity": self._to_severity(severity_value),
            "confidence": self._to_confidence(confidence_value),
            "narrative": narrative,
        }

    def _heuristic_extract(
        self,
        title: str,
        summary: str,
        region_hint: str | None,
    ) -> dict[str, object]:
        text = f"{title} {summary}".lower()

        negative_signals = [
            term
            for term in (
                "delay",
                "shortage",
                "strike",
                "flood",
                "drought",
                "storm",
                "congestion",
                "ban",
                "outbreak",
            )
            if term in text
        ]

        products = [
            term
            for term in (
                "vegetable",
                "rice",
                "egg",
                "seafood",
                "poultry",
                "fruit",
            )
            if term in text
        ] or ["mixed food supply"]

        if "storm" in text or "flood" in text or "drought" in text:
            risk_type = RiskType.WEATHER
        elif "strike" in text:
            risk_type = RiskType.STRIKE
        elif "port" in text or "congestion" in text:
            risk_type = RiskType.PORT_DISRUPTION
        elif "ban" in text or "policy" in text:
            risk_type = RiskType.POLICY
        elif "outbreak" in text:
            risk_type = RiskType.DISEASE
        else:
            risk_type = RiskType.OTHER

        severity = IssueSeverity.HIGH if len(negative_signals) >= 2 else IssueSeverity.MEDIUM
        if "shortage" in text or "ban" in text:
            severity = IssueSeverity.CRITICAL

        keywords = sorted(set(products + negative_signals + [risk_type.value]))
        regions = [region for region in REGION_COORDINATES if region.lower() in text]
        if region_hint and region_hint in REGION_COORDINATES and region_hint not in regions:
            regions.insert(0, region_hint)

        return {
            "keywords": keywords,
            "negative_signals": negative_signals,
            "affected_products": products,
            "affected_regions": regions or [region_hint or "Singapore"],
            "risk_type": risk_type,
            "severity": severity,
            "confidence": 0.8 if negative_signals else 0.55,
            "narrative": (
                "Potential supply-chain disruption detected from trusted media coverage."
            ),
        }

    def _coerce_string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _to_risk_type(self, value: str) -> RiskType:
        try:
            return RiskType(value)
        except ValueError:
            return RiskType.OTHER

    def _to_severity(self, value: str) -> IssueSeverity:
        try:
            return IssueSeverity(value)
        except ValueError:
            return IssueSeverity.MEDIUM

    def _to_confidence(self, value: object) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.7
        return max(0.0, min(1.0, confidence))

    def _coerce_keywords_from_text(self, title: str, summary: str) -> list[str]:
        text = f"{title} {summary}".lower()
        candidates = (
            "supply chain",
            "logistics",
            "weather",
            "port",
            "shipping",
            "food imports",
            "agriculture",
            "freight",
        )
        return [candidate for candidate in candidates if candidate in text]


class IssueExtractionAgent:
    """
    Agent 2:
    Uses TinyFish keyword extraction to convert source articles into structured issues.
    """

    def __init__(self, tinyfish_client: TinyFishAPIClient | None = None) -> None:
        self.tinyfish_client = tinyfish_client or TinyFishAPIClient()

    def run(self, batch_id: str, source_batch: SourceBatch) -> IssueBatch:
        issues: list[IssueRecord] = []
        live_issue_count = 0
        live_errors: list[str] = []
        async_extraction_payloads, async_attempted = self._extract_async_payloads(source_batch)

        for index, source in enumerate(source_batch.sources, start=1):
            extraction_payload = async_extraction_payloads.get(source.url)
            if extraction_payload is None:
                if async_attempted:
                    extraction_payload = self.tinyfish_client._heuristic_extract(
                        source.title,
                        source.summary,
                        source.region,
                    ) | {
                        "engine": "heuristic_fallback",
                        "live_error": "Async TinyFish extraction did not return a completed result for this article.",
                    }
                else:
                    extraction_payload = self.tinyfish_client.extract_keywords(
                        title=source.title,
                        summary=source.summary,
                        article_url=source.url,
                        region_hint=source.region,
                    )
            if extraction_payload.get("engine") == "tinyfish_web":
                live_issue_count += 1
            if extraction_payload.get("live_error"):
                live_errors.append(str(extraction_payload["live_error"]))
            region = self._select_region(source.region, extraction_payload["affected_regions"])
            latitude, longitude = REGION_COORDINATES.get(
                region, REGION_COORDINATES["Singapore"]
            )

            extraction = KeywordExtraction(
                keywords=list(extraction_payload["keywords"]),
                negative_signals=list(extraction_payload["negative_signals"]),
                affected_products=list(extraction_payload["affected_products"]),
                affected_regions=list(extraction_payload["affected_regions"]),
                risk_type=extraction_payload["risk_type"],
                severity=extraction_payload["severity"],
                confidence=float(extraction_payload["confidence"]),
                narrative=str(extraction_payload["narrative"]),
            )

            issues.append(
                IssueRecord(
                    issue_id=f"{batch_id}-ISSUE-{index:03d}",
                    source_url=source.url,
                    title=source.title,
                    region=region,
                    latitude=latitude,
                    longitude=longitude,
                    extraction=extraction,
                )
            )

        return IssueBatch(
            batch_id=batch_id,
            metadata={
                "agent": "agent_2_issue_extraction",
                "source_batch_id": source_batch.batch_id,
                "issue_count": len(issues),
                "live_issue_count": live_issue_count,
                "fallback_issue_count": len(issues) - live_issue_count,
                "live_errors": live_errors[:5],
            },
            issues=issues,
        )

    def _extract_async_payloads(
        self,
        source_batch: SourceBatch,
    ) -> tuple[dict[str, dict[str, object]], bool]:
        if not self.tinyfish_client.web_client.is_configured:
            return {}, False

        tasks = [
            {"url": source.url, "goal": self.tinyfish_client.build_extraction_goal()}
            for source in source_batch.sources
        ]
        if not tasks:
            return {}, False

        try:
            responses = self.tinyfish_client.web_client.run_many_concurrent(tasks)
        except TinyFishAPIError:
            return {}, True

        payloads: dict[str, dict[str, object]] = {}
        for source, response in zip(source_batch.sources, responses):
            result = response.get("result") or response.get("resultJson")
            if response.get("status") != "COMPLETED" or not isinstance(result, dict):
                continue
            payloads[source.url] = self.tinyfish_client._normalize_tinyfish_result(
                result,
                source.title,
                source.summary,
                source.region,
            ) | {"engine": "tinyfish_web", "live_error": None}

        return payloads, True

    def _select_region(self, source_region: str, affected_regions: list[str]) -> str:
        if source_region in REGION_COORDINATES:
            return source_region

        for region in affected_regions:
            if region in REGION_COORDINATES and region != "Singapore":
                return region

        for region in affected_regions:
            if region in REGION_COORDINATES:
                return region

        return "Singapore"
