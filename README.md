# COLLIDE — AI-Powered BTM Data Center Site Selection

An AI siting platform that jointly scores candidate sites across land viability, gas supply reliability, and BTM power economics — surfacing a ranked set of locations with quantified risk, cost estimates, and sensitivity analysis.

Built for the ASU Energy Hackathon 2026.

---

## What it does

Hyperscale AI data centers need 50–500 MW of power 24/7. Grid interconnection queues now stretch 3–7 years. The alternative — behind-the-meter (BTM) natural gas generation — requires evaluating three interlocking constraints simultaneously:

- **Sub-A: Land viability** — zoning, fiber proximity, water access, parcel size, flood zone
- **Sub-B: Gas supply reliability** — pipeline failure probability, hub distance, curtailment risk
- **Sub-C: Power economics** — BTM spread (LMP minus generation cost), spread durability

COLLIDE scores every candidate site across all three dimensions in seconds, streams a composite scorecard with 20-year NPV estimates, and lets an AI analyst answer what-if questions in natural language.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Leaflet, Recharts |
| Backend | Python FastAPI, async SSE |
| AI orchestration | LangGraph + LangChain |
| LLM | Anthropic Claude Haiku + Sonnet |
| ML models | Random Forest (land, power durability), Gaussian KDE (gas), GMM (regime) |
| Live data | GridStatus (ERCOT LMP), EIA Open Data, CAISO OASIS |
| Web enrichment | Tavily API |
| Data pipeline | DuckDB, Parquet, Pandera, 10 public APIs |
| Deployment | Vercel (experimentalServices: Vite + FastAPI) |

---

## ML models

### Land viability — Random Forest Classifier
- 300 trees, max depth 8, trained on parcel attribute data
- **Top features:** highway access (28.5%), substation proximity (23.7%), pipeline distance (19.9%), water distance (14.6%), fiber proximity (8.1%)
- SHAP explainer included for per-site feature attribution

### Gas reliability — GPU Gaussian KDE
- Bandwidth 0.5, trained on PHMSA pipeline incident coordinates (severity-weighted)
- Scoring: incident density 40% + interstate pipeline proximity 35% + Waha distance 25%
- Falls back to PHMSA density grid when PyTorch unavailable

### Power durability — Random Forest Classifier
- 200 trees, max depth 6
- **Top features:** LMP level (68.4%), market regime encoding (30.9%), Waha price (0.8%)

### Market regime — Gaussian Mixture Model
- 3 components, full covariance, trained on ERCOT 5-feature historical data
- Labels: `normal` (cluster 0), `wind_curtailment` (cluster 1), `stress_scarcity` (cluster 2)
- Training mean: LMP $78/MWh, wind penetration 31%, demand 54.9 GW

### Composite score — TOPSIS
- Weights: land 30%, gas 35%, power 35% (user-adjustable)
- 20-year NPV via Monte Carlo (10,000 scenarios, 8% WACC, 100 MW plant)

---

## Features

- **Interactive map** — click any coordinate for a full scorecard; right-click for context menu
- **Scorecard panel** — land/gas/power breakdown, SHAP explanations, NPV P10/P50/P90, streaming AI narrative
- **Compare mode** — up to 5 sites side by side
- **Grid optimizer** — draw a bounding box, stream top-N candidates
- **AI Analyst** — LangGraph agent with 5 intents: stress test, compare, timing, explain, configure
- **Live market data** — Waha gas price, ERCOT + CAISO LMP, regime classification (updated every 5 min)
- **72-hour LMP forecast** — Moirai model, P10/P50/P90 confidence bands
- **Heat layers** — composite / gas / LMP score overlays on the map

---

## Data sources

| Source | Dataset | Cadence |
|---|---|---|
| EIA-930 | BA demand, net generation | 15 min |
| EIA Open Data | Waha + Henry Hub gas prices | Daily |
| CAISO OASIS | SP15, NP15, Palo Verde LMP | 5 min |
| NOAA NWS | Phoenix weather forecast | Hourly |
| BLM GeoBOB | Federal land ownership (AZ, NM, TX) | Static |
| FCC HIFLD | Dark fiber and FTTP availability | Static |
| USGS NHD | Water body proximity | Static |
| FEMA | 100-year flood zone boundaries | Periodic |
| EIA Gas | Pipeline routes ERCOT + WECC | Periodic |
| PHMSA | Gas pipeline incident records | Periodic |

---

## Project structure

```
collide/
├── src/                    # React frontend
│   ├── components/         # 28 UI components
│   ├── hooks/              # 13 custom hooks (useEvaluate, useAgent, ...)
│   ├── docs/               # /docs/* documentation pages
│   └── data/               # Static site definitions
├── backend/
│   ├── scoring/            # Sub-A, Sub-B, Sub-C + TOPSIS + cost
│   ├── agent/              # LangGraph agent (graph.py, tools.py)
│   ├── features/           # Spatial feature extraction
│   ├── pipeline/           # FastAPI routes + background jobs
│   └── data/               # Site definitions + live cache
├── data/models/            # Trained pkl files (RF, GMM, KDE, SHAP)
├── ingestion/              # Data pipeline (see ingestion/README.md)
└── docs/                   # Problem statement + specs + plans
```

---

## Getting started

### Frontend

```bash
npm install
npm run dev
```

### Backend

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt
npm run dev:api
```

Set environment variables in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
GRIDSTATUS_API_KEY=...
EIA_API_KEY=...
```

### Data pipeline

See [`ingestion/README.md`](ingestion/README.md) for full setup. To run all sources:

```bash
cd ingestion
python -m ingestion.run
```

---

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/sites` | All candidate sites with scores |
| GET | `/api/market` | Live gas prices, LMP, BA demand |
| POST | `/api/evaluate` | Score a coordinate (SSE stream) |
| POST | `/api/optimize` | Grid search (SSE stream) |
| POST | `/api/agent` | AI Analyst query (SSE stream) |
| GET | `/api/forecast` | 72 h LMP forecast P10/P50/P90 |
| GET | `/api/regime` | Current market regime |
| WS | `/ws/lmp/stream` | Live ERCOT LMP WebSocket |

Full schema reference: [`/docs/schema`](/docs/schema)

---

## Documentation

Live docs are available at `/docs` in the app:

- [Overview](/src/pages/docs/overview.md) — what COLLIDE does and quick start
- [Architecture](/src/pages/docs/architecture.md) — system layers, agent graph, data pipeline
- [How It Works](/src/pages/docs/howitworks.md) — ML models, weights, scoring pipeline
- [Features](/src/pages/docs/features.md) — full feature guide
- [Data](/src/pages/docs/data.md) — data sources and pipeline details
- [Schema](/src/pages/docs/schema.md) — API contracts, SSE events, data models

---

## Links

- [GitHub](https://github.com/BhavyaShah1234/EnergyHackathon)
- [Ingestion pipeline docs](ingestion/README.md)
