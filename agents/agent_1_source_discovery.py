from __future__ import annotations

from dataclasses import dataclass, field
import os
from urllib.parse import urlparse

from agents.shared.models import SourceBatch, SourceRecord
from agents.shared.tinyfish import TinyFishAPIError, TinyFishWebAgentClient


@dataclass
class SourceSeed:
    url: str
    publisher: str
    region: str
    goal: str


@dataclass
class SourceDiscoveryConfig:
    allowed_domains: set[str] = field(
        default_factory=lambda: {
            "reuters.com",
            "bloomberg.com",
            "straitstimes.com",
            "channelnewsasia.com",
            "maritime-executive.com",
            "lloydslist.com",
            "seatrade-maritime.com",
            "ifw-net.com",
            "splash247.com",
        }
    )
    blocked_extensions: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".pdf",
        ".mp4",
    )
    supply_chain_terms: tuple[str, ...] = (
        "supply chain",
        "logistics",
        "shipping",
        "port",
        "freight",
        "food security",
        "produce",
        "vegetable",
        "import",
        "export",
        "strike",
        "storm",
        "drought",
    )
    batch_frequency: str = "hourly"
    max_articles_per_source: int = 2
    max_live_seed_attempts: int = 1
    source_seeds: tuple[SourceSeed, ...] = (
        SourceSeed(
            url="https://www.channelnewsasia.com/asia",
            publisher="Channel NewsAsia",
            region="Asia",
            goal=(
                "Extract up to 5 recent article links from this page that are about "
                "supply chain disruption, logistics delays, food imports, weather damage, "
                "port congestion, shipping disruption, strikes, or agricultural shortages "
                "relevant to Singapore or Southeast Asia. Respond only as JSON with "
                '{"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.reuters.com/world/asia-pacific/",
            publisher="Reuters",
            region="Asia",
            goal=(
                "Extract up to 5 recent Reuters article links from this page about "
                "food supply, logistics disruptions, weather shocks, port issues, freight, "
                "or trade disruptions relevant to Asia or Singapore. Respond only as JSON "
                'with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.maritime-executive.com/",
            publisher="The Maritime Executive",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page specifically about "
                "port congestion, shipping delays, strikes, route disruption, or cargo risk "
                "that could affect food or container supply chains in Asia. Respond only as JSON "
                'with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.seatrade-maritime.com/",
            publisher="Seatrade Maritime",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page about maritime logistics, "
                "port disruption, vessel congestion, weather impacts, or trade routes affecting "
                "Asia. Respond only as JSON with "
                '{"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
    )


class SourceDiscoveryAgent:
    """
    Agent 1:
    Filters scraped URLs into a trusted, supply-chain-focused source batch.
    """

    def __init__(
        self,
        config: SourceDiscoveryConfig | None = None,
        tinyfish_client: TinyFishWebAgentClient | None = None,
    ) -> None:
        self.config = config or SourceDiscoveryConfig()
        self.tinyfish_client = tinyfish_client or TinyFishWebAgentClient()

    def run(
        self,
        batch_id: str,
        candidates: list[dict[str, str]] | None = None,
    ) -> SourceBatch:
        source_mode = "seeded_input"
        live_errors: list[str] = []
        if candidates is None:
            candidates, source_mode, live_errors = self._collect_live_candidates()

        valid_sources: list[SourceRecord] = []
        rejected_count = 0
        seen_urls: set[str] = set()

        for candidate in candidates:
            if not self._is_valid_candidate(candidate):
                rejected_count += 1
                continue

            url = candidate["url"]
            if url in seen_urls:
                rejected_count += 1
                continue
            seen_urls.add(url)

            valid_sources.append(
                SourceRecord(
                    url=url,
                    title=candidate["title"],
                    publisher=candidate["publisher"],
                    summary=candidate["summary"],
                    region=candidate.get("region", "Unknown"),
                    score=self._score_candidate(candidate),
                    tags=self._extract_tags(candidate),
                )
            )

        return SourceBatch(
            batch_id=batch_id,
            metadata={
                "agent": "agent_1_source_discovery",
                "batch_frequency": self.config.batch_frequency,
                "source_mode": source_mode,
                "live_seed_attempts": self.config.max_live_seed_attempts,
                "candidate_count": len(candidates),
                "accepted_count": len(valid_sources),
                "rejected_count": rejected_count,
                "live_errors": live_errors[:5],
            },
            sources=sorted(valid_sources, key=lambda source: source.score, reverse=True),
        )

    def _collect_live_candidates(self) -> tuple[list[dict[str, str]], str, list[str]]:
        max_seed_attempts = max(
            1,
            int(os.getenv("TINYFISH_MAX_SOURCE_SEEDS", str(self.config.max_live_seed_attempts))),
        )
        live_errors: list[str] = []
        if self.tinyfish_client.is_configured:
            collected: list[dict[str, str]] = []
            for seed in self.config.source_seeds[:max_seed_attempts]:
                try:
                    result = self.tinyfish_client.extract_json(seed.url, seed.goal)
                except TinyFishAPIError as exc:
                    live_errors.append(f"{seed.publisher}: {exc}")
                    continue
                collected.extend(self._normalize_tinyfish_articles(seed, result))

            if collected:
                return collected, "tinyfish_web", live_errors

        if not self.tinyfish_client.is_configured:
            live_errors.append("TinyFish source discovery skipped because TINYFISH_API_KEY is not configured.")

        return self._fallback_candidates(), "fallback_demo", live_errors

    def _normalize_tinyfish_articles(
        self,
        seed: SourceSeed,
        result: dict[str, object],
    ) -> list[dict[str, str]]:
        raw_articles = result.get("articles")
        if not isinstance(raw_articles, list):
            return []

        normalized: list[dict[str, str]] = []
        for raw_article in raw_articles[: self.config.max_articles_per_source]:
            if not isinstance(raw_article, dict):
                continue

            url = str(raw_article.get("url", "")).strip()
            title = str(raw_article.get("title", "")).strip()
            summary = str(raw_article.get("summary", "")).strip()
            region = str(raw_article.get("region", "")).strip() or seed.region
            if not url or not title:
                continue

            normalized.append(
                {
                    "url": url,
                    "title": title,
                    "publisher": seed.publisher,
                    "summary": summary,
                    "region": region,
                }
            )

        return normalized

    def _fallback_candidates(self) -> list[dict[str, str]]:
        return [
            {
                "url": "https://www.reuters.com/world/asia-pacific/malaysia-floods-hit-vegetable-supply-chain-2026-03-27/",
                "title": "Malaysia floods hit vegetable supply chain into Singapore",
                "publisher": "Reuters",
                "summary": "Flooding disrupted farms and trucking routes, raising concerns over vegetable shortages and logistics delays.",
                "region": "Malaysia",
            },
            {
                "url": "https://www.channelnewsasia.com/asia/port-strike-thailand-freight-delay-food-imports-2026",
                "title": "Thai port strike causes freight congestion for food imports",
                "publisher": "Channel NewsAsia",
                "summary": "A port strike and vessel backlog are delaying produce and seafood shipments around Southeast Asia.",
                "region": "Thailand",
            },
            {
                "url": "https://www.straitstimes.com/asia/australian-heatwave-risks-fruit-harvests-for-exporters",
                "title": "Australian heatwave risks fruit harvests for regional exporters",
                "publisher": "The Straits Times",
                "summary": "A severe heatwave is stressing fruit harvests and cold-chain planning for importers across Asia.",
                "region": "Australia",
            },
        ]

    def _is_valid_candidate(self, candidate: dict[str, str]) -> bool:
        url = candidate.get("url", "").strip()
        title = candidate.get("title", "").lower()
        summary = candidate.get("summary", "").lower()

        if not url or not title:
            return False

        if url.lower().endswith(self.config.blocked_extensions):
            return False

        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        if domain not in self.config.allowed_domains:
            return False

        searchable_text = " ".join((title, summary))
        return any(term in searchable_text for term in self.config.supply_chain_terms)

    def _score_candidate(self, candidate: dict[str, str]) -> float:
        text = " ".join(
            (candidate.get("title", ""), candidate.get("summary", ""))
        ).lower()
        hits = sum(1 for term in self.config.supply_chain_terms if term in text)
        return min(1.0, 0.15 * hits + 0.2)

    def _extract_tags(self, candidate: dict[str, str]) -> list[str]:
        text = " ".join(
            (candidate.get("title", ""), candidate.get("summary", ""))
        ).lower()
        return [term for term in self.config.supply_chain_terms if term in text]
