from __future__ import annotations

import json
from pathlib import Path

from agents.shared.models import IssueBatch, RecommendationBatch, VisualizationBatch


class MapVisualizationAgent:
    """
    Agent 4:
    Builds a map-ready GeoJSON payload and a simple HTML visualization.
    """

    def run(
        self,
        batch_id: str,
        issue_batch: IssueBatch,
        recommendation_batch: RecommendationBatch,
        output_dir: str = "outputs",
    ) -> VisualizationBatch:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        geojson = self._build_geojson(issue_batch, recommendation_batch)
        geojson_path = output_path / f"{batch_id}_supply_chain_map.geojson"
        html_path = output_path / f"{batch_id}_supply_chain_map.html"

        geojson_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
        html_path.write_text(self._build_html(geojson), encoding="utf-8")

        return VisualizationBatch(
            batch_id=batch_id,
            metadata={
                "agent": "agent_4_map_visualization",
                "issue_batch_id": issue_batch.batch_id,
                "recommendation_batch_id": recommendation_batch.batch_id,
            },
            geojson=geojson,
            html_path=str(html_path),
        )

    def _build_geojson(
        self,
        issue_batch: IssueBatch,
        recommendation_batch: RecommendationBatch,
    ) -> dict[str, object]:
        recommendations_by_issue: dict[str, list[dict[str, object]]] = {}

        for recommendation in recommendation_batch.recommendations:
            recommendations_by_issue.setdefault(recommendation.issue_id, []).append(
                recommendation.to_dict()
            )

        features = []
        for issue in issue_batch.issues:
            popup_recommendations = recommendations_by_issue.get(issue.issue_id, [])
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [issue.longitude, issue.latitude],
                    },
                    "properties": {
                        "issue_id": issue.issue_id,
                        "title": issue.title,
                        "source_url": issue.source_url,
                        "region": issue.region,
                        "severity": issue.extraction.severity.value,
                        "risk_type": issue.extraction.risk_type.value,
                        "narrative": issue.extraction.narrative,
                        "products": issue.extraction.affected_products,
                        "negative_signals": issue.extraction.negative_signals,
                        "recommendations": popup_recommendations,
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}

    def _build_html(self, geojson: dict[str, object]) -> str:
        raw_geojson = json.dumps(geojson).replace("</", "<\\/")
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Supply Chain Resilience Map</title>
    <style>
      :root {{
        --bg: #f3efe6;
        --panel: #fffaf0;
        --ink: #1c1b19;
        --accent: #0d5c63;
        --danger: #bd3d3a;
        --line: #d4cab8;
      }}
      body {{
        margin: 0;
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        background: radial-gradient(circle at top, #fff7db 0%, var(--bg) 58%);
        color: var(--ink);
      }}
      .layout {{
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        min-height: 100vh;
      }}
      .map {{
        position: relative;
        padding: 32px;
        border-right: 1px solid var(--line);
      }}
      .map-shell {{
        position: relative;
        height: calc(100vh - 64px);
        border-radius: 24px;
        background:
          linear-gradient(180deg, rgba(13, 92, 99, 0.08), rgba(13, 92, 99, 0)),
          linear-gradient(135deg, #d8efe5 0%, #f7f0d7 100%);
        overflow: hidden;
        box-shadow: 0 24px 80px rgba(28, 27, 25, 0.08);
      }}
      .ring {{
        position: absolute;
        left: 50%;
        top: 58%;
        width: 180px;
        height: 180px;
        margin-left: -90px;
        margin-top: -90px;
        border: 2px dashed rgba(13, 92, 99, 0.2);
        border-radius: 999px;
      }}
      .pin {{
        position: absolute;
        width: 18px;
        height: 18px;
        border-radius: 999px;
        border: 2px solid white;
        background: var(--danger);
        box-shadow: 0 0 0 8px rgba(189, 61, 58, 0.15);
        cursor: pointer;
        transform: translate(-50%, -50%);
      }}
      .sidebar {{
        padding: 32px;
        background: rgba(255, 250, 240, 0.85);
        backdrop-filter: blur(10px);
      }}
      h1 {{
        margin: 0 0 8px;
        font-size: 2rem;
      }}
      .lede {{
        margin: 0 0 24px;
        line-height: 1.5;
      }}
      .card {{
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 16px;
        background: white;
      }}
      .card h2 {{
        margin: 0 0 8px;
        font-size: 1rem;
      }}
      .meta {{
        color: #625b50;
        font-size: 0.92rem;
      }}
      .pill {{
        display: inline-block;
        margin: 6px 8px 0 0;
        padding: 4px 10px;
        border-radius: 999px;
        background: #f4ead7;
        font-size: 0.85rem;
      }}
      @media (max-width: 900px) {{
        .layout {{
          grid-template-columns: 1fr;
        }}
        .map {{
          border-right: 0;
          border-bottom: 1px solid var(--line);
        }}
        .map-shell {{
          height: 50vh;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="layout">
      <section class="map">
        <div class="map-shell" id="map">
          <div class="ring" title="Singapore risk watch zone"></div>
        </div>
      </section>
      <aside class="sidebar">
        <h1>Supply Chain Watch</h1>
        <p class="lede">
          Click a disruption pin to inspect the affected product flow and the
          recommended fallback suppliers.
        </p>
        <div id="details" class="card">
          <h2>Select a disruption</h2>
          <p class="meta">Pins show issues around Singapore and nearby sourcing regions.</p>
        </div>
      </aside>
    </div>
    <script id="geojson-data" type="application/json">{raw_geojson}</script>
    <script>
      const geojson = JSON.parse(document.getElementById("geojson-data").textContent);
      const map = document.getElementById("map");
      const details = document.getElementById("details");

      function project(latitude, longitude) {{
        const x = ((longitude - 70) / 70) * map.clientWidth;
        const y = ((25 - latitude) / 40) * map.clientHeight;
        return {{ x, y }};
      }}

      function renderDetails(feature) {{
        const props = feature.properties;
        const recommendations = props.recommendations
          .map((item) => `
            <div class="pill">${{item.strategy}}: ${{item.recommended_supplier.supplier_name}}</div>
          `)
          .join("");

        details.innerHTML = `
          <h2>${{props.title}}</h2>
          <p class="meta">${{props.region}} • ${{props.severity}} • ${{props.risk_type}}</p>
          <p>Affected products: ${{props.products.join(", ")}}</p>
          <p>Signals: ${{props.negative_signals.join(", ") || "monitoring"}}</p>
          <div>${{recommendations || '<span class="pill">No recommendation available</span>'}}</div>
        `;
      }}

      geojson.features.forEach((feature) => {{
        const [longitude, latitude] = feature.geometry.coordinates;
        const pin = document.createElement("button");
        const point = project(latitude, longitude);
        pin.className = "pin";
        pin.style.left = `${{point.x}}px`;
        pin.style.top = `${{point.y}}px`;
        pin.title = feature.properties.title;
        pin.addEventListener("click", () => renderDetails(feature));
        map.appendChild(pin);
      }});
    </script>
  </body>
</html>
"""
