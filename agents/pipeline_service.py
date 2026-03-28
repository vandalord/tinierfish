from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.agent_1_source_discovery import SourceDiscoveryAgent
from agents.agent_2_issue_extraction import IssueExtractionAgent
from agents.agent_3_alternative_sourcing import AlternativeSourcingAgent
from agents.agent_4_map_visualization import MapVisualizationAgent


SAMPLE_CANDIDATES = [
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
    {
        "url": "https://www.example.com/lifestyle/travel-tips",
        "title": "Weekend travel tips",
        "publisher": "Example",
        "summary": "This unrelated article should be filtered out.",
        "region": "Singapore",
    },
]


def run_demo_pipeline(
    output_dir: str = "outputs",
    write_files: bool = True,
    use_live_sources: bool = True,
) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_root = f"BATCH-{timestamp}"

    agent_1 = SourceDiscoveryAgent()
    agent_2 = IssueExtractionAgent()
    agent_3 = AlternativeSourcingAgent()
    agent_4 = MapVisualizationAgent()

    source_batch = agent_1.run(
        f"{batch_root}-A1",
        None if use_live_sources else SAMPLE_CANDIDATES,
    )
    issue_batch = agent_2.run(f"{batch_root}-A2", source_batch)
    recommendation_batch = agent_3.run(f"{batch_root}-A3", issue_batch)
    visualization_batch = agent_4.run(
        f"{batch_root}-A4",
        issue_batch,
        recommendation_batch,
        output_dir=output_dir,
    )

    payload = {
        "batch_root": batch_root,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_mode": source_batch.metadata.get("source_mode", "unknown"),
        "source_batch": source_batch.to_dict(),
        "issue_batch": issue_batch.to_dict(),
        "recommendation_batch": recommendation_batch.to_dict(),
        "visualization_batch": visualization_batch.to_dict(),
    }

    if write_files:
        outputs = Path(output_dir)
        outputs.mkdir(parents=True, exist_ok=True)
        (outputs / "source_batch.json").write_text(
            json.dumps(source_batch.to_dict(), indent=2),
            encoding="utf-8",
        )
        (outputs / "issue_batch.json").write_text(
            json.dumps(issue_batch.to_dict(), indent=2),
            encoding="utf-8",
        )
        (outputs / "recommendation_batch.json").write_text(
            json.dumps(recommendation_batch.to_dict(), indent=2),
            encoding="utf-8",
        )
        (outputs / "visualization_batch.json").write_text(
            json.dumps(visualization_batch.to_dict(), indent=2),
            encoding="utf-8",
        )
        (outputs / "latest_dashboard.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    return payload
