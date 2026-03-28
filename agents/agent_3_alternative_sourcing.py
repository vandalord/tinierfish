from __future__ import annotations

from agents.shared.models import IssueBatch, IssueRecord, Recommendation, RecommendationBatch, RiskType, SupplierOption


DEFAULT_SUPPLIERS = [
    SupplierOption(
        supplier_id="SUP-001",
        supplier_name="Johor Fresh Greens Cooperative",
        country="Malaysia",
        latitude=1.4927,
        longitude=103.7414,
        products=["vegetable", "fruit", "egg", "mixed food supply"],
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
        products=["vegetable", "fruit", "rice", "mixed food supply"],
        average_cost_index=1.12,
        reliability_score=0.9,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-003",
        supplier_name="Batam Cold Chain Hub",
        country="Indonesia",
        latitude=1.0456,
        longitude=104.0305,
        products=["seafood", "mixed food supply", "general cargo", "container capacity"],
        average_cost_index=1.03,
        reliability_score=0.87,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-004",
        supplier_name="Andhra Staple Foods",
        country="India",
        latitude=15.9129,
        longitude=79.74,
        products=["rice", "egg", "poultry", "mixed food supply"],
        average_cost_index=0.96,
        reliability_score=0.86,
        active_risk_tags=[],
    ),
    SupplierOption(
        supplier_id="SUP-005",
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
        supplier_id="SUP-006",
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
        supplier_id="SUP-007",
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
        supplier_id="SUP-008",
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
        supplier_id="SUP-009",
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
        "general cargo",
        "container capacity",
    ],
    "food imports": ["mixed food supply", "general cargo", "container capacity"],
    "logistics": ["general cargo", "container capacity", "mixed food supply"],
    "freight": ["general cargo", "container capacity", "mixed food supply"],
    "shipping": ["general cargo", "container capacity", "mixed food supply"],
    "transport": ["general cargo", "container capacity", "mixed food supply"],
    "produce": ["vegetable", "fruit", "mixed food supply"],
    "grain": ["rice", "mixed food supply"],
    "fuel security": ["petrol", "diesel", "jet fuel", "fuel security", "energy logistics"],
    "containerized trade": ["general cargo", "container capacity", "mixed food supply"],
    "global maritime cargo": ["general cargo", "container capacity", "mixed food supply"],
}


class AlternativeSourcingAgent:
    """
    Agent 3:
    Recommends safer or cheaper alternative suppliers for each detected issue.
    """

    def __init__(self, supplier_catalog: list[SupplierOption] | None = None) -> None:
        self.supplier_catalog = supplier_catalog or DEFAULT_SUPPLIERS

    def run(self, batch_id: str, issue_batch: IssueBatch) -> RecommendationBatch:
        recommendations: list[Recommendation] = []
        seen_recommendations: set[tuple[str, str, str]] = set()

        for issue in issue_batch.issues:
            issue_start_count = len(recommendations)

            for product in self._candidate_products(issue):
                cheapest = self._pick_best_supplier(issue.region, product, strategy="cheapest")
                if cheapest is not None:
                    key = (issue.issue_id, "first_cheapest", cheapest.supplier_id)
                    if key not in seen_recommendations:
                        seen_recommendations.add(key)
                        recommendations.append(
                            Recommendation(
                                issue_id=issue.issue_id,
                                strategy="first_cheapest",
                                product=product,
                                recommended_supplier=cheapest,
                                source_label=cheapest.supplier_name,
                                source_url=None,
                                rationale=(
                                    f"{cheapest.supplier_name} can cover the {product} category "
                                    f"without relying on the affected region ({issue.region})."
                                ),
                                estimated_cost_delta_pct=round((cheapest.average_cost_index - 1.0) * 100, 2),
                                security_score=self._security_score(cheapest),
                            )
                        )

                secure = self._pick_best_supplier(issue.region, product, strategy="secure")
                if secure is not None:
                    key = (issue.issue_id, "first_secure", secure.supplier_id)
                    if key not in seen_recommendations:
                        seen_recommendations.add(key)
                        recommendations.append(
                            Recommendation(
                                issue_id=issue.issue_id,
                                strategy="first_secure",
                                product=product,
                                recommended_supplier=secure,
                                source_label=secure.supplier_name,
                                source_url=None,
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
                    key = (issue.issue_id, "first_cheapest", cheapest.supplier_id)
                    if key in seen_recommendations:
                        continue
                    seen_recommendations.add(key)
                    recommendations.append(
                        Recommendation(
                            issue_id=issue.issue_id,
                            strategy="first_cheapest",
                            product=product,
                            recommended_supplier=cheapest,
                            source_label=cheapest.supplier_name,
                            source_url=None,
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
            },
            recommendations=recommendations,
        )

    def _pick_best_supplier(
        self,
        affected_region: str,
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
        if not valid_suppliers:
            return None

        if strategy == "cheapest":
            return min(valid_suppliers, key=lambda supplier: supplier.average_cost_index)

        return max(valid_suppliers, key=self._security_score)

    def _security_score(self, supplier: SupplierOption) -> float:
        penalty = 0.08 * len(supplier.active_risk_tags)
        return round(max(0.0, supplier.reliability_score - penalty), 3)

    def _candidate_products(self, issue: IssueRecord) -> list[str]:
        candidates: list[str] = []

        for product in issue.extraction.affected_products:
            normalized = product.lower()
            if normalized not in candidates:
                candidates.append(normalized)

        searchable_text = " ".join(
            [issue.title, issue.extraction.narrative, *issue.extraction.keywords]
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
