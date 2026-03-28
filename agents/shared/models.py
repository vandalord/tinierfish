from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(str, Enum):
    WEATHER = "weather"
    PORT_DISRUPTION = "port_disruption"
    STRIKE = "strike"
    CONFLICT = "conflict"
    POLICY = "policy"
    PRICE_SHOCK = "price_shock"
    DISEASE = "disease"
    OTHER = "other"


@dataclass
class SourceRecord:
    url: str
    title: str
    publisher: str
    summary: str
    region: str
    collected_at: str = field(default_factory=utc_now_iso)
    score: float = 0.0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KeywordExtraction:
    keywords: list[str]
    negative_signals: list[str]
    affected_products: list[str]
    affected_regions: list[str]
    risk_type: RiskType
    severity: IssueSeverity
    confidence: float
    narrative: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "risk_type": self.risk_type.value,
            "severity": self.severity.value,
        }


@dataclass
class IssueRecord:
    issue_id: str
    source_url: str
    source_publisher: str
    title: str
    region: str
    latitude: float
    longitude: float
    extraction: KeywordExtraction
    detected_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "source_url": self.source_url,
            "source_publisher": self.source_publisher,
            "title": self.title,
            "region": self.region,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "detected_at": self.detected_at,
            "extraction": self.extraction.to_dict(),
        }


@dataclass
class SupplierOption:
    supplier_id: str
    supplier_name: str
    country: str
    latitude: float
    longitude: float
    products: list[str]
    average_cost_index: float
    reliability_score: float
    active_risk_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    issue_id: str
    strategy: str
    product: str
    recommended_supplier: SupplierOption
    source_label: str | None
    source_url: str | None
    rationale: str
    estimated_cost_delta_pct: float
    security_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "strategy": self.strategy,
            "product": self.product,
            "recommended_supplier": self.recommended_supplier.to_dict(),
            "source_label": self.source_label,
            "source_url": self.source_url,
            "rationale": self.rationale,
            "estimated_cost_delta_pct": self.estimated_cost_delta_pct,
            "security_score": self.security_score,
        }


@dataclass
class AgentBatch:
    batch_id: str
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceBatch(AgentBatch):
    sources: list[SourceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "sources": [source.to_dict() for source in self.sources],
        }


@dataclass
class IssueBatch(AgentBatch):
    issues: list[IssueRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class RecommendationBatch(AgentBatch):
    recommendations: list[Recommendation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "recommendations": [
                recommendation.to_dict() for recommendation in self.recommendations
            ],
        }


@dataclass
class VisualizationBatch(AgentBatch):
    geojson: dict[str, Any] = field(default_factory=dict)
    html_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "geojson": self.geojson,
            "html_path": self.html_path,
        }
