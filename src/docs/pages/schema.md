# Schema Reference

Data models, API endpoint contracts, SSE event formats, and agent intent types.

## Site model

Predefined candidate sites are defined in `backend/data/sites.py` and mirrored in `src/data/sites.js`.

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique slug (e.g. `permian-prime`) |
| `name` | string | Human-readable name (e.g. `Permian Prime`) |
| `lat` | float | Latitude |
| `lng` | float | Longitude |
| `state` | string | State abbreviation — `TX`, `NM`, or `AZ` |
| `market` | string | Wholesale market — `ERCOT` or `WECC` |
| `acres` | int | Estimated available parcel size |
| `land_cost_per_acre` | float | Land acquisition cost (USD/acre) |
| `fiber_km` | float | Distance to nearest dark fiber route (km) |
| `water_km` | float | Distance to nearest water source (km) |
| `pipeline_km` | float | Distance to nearest gas pipeline (km) |
| `gas_hub` | string | Primary gas pricing hub — `waha` or `henry_hub` |
| `lmp_node` | string | ERCOT or CAISO settlement point for LMP |

## Scorecard

`SiteScorecard` is the main output of the scoring engine (`backend/scoring/scorecard.py`).

| Field | Type | Description |
|---|---|---|
| `land_score` | float 0–1 | Sub-A: land viability |
| `gas_score` | float 0–1 | Sub-B: gas supply reliability |
| `power_score` | float 0–1 | Sub-C: BTM power economics |
| `composite_score` | float 0–1 | TOPSIS-weighted composite |
| `land_shap` | object | SHAP feature importances for land score |
| `spread_p50_mwh` | float | BTM spread at P50 ($/MWh) |
| `spread_durability` | float 0–1 | How stable a positive spread is likely to be |
| `regime` | string | Market state — `scarcity`, `normal`, or `oversupply` |
| `regime_proba` | float | Classifier confidence (0–1) |
| `cost` | CostEstimate | Full cost breakdown (see below) |
| `web_land_adjustment` | float | Tavily-derived land score adjustment (−0.10 to +0.10) |
| `web_pipeline_score` | float | Tavily-derived pipeline reliability opinion (0–1) |
| `sources` | array | Web enrichment source URLs |
| `live_gas_price` | float | Waha Hub spot price at evaluation time ($/MMBtu) |
| `live_lmp_mwh` | float | Settlement point LMP at evaluation time ($/MWh) |

## Cost estimate

`CostEstimate` is nested inside every scorecard (`backend/scoring/cost.py`).

| Field | Type | Description |
|---|---|---|
| `land_acquisition_m` | float | Land cost ($M) |
| `pipeline_connection_m` | float | Pipeline tie-in cost ($M) |
| `water_connection_m` | float | Water connection cost ($M) |
| `btm_capex_m` | float | BTM plant capital cost ($M) |
| `npv_p10_m` | float | 20-year NPV at 10th percentile ($M) |
| `npv_p50_m` | float | 20-year NPV at 50th percentile ($M) |
| `npv_p90_m` | float | 20-year NPV at 90th percentile ($M) |
| `wacc` | float | Discount rate used (e.g. `0.08`) |
| `capacity_mw` | float | Assumed BTM plant capacity (MW) |

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/sites` | All predefined candidate sites with cached scores |
| GET | `/api/sites/{id}` | Single site detail |
| GET | `/api/market` | Live gas prices, LMP, BA demand |
| POST | `/api/evaluate` | Score a coordinate (SSE stream) |
| POST | `/api/optimize` | Grid search within bounds (SSE stream) |
| GET | `/api/heatmap` | GeoJSON heat layer |
| GET | `/api/compare` | Compare N coordinates, return ranked |
| GET | `/api/forecast` | 72 h Moirai LMP forecast (P10/P50/P90) |
| GET | `/api/regime` | Current market regime classification |
| GET | `/api/cache/status` | Cache state and data freshness |
| POST | `/api/agent` | AI Analyst query (SSE stream) |
| GET | `/api/news` | Latest industry headlines via Tavily |
| POST | `/api/pipeline/run` | Trigger full ingestion pipeline |
| WS | `/ws/lmp/stream` | Live ERCOT LMP (5-min WebSocket) |

## Evaluate request

```json
POST /api/evaluate
{
  "lat": 31.5,
  "lon": -104.2,
  "weights": {
    "land": 0.30,
    "gas": 0.35,
    "power": 0.35
  }
}
```

## SSE event formats

### /api/evaluate

```
event: scorecard
data: {"land_score": 0.72, "gas_score": 0.81, "composite_score": 0.73, ...}

event: web_context
data: {"web_land_adjustment": 0.05, "sources": ["https://..."]}

event: narrative
data: {"text": "This site in the Permian Basin..."}

event: done
data: {}
```

### /api/optimize

```
event: progress
data: {"evaluated": 42, "total": 120, "pct": 35}

event: result
data: {"lat": 31.5, "lon": -104.2, "composite_score": 0.81, ...}

event: done
data: {"top_n": 5}
```

### /api/agent

```
event: token
data: {"text": "Based on current Waha prices..."}

event: citations
data: [{"url": "https://...", "title": "..."}]

event: done
data: {}
```

## Agent intent types

The AI Analyst classifies every query into one of five intents before routing to a tool:

| Intent | Trigger example | What happens |
|---|---|---|
| `stress_test` | *"What if gas spikes 40%?"* | Re-scores with modified gas price, shows delta vs. original |
| `compare` | *"Compare my pinned sites"* | Calls `/api/compare` on current pins, returns ranked table |
| `timing` | *"When should I build?"* | Combines LMP forecast + regime outlook into a recommendation |
| `explanation` | *"Why is land score low?"* | Reads SHAP values from the scorecard, explains in plain English |
| `config` | *"Set gas weight to 50%"* | Updates scoring weights and re-runs the last evaluation |
