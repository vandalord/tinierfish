# Multi-Agent Supply Chain Resilience

This folder contains a lightweight starter implementation for the four-agent
system proposed for Singapore food-import resilience.

## Agents

1. `agent_1_source_discovery.py`
   - Uses TinyFish Web Agent against live source pages to extract fresh article
     links, then filters them into a trusted hourly source batch.
2. `agent_2_issue_extraction.py`
   - Uses TinyFish Web Agent on each article URL to extract negative supply-chain
     signals, products, regions, and severity as structured JSON.
3. `agent_3_alternative_sourcing.py`
   - Recommends cheaper and more secure alternative suppliers outside the
     affected region.
4. `agent_4_map_visualization.py`
   - Creates GeoJSON and an HTML map-like dashboard with clickable disruption
     pins and fallback supplier suggestions.

## Shared Contracts

`shared/models.py` defines the handoff objects passed between agents:

- `SourceBatch`
- `IssueBatch`
- `RecommendationBatch`
- `VisualizationBatch`

These give each service a clean input and output shape for batching, storage,
or orchestration in a queue system later.

## Demo

Set your TinyFish key in the shell or a local `.env` file first:

```bash
export TINYFISH_API_KEY=your_tinyfish_api_key_here
```

Run the end-to-end example:

```bash
python3 -m agents.pipeline_demo
```

This writes JSON batches and a browsable HTML file into `outputs/`.

## Local Web Server

Run the live dashboard server:

```bash
python3 -m webapp.server --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

The dashboard fetches `/api/dashboard`, renders disruptions on a live SVG map,
polls cached results every 60 seconds, and uses a background refresh job when
the user presses the refresh button.

Useful local endpoints:

- `GET /api/dashboard` returns the latest cached batch plus runtime metadata.
- `GET /api/status` returns the background refresh state.
- `POST /api/refresh` queues a fresh TinyFish/web ingestion run without blocking the page.

## Production Notes

- `TinyFishAPIClient` reads `TINYFISH_API_KEY` from the environment and uses
  TinyFish's synchronous automation API when the key is present.
- Agent 1 seeds live source pages and asks TinyFish to return structured article
  links relevant to supply-chain disruption monitoring.
- Replace the sample supplier catalog with your actual procurement data.
- Tune the TinyFish goals and seed URLs for the exact publishers you trust.
- If you later move this into FastAPI, Celery, Temporal, or an event bus, the
  batch models can stay the same.
