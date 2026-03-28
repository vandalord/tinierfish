from __future__ import annotations

from agents.shared.models import IssueBatch, Recommendation, RecommendationBatch, SupplierOption
from agents.shared.models import IssueRecord, RiskType

from agents.shared.models import IssueBatch, IssueRecord, Recommendation, RecommendationBatch, SupplierOption
from agents.shared.tinyfish import TinyFishAPIError, TinyFishWebAgentClient


COUNTRY_COORDINATES: dict[str, tuple[float, float]] = {
    "Singapore": (1.3521, 103.8198),
    "Malaysia": (4.2105, 101.9758),
    "Indonesia": (-0.7893, 113.9213),
    "Thailand": (15.87, 100.9925),
    "Vietnam": (14.0583, 108.2772),
    "Philippines": (12.8797, 121.774),
    "Australia": (-25.2744, 133.7751),
    "India": (20.5937, 78.9629),
    "China": (35.8617, 104.1954),
    "Japan": (36.2048, 138.2529),
    "South Korea": (35.9078, 127.7669),
    "Taiwan": (23.6978, 120.9605),
    "Myanmar": (21.9162, 95.956),
    "Cambodia": (12.5657, 104.991),
    "Laos": (19.8563, 102.4955),
    "Brunei": (4.5353, 114.7277),
    "New Zealand": (-40.9006, 174.886),
}

PRODUCT_ALIASES: dict[str, str] = {
    "vegetable": "vegetable",
    "vegetables": "vegetable",
    "produce": "vegetable",
    "greens": "vegetable",
    "fruit": "fruit",
    "fruits": "fruit",
    "rice": "rice",
    "grain": "rice",
    "grains": "rice",
    "egg": "egg",
    "eggs": "egg",
    "seafood": "seafood",
    "seafoods": "seafood",
    "fish": "seafood",
    "fishes": "seafood",
    "shrimp": "seafood",
    "prawn": "seafood",
    "prawns": "seafood",
    "poultry": "poultry",
    "chicken": "poultry",
    "mixed food supply": "mixed food supply",
    "food imports": "mixed food supply",
    "food supply": "mixed food supply",
}

ALL_PRODUCTS = ("vegetable", "fruit", "rice", "egg", "seafood", "poultry")

DEFAULT_SUPPLIERS = [
    SupplierOption(
        supplier_id="SUP-001",
        supplier_name="Johor Fresh Greens Cooperative",
        country="Malaysia",
        latitude=1.4927,
        longitude=103.7414,
        products=["vegetable", "fruit", "egg"],
        average_cost_index=1.0,
        reliability_score=0.88,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-002",
        supplier_name="Central Highlands Produce Network",
        country="Vietnam",
        latitude=12.6667,
        longitude=108.05,
        products=["vegetable", "fruit", "rice"],
        average_cost_index=1.12,
        reliability_score=0.9,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-003",
        supplier_name="Batam Cold Chain Alliance",
        country="Indonesia",
        latitude=1.1301,
        longitude=104.052,
        products=["seafood", "poultry", "egg"],
        average_cost_index=1.05,
        reliability_score=0.87,
        active_risk_tags=["weather", "monsoon"],
    ),
    SupplierOption(
        supplier_id="SUP-004",
        supplier_name="Mekong Delta Seafood Exchange",
        country="Vietnam",
        latitude=10.0452,
        longitude=105.7469,
        products=["seafood", "rice", "fruit"],
        average_cost_index=1.08,
        reliability_score=0.91,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-005",
        supplier_name="Queensland Agri Reserve",
        country="Australia",
        latitude=-20.9176,
        longitude=142.7028,
        products=["vegetable", "fruit", "poultry"],
        average_cost_index=1.24,
        reliability_score=0.94,
        active_risk_tags=["weather", "cyclone"],
    ),
    SupplierOption(
        supplier_id="SUP-006",
        supplier_name="Andhra Staple Foods",
        country="India",
        latitude=15.9129,
        longitude=79.74,
        products=["rice", "egg", "poultry"],
        average_cost_index=0.96,
        reliability_score=0.86,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-005",
        supplier_name="Batam Cold Chain Hub",
        country="Indonesia",
        latitude=1.0456,
        longitude=104.0305,
        products=["seafood", "mixed food supply", "general cargo"],
        average_cost_index=1.03,
        reliability_score=0.87,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-006",
        supplier_name="Penang Staples Exchange",
        country="Malaysia",
        latitude=5.4164,
        longitude=100.3327,
        products=["rice", "grain", "egg", "mixed food supply", "container capacity"],
        average_cost_index=1.01,
        reliability_score=0.89,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-007",
        supplier_name="Cebu Marine Foods Cluster",
        country="Philippines",
        latitude=10.3157,
        longitude=123.8854,
        products=["seafood", "mixed food supply", "general cargo"],
        average_cost_index=1.08,
        reliability_score=0.9,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-008",
        supplier_name="Colombo Rerouting Logistics Hub",
        country="Sri Lanka",
        latitude=6.9271,
        longitude=79.8612,
        products=["general cargo", "container capacity", "mixed food supply"],
        average_cost_index=1.07,
        reliability_score=0.93,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-009",
        supplier_name="Adelaide Fresh Produce Reserve",
        country="Australia",
        latitude=-34.9285,
        longitude=138.6007,
        products=["vegetable", "fruit", "mixed food supply"],
        average_cost_index=1.16,
        reliability_score=0.92,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-010",
        supplier_name="Johor Fuel Bunkering Reserve",
        country="Malaysia",
        latitude=1.4655,
        longitude=103.7578,
        products=["petrol", "diesel", "jet fuel", "fuel security", "energy logistics"],
        average_cost_index=1.05,
        reliability_score=0.91,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-011",
        supplier_name="Chennai Refined Fuels Terminal",
        country="India",
        latitude=13.0827,
        longitude=80.2707,
        products=["petrol", "diesel", "jet fuel", "fuel security", "energy logistics"],
        average_cost_index=1.09,
        reliability_score=0.93,
        active_risk_tags=[],
    ),
]

PRODUCT_ALIASES: dict[str, list[str]] = {
    "mixed food supply": [
        "mixed food supply",
        "vegetable",
        "fruit",
        "rice",
        "egg",
        "seafood",
        "poultry",
        "grain",
        "general cargo",
        "container capacity",
    ],
    "food imports": ["mixed food supply", "general cargo", "container capacity"],
    "logistics": ["general cargo", "container capacity", "mixed food supply"],
    "freight": ["general cargo", "container capacity", "mixed food supply"],
    "shipping": ["general cargo", "container capacity", "mixed food supply"],
    "transport": ["general cargo", "container capacity", "mixed food supply"],
    "produce": ["vegetable", "fruit", "mixed food supply"],
    "grain": ["grain", "rice", "mixed food supply"],
    "fuel security": ["petrol", "diesel", "jet fuel", "fuel security", "energy logistics"],
    "containerized trade": ["general cargo", "container capacity", "mixed food supply"],
    "global maritime cargo": ["general cargo", "container capacity", "mixed food supply"],
}


@dataclass
class TinyFishAlternativeSourcingClient:
    """
    TinyFish-backed sourcing recommendations with a heuristic fallback.
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

    def recommend(self, issue: IssueRecord) -> dict[str, object]:
        if not self.web_client.is_configured or not issue.source_url:
            return {
                "engine": "heuristic_fallback",
                "live_error": None if self.web_client.is_configured else "TINYFISH_API_KEY is not configured.",
                "recommendations": [],
            }

        try:
            result = self.web_client.extract_json(
                url=issue.source_url,
                goal=self._build_goal(issue),
            )
            return {
                "engine": "tinyfish_web",
                "live_error": None,
                "recommendations": self._normalize_result(issue, result),
            }
        except TinyFishAPIError as exc:
            return {
                "engine": "heuristic_fallback",
                "live_error": str(exc),
                "recommendations": [],
            }

    def _build_goal(self, issue: IssueRecord) -> str:
        products = ", ".join(issue.extraction.affected_products) or "mixed food supply"
        affected_regions = ", ".join(issue.extraction.affected_regions) or issue.region
        negative_signals = ", ".join(issue.extraction.negative_signals) or "general disruption"

        return (
            "Read this disruption article and recommend alternative sourcing options for Singapore. "
            "Use current web context if needed, but respond only as JSON with the exact shape "
            '{"recommendations":[{"strategy":"first_cheapest","product":"","supplier_name":"","country":"","products":[],"average_cost_index":1.0,"reliability_score":0.0,"active_risk_tags":[],"source_label":"","source_url":"","rationale":"","estimated_cost_delta_pct":0.0,"security_score":0.0}]}. '
            "Recommend up to 4 alternatives outside the affected countries and not exposed to the same disruption. "
            "Prefer nearby Asia-Pacific sourcing options when realistic. "
            "Use strategy only from: first_cheapest, first_secure. "
            f"Affected region anchor: {issue.region}. "
            f"Regions to avoid if possible: {affected_regions}. "
            f"Risk type: {issue.extraction.risk_type.value}. "
            f"Products to cover: {products}. "
            f"Negative signals: {negative_signals}. "
            "If a product is industrial rather than food, still recommend the most realistic alternative sourcing country or supplier network for Singapore importers."
        )

    def _normalize_result(
        self,
        issue: IssueRecord,
        result: dict[str, object],
    ) -> list[Recommendation]:
        raw_recommendations = result.get("recommendations")
        if not isinstance(raw_recommendations, list):
            return []

        normalized: list[Recommendation] = []
        seen_keys: set[tuple[str, str, str, str]] = set()
        blocked_countries = self._blocked_countries(issue)

        for index, item in enumerate(raw_recommendations, start=1):
            if not isinstance(item, dict):
                continue

            strategy = str(item.get("strategy", "first_secure")).strip().lower()
            if strategy not in {"first_cheapest", "first_secure"}:
                strategy = "first_secure"

            product = str(item.get("product", "")).strip()
            if not product:
                product = issue.extraction.affected_products[0] if issue.extraction.affected_products else "mixed food supply"

            country = self._clean_country(str(item.get("country", "")).strip())
            if not country or country in blocked_countries:
                continue

            supplier_name = str(item.get("supplier_name", "")).strip() or f"{country} Alternative Supply Network"
            dedupe_key = (strategy, product.lower(), supplier_name.lower(), country.lower())
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            latitude, longitude = COUNTRY_COORDINATES.get(country, (issue.latitude, issue.longitude))
            supplier_products = self._coerce_string_list(item.get("products")) or [product]
            estimated_cost_delta_pct = self._to_float(item.get("estimated_cost_delta_pct"), 0.0)
            average_cost_index = self._to_float(
                item.get("average_cost_index"),
                round(1.0 + (estimated_cost_delta_pct / 100.0), 3),
            )
            reliability_score = self._clamp(self._to_float(item.get("reliability_score"), 0.82))
            active_risk_tags = self._coerce_string_list(item.get("active_risk_tags"))
            security_score = self._clamp(
                self._to_float(item.get("security_score"), max(0.0, reliability_score - 0.08 * len(active_risk_tags)))
            )
            rationale = str(item.get("rationale", "")).strip() or (
                f"{supplier_name} in {country} is an online-researched alternative outside the affected region."
            )
            source_label = str(item.get("source_label", "")).strip() or "TinyFish live search"
            source_url = str(item.get("source_url", "")).strip() or issue.source_url

            normalized.append(
                Recommendation(
                    issue_id=issue.issue_id,
                    strategy=strategy,
                    product=product,
                    recommended_supplier=SupplierOption(
                        supplier_id=f"TF-{issue.issue_id}-{index:03d}",
                        supplier_name=supplier_name,
                        country=country,
                        latitude=latitude,
                        longitude=longitude,
                        products=supplier_products,
                        average_cost_index=average_cost_index,
                        reliability_score=reliability_score,
                        active_risk_tags=active_risk_tags,
                    ),
                    source_label=source_label,
                    source_url=source_url,
                    rationale=rationale,
                    estimated_cost_delta_pct=estimated_cost_delta_pct,
                    security_score=security_score,
                )
            )

        return normalized

    def _coerce_string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _to_float(self, value: object, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.5, value))

    def _clean_country(self, value: str) -> str:
        if value in COUNTRY_COORDINATES:
            return value
        lowered = value.lower()
        for country in COUNTRY_COORDINATES:
            if country.lower() in lowered:
                return country
        return value

    def _blocked_countries(self, issue: IssueRecord) -> set[str]:
        blocked = {issue.region}
        for region in issue.extraction.affected_regions:
            cleaned = self._clean_country(region)
            if cleaned in COUNTRY_COORDINATES:
                blocked.add(cleaned)
        return blocked


class AlternativeSourcingAgent:
    """
    Agent 3:
    Recommends live TinyFish-sourced alternatives first, then falls back to a
    local supplier catalog only if the live search fails.
    """

    def __init__(
        self,
        supplier_catalog: list[SupplierOption] | None = None,
        live_client: TinyFishAlternativeSourcingClient | None = None,
    ) -> None:
        self.supplier_catalog = supplier_catalog or DEFAULT_SUPPLIERS
        self.live_client = live_client or TinyFishAlternativeSourcingClient()

    def run(self, batch_id: str, issue_batch: IssueBatch) -> RecommendationBatch:
        recommendations: list[Recommendation] = []
        seen_recommendations: set[tuple[str, str, str]] = set()

        for issue in issue_batch.issues:
            issue_start_count = len(recommendations)
            for product in self._candidate_products(issue):
                cheapest = self._pick_best_supplier(issue.region, product, strategy="cheapest")
                if cheapest is None:
                    continue

                cheapest_key = (issue.issue_id, "first_cheapest", cheapest.supplier_id)
                if cheapest_key not in seen_recommendations:
                    seen_recommendations.add(cheapest_key)
                    recommendations.append(
                        Recommendation(
                            issue_id=issue.issue_id,
                            strategy="first_cheapest",
                            product=product,
                            recommended_supplier=cheapest,
                            rationale=(
                                f"{cheapest.supplier_name} can cover the {product} category "
                                f"without relying on the affected region ({issue.region})."
                            ),
                            estimated_cost_delta_pct=round((cheapest.average_cost_index - 1.0) * 100, 2),
                            security_score=self._security_score(cheapest),
                        )
                    )

                secure = self._pick_best_supplier(issue.region, product, strategy="secure")
                if secure is None or secure.supplier_id == cheapest.supplier_id:
                    continue

                secure_key = (issue.issue_id, "first_secure", secure.supplier_id)
                if secure_key in seen_recommendations:
                    continue
                seen_recommendations.add(secure_key)
                recommendations.append(
                    Recommendation(
                        issue_id=issue.issue_id,
                        strategy="first_secure",
                        product=product,
                        recommended_supplier=secure,
                        rationale=(
                            f"{secure.supplier_name} is outside the affected region "
                            f"and offers the strongest resilience score for {product}."
                        ),
                        estimated_cost_delta_pct=round((secure.average_cost_index - 1.0) * 100, 2),
                        security_score=self._security_score(secure),
                    )
                )

            if len(recommendations) == issue_start_count:
                for product in self._fallback_products(issue):
                    cheapest = self._pick_best_supplier(issue.region, product, strategy="cheapest")
                    if cheapest is None:
                        continue

                    cheapest_key = (issue.issue_id, "first_cheapest", cheapest.supplier_id)
                    if cheapest_key not in seen_recommendations:
                        seen_recommendations.add(cheapest_key)
                        recommendations.append(
                            Recommendation(
                                issue_id=issue.issue_id,
                                strategy="first_cheapest",
                                product=product,
                                recommended_supplier=cheapest,
                                rationale=(
                                    f"{cheapest.supplier_name} is a broad fallback for {product} "
                                    f"when the disruption affects cross-border supply resilience."
                                ),
                                estimated_cost_delta_pct=round((cheapest.average_cost_index - 1.0) * 100, 2),
                                security_score=self._security_score(cheapest),
                            )
                        )
                    break

        return RecommendationBatch(
            batch_id=batch_id,
            metadata={
                "agent": "agent_3_alternative_sourcing",
                "issue_batch_id": issue_batch.batch_id,
                "recommendation_count": len(recommendations),
                "live_recommendation_count": live_recommendation_count,
                "fallback_recommendation_count": fallback_recommendation_count,
                "issues_without_matches": issues_without_matches,
                "country_search_enabled": True,
                "live_errors": live_errors[:5],
            },
            recommendations=recommendations,
        )

    def _build_fallback_recommendations(self, issue: IssueRecord) -> list[Recommendation]:
        issue_recommendations: list[Recommendation] = []
        requested_products = self._resolve_requested_products(issue)

        for product in requested_products:
            cheapest = self._pick_best_supplier(issue, product, strategy="cheapest")
            if cheapest is None:
                continue

            issue_recommendations.append(
                Recommendation(
                    issue_id=issue.issue_id,
                    strategy="first_cheapest",
                    product=product,
                    recommended_supplier=cheapest,
                    source_label="Local fallback supplier catalog",
                    source_url=None,
                    rationale=self._build_rationale(issue, product, cheapest, "cheapest"),
                    estimated_cost_delta_pct=round((cheapest.average_cost_index - 1.0) * 100, 2),
                    security_score=self._security_score(cheapest),
                )
            )

            secure = self._pick_best_supplier(issue, product, strategy="secure")
            if secure is None or secure.supplier_id == cheapest.supplier_id:
                continue

            issue_recommendations.append(
                Recommendation(
                    issue_id=issue.issue_id,
                    strategy="first_secure",
                    product=product,
                    recommended_supplier=secure,
                    source_label="Local fallback supplier catalog",
                    source_url=None,
                    rationale=self._build_rationale(issue, product, secure, "secure"),
                    estimated_cost_delta_pct=round((secure.average_cost_index - 1.0) * 100, 2),
                    security_score=self._security_score(secure),
                )
            )

        return issue_recommendations

    def _resolve_requested_products(self, issue: IssueRecord) -> list[str]:
        normalized_products: list[str] = []

        for raw_product in issue.extraction.affected_products:
            normalized = self._normalize_product(raw_product)
            if normalized not in normalized_products:
                normalized_products.append(normalized)

        if normalized_products:
            return normalized_products

        keyword_products = [
            self._normalize_product(keyword)
            for keyword in issue.extraction.keywords
            if self._normalize_product(keyword) != "mixed food supply"
        ]
        deduped_keywords = list(dict.fromkeys(keyword_products))
        if deduped_keywords:
            return deduped_keywords

        return ["mixed food supply"]

    def _pick_best_supplier(
        self,
        issue: IssueRecord,
        product: str,
        strategy: str,
    ) -> SupplierOption | None:
        matching_products = PRODUCT_ALIASES.get(product, [product])
        valid_suppliers = [
            supplier
            for supplier in self.supplier_catalog
            if supplier.country != affected_region
            and any(match in supplier.products for match in matching_products)
        ]

        if requested_product == "mixed food supply":
            return valid_suppliers

        exact_matches = [
            supplier
            for supplier in valid_suppliers
            if requested_product in self._normalize_products(supplier.products)
        ]
        if exact_matches:
            return exact_matches

        return [
            supplier
            for supplier in valid_suppliers
            if set(self._normalize_products(supplier.products)).intersection(ALL_PRODUCTS)
        ]

    def _normalize_product(self, product: str) -> str:
        lowered = product.strip().lower()
        if lowered in PRODUCT_ALIASES:
            return PRODUCT_ALIASES[lowered]

        for alias, canonical in PRODUCT_ALIASES.items():
            if alias in lowered:
                return canonical

        return "mixed food supply"

    def _normalize_products(self, products: list[str]) -> list[str]:
        return [self._normalize_product(product) for product in products]

    def _normalize_risk_tags(self, tags: list[str]) -> set[str]:
        normalized: set[str] = set()
        for tag in tags:
            lowered = tag.strip().lower()
            if lowered in {"flood", "storm", "heatwave", "drought", "cyclone", "typhoon", "monsoon"}:
                normalized.add("weather")
            normalized.add(lowered)
        return normalized

    def _issue_risk_tags(self, issue: IssueRecord) -> set[str]:
        tags = {issue.extraction.risk_type.value}
        for signal in issue.extraction.negative_signals:
            lowered = signal.strip().lower()
            if lowered in {"flood", "storm", "heatwave", "drought", "cyclone", "typhoon", "monsoon"}:
                tags.add("weather")
            tags.add(lowered)
        return tags

    def _build_rationale(
        self,
        issue: IssueRecord,
        product: str,
        supplier: SupplierOption,
        strategy: str,
    ) -> str:
        distance = round(
            self._distance_km(issue.latitude, issue.longitude, supplier.latitude, supplier.longitude)
        )
        if strategy == "cheapest":
            return (
                f"{supplier.supplier_name} in {supplier.country} is outside the affected region "
                f"({issue.region}) and is the lowest-cost nearby option for {product} at roughly "
                f"{distance} km from the disruption zone."
            )

        return (
            f"{supplier.supplier_name} in {supplier.country} avoids the same active risk pattern as "
            f"{issue.region} and offers the strongest resilience score for {product}, about "
            f"{distance} km away."
        )

    def _security_score(self, supplier: SupplierOption) -> float:
        penalty = 0.08 * len(self._normalize_risk_tags(supplier.active_risk_tags))
        return round(max(0.0, supplier.reliability_score - penalty), 3)

    def _candidate_products(self, issue: IssueRecord) -> list[str]:
        candidates: list[str] = []

        for product in issue.extraction.affected_products:
            if product not in candidates:
                candidates.append(product)

        searchable_text = " ".join(
            [issue.title, *issue.extraction.keywords, *issue.extraction.affected_products]
        ).lower()
        for alias in PRODUCT_ALIASES:
            if alias in searchable_text and alias not in candidates:
                candidates.append(alias)

        if issue.extraction.risk_type in {RiskType.PORT_DISRUPTION, RiskType.STRIKE}:
            for product in ("general cargo", "container capacity", "mixed food supply"):
                if product not in candidates:
                    candidates.append(product)

        if "fuel" in searchable_text and "fuel security" not in candidates:
            candidates.append("fuel security")

        if not candidates:
            candidates.append("mixed food supply")

        return candidates[:3]

    def _fallback_products(self, issue: IssueRecord) -> list[str]:
        searchable_text = " ".join([issue.title, issue.extraction.narrative]).lower()
        fallback_products = ["mixed food supply", "general cargo", "container capacity"]
        if "fuel" in searchable_text or "airline" in searchable_text:
            fallback_products.insert(0, "fuel security")
        return fallback_products
