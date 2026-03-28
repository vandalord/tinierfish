from __future__ import annotations

from agents.shared.models import IssueBatch, Recommendation, RecommendationBatch, SupplierOption


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
        supplier_name="Queensland Agri Reserve",
        country="Australia",
        latitude=-20.9176,
        longitude=142.7028,
        products=["vegetable", "fruit", "poultry"],
        average_cost_index=1.24,
        reliability_score=0.94,
        active_risk_tags=["cyclone"],
    ),
    SupplierOption(
        supplier_id="SUP-004",
        supplier_name="Andhra Staple Foods",
        country="India",
        latitude=15.9129,
        longitude=79.74,
        products=["rice", "egg", "poultry"],
        average_cost_index=0.96,
        reliability_score=0.86,
        active_risk_tags=[],
    ),
]


class AlternativeSourcingAgent:
    """
    Agent 3:
    Recommends safer or cheaper alternative suppliers for each detected issue.
    """

    def __init__(self, supplier_catalog: list[SupplierOption] | None = None) -> None:
        self.supplier_catalog = supplier_catalog or DEFAULT_SUPPLIERS

    def run(self, batch_id: str, issue_batch: IssueBatch) -> RecommendationBatch:
        recommendations: list[Recommendation] = []

        for issue in issue_batch.issues:
            for product in issue.extraction.affected_products:
                cheapest = self._pick_best_supplier(issue.region, product, strategy="cheapest")
                if cheapest is None:
                    continue

                recommendations.append(
                    Recommendation(
                        issue_id=issue.issue_id,
                        strategy="first_cheapest",
                        product=product,
                        recommended_supplier=cheapest,
                        rationale=(
                            f"{cheapest.supplier_name} avoids the affected region "
                            f"({issue.region}) while preserving a low cost index."
                        ),
                        estimated_cost_delta_pct=round((cheapest.average_cost_index - 1.0) * 100, 2),
                        security_score=self._security_score(cheapest),
                    )
                )

                secure = self._pick_best_supplier(issue.region, product, strategy="secure")
                if secure is None or secure.supplier_id == cheapest.supplier_id:
                    continue

                recommendations.append(
                    Recommendation(
                        issue_id=issue.issue_id,
                        strategy="first_secure",
                        product=product,
                        recommended_supplier=secure,
                        rationale=(
                            f"{secure.supplier_name} is outside the affected region "
                            f"and provides the strongest resilience score."
                        ),
                        estimated_cost_delta_pct=round((secure.average_cost_index - 1.0) * 100, 2),
                        security_score=self._security_score(secure),
                    )
                )

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
        valid_suppliers = [
            supplier
            for supplier in self.supplier_catalog
            if product in supplier.products and supplier.country != affected_region
        ]
        if not valid_suppliers:
            return None

        if strategy == "cheapest":
            return min(valid_suppliers, key=lambda supplier: supplier.average_cost_index)

        return max(valid_suppliers, key=self._security_score)

    def _security_score(self, supplier: SupplierOption) -> float:
        penalty = 0.08 * len(supplier.active_risk_tags)
        return round(max(0.0, supplier.reliability_score - penalty), 3)
