from __future__ import annotations

from dataclasses import dataclass, field
import os
from urllib.parse import urlparse

from agents.shared.models import SourceBatch, SourceRecord
from agents.shared.tinyfish import TinyFishAPIError, TinyFishWebAgentClient


@dataclass(slots=True)
class SourceSeed:
    url: str
    publisher: str
    region: str
    goal: str


@dataclass(slots=True)
class SourceDiscoveryConfig:
    allowed_domains: set[str] = field(
        default_factory=lambda: {
            "reuters.com",
            "bloomberg.com",
            "nikkei.com",
            "straitstimes.com",
            "channelnewsasia.com",
            "scmp.com",
            "theloadstar.com",
            "freightwaves.com",
            "gcaptain.com",
            "bangkokpost.com",
            "reliefweb.int",
            "fao.org",
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
        "transport",
        "cargo",
        "food security",
        "produce",
        "vegetable",
        "grain",
        "container",
        "cold chain",
        "import",
        "export",
        "strike",
        "storm",
        "drought",
    )
    batch_frequency: str = "hourly"
    max_articles_per_source: int = 4
    max_live_seed_attempts: int = 8
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
            url="https://www.straitstimes.com/asia",
            publisher="The Straits Times",
            region="Asia",
            goal=(
                "Extract up to 5 recent article links from this page about food imports, "
                "shipping delays, logistics disruptions, agricultural weather damage, "
                "trade bottlenecks, or supply risk relevant to Singapore or Southeast Asia. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.scmp.com/topics/supply-chain",
            publisher="South China Morning Post",
            region="Asia",
            goal=(
                "Extract up to 5 recent article links from this topic page about supply chain disruption, "
                "shipping delays, logistics bottlenecks, energy transport, or import risks relevant to Asia. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://asia.nikkei.com/Economy",
            publisher="Nikkei Asia",
            region="Asia",
            goal=(
                "Extract up to 5 recent article links from this page about Asian trade, logistics, food imports, "
                "shipping, manufacturing disruption, or supply chain risk relevant to Singapore and Southeast Asia. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
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
        SourceSeed(
            url="https://splash247.com/",
            publisher="Splash247",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page about shipping disruption, "
                "port congestion, rerouting, vessel delay, or freight risk relevant to Asia. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://theloadstar.com/",
            publisher="The Loadstar",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page about air cargo, ocean freight, "
                "container disruption, port operations, or supply-chain bottlenecks affecting Asia. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.freightwaves.com/",
            publisher="FreightWaves",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page about freight markets, "
                "shipping disruption, logistics bottlenecks, container shortages, or supply chain risk "
                "relevant to food and consumer imports in Asia. Respond only as JSON with "
                '{"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://gcaptain.com/",
            publisher="gCaptain",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page about maritime incidents, port closures, "
                "groundings, cargo disruption, or shipping routes affecting Asia. Respond only as JSON with "
                '{"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.fao.org/newsroom/en/",
            publisher="FAO Newsroom",
            region="Global",
            goal=(
                "Extract up to 5 recent article links from this page about food price spikes, cereal markets, "
                "agricultural weather shocks, food insecurity, or import-related food supply issues relevant to Asia. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.fao.org/giews/en/",
            publisher="FAO GIEWS",
            region="Global",
            goal=(
                "Extract up to 5 recent alert or report links from this page about crop failures, drought, floods, "
                "food supply warnings, or import pressure that could affect regional sourcing into Singapore. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://www.fao.org/giews/food-prices/home/en/",
            publisher="FAO FPMA",
            region="Global",
            goal=(
                "Extract up to 5 recent links from this page about food price monitoring, staple price spikes, "
                "market stress, or commodity supply warnings relevant to Asia. Respond only as JSON with "
                '{"articles":[{"url":"","title":"","summary":"","region":""}]}.'
            ),
        ),
        SourceSeed(
            url="https://reliefweb.int/updates?view=reports",
            publisher="ReliefWeb",
            region="Global",
            goal=(
                "Extract up to 5 recent report links from this page about floods, drought, storms, conflict, "
                "or food security emergencies in Asia or nearby sourcing regions that could disrupt imports into Singapore. "
                'Respond only as JSON with {"articles":[{"url":"","title":"","summary":"","region":""}]}.'
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
        if candidates is None:
            candidates, source_mode = self._collect_live_candidates()

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
            },
            sources=sorted(valid_sources, key=lambda source: source.score, reverse=True),
        )

    def _collect_live_candidates(self) -> tuple[list[dict[str, str]], str]:
        max_seed_attempts = max(
            1,
            int(os.getenv("TINYFISH_MAX_SOURCE_SEEDS", str(self.config.max_live_seed_attempts))),
        )
        if self.tinyfish_client.is_configured:
            collected = self._collect_live_candidates_async(
                self.config.source_seeds[:max_seed_attempts]
            )

            if collected:
                return collected, "tinyfish_web"

        return self._fallback_candidates(), "fallback_demo"

    def _collect_live_candidates_async(
        self,
        seeds: tuple[SourceSeed, ...] | list[SourceSeed],
    ) -> list[dict[str, str]]:
        tasks = [{"url": seed.url, "goal": seed.goal} for seed in seeds]
        if not tasks:
            return []

        try:
            responses = self.tinyfish_client.run_many_concurrent(tasks)
        except TinyFishAPIError:
            return []

        collected: list[dict[str, str]] = []
        for seed, response in zip(seeds, responses):
            result = response.get("result") or response.get("resultJson")
            if response.get("status") != "COMPLETED" or not isinstance(result, dict):
                continue
            collected.extend(self._normalize_tinyfish_articles(seed, result))

        return collected

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
        domain = parsed.netloc.removeprefix("www.")
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
