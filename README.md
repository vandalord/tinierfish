# tinierfish

TinyFish AI 2026

This repo now includes a starter multi-agent pipeline for dynamic supply chain
resilience focused on Singapore's food-import risk monitoring.

The implementation lives in [agents/README.md](/Users/cavan/tinierfish/cookedtinyfish/agents/README.md) and includes:

- Agent 1: source discovery and trusted URL filtering
- Agent 2: TinyFish-powered issue extraction
- Agent 3: alternative supplier recommendation
- Agent 4: geographic visualization of disruptions and fallbacks

To run the demo pipeline:

```bash
export TINYFISH_API_KEY=your_tinyfish_api_key_here
python3 -m agents.pipeline_demo
```

To run the live local dashboard:

```bash
python3 -m webapp.server --host 127.0.0.1 --port 8000
```

The dashboard now serves cached batches instantly, shows whether data came from
`tinyfish_web` or `fallback_demo`, and runs refreshes in the background.