# COLLIDE Gap Closure & AI Analyst System — Design Spec
**Date:** 2026-04-18
**Extends:** `2026-04-18-btm-datacenter-siting-design.md` (original spec)

---

## Problem Statement

The original spec fully defines the platform architecture, ML models, scoring pipeline, and LangGraph agent system. A subset of those features was not implemented in the first integration pass. This spec defines exactly what remains and how it integrates — no architectural changes to the original design.

---

## Scope: What Remains to Build

| Gap | Original Spec Reference | Status |
|-----|------------------------|--------|
| AI Analyst panel (auto-briefing + chat) | Layer 4 LangGraph, Layer 6 Frontend | Missing |
| Agent tools: news, forecast, monte carlo, web search | Layer 4 tools list | Partial (evaluate_site + compare_sites only) |
| Pipeline trigger button + last-run status | Dashboard header | Missing |
| LMP node selector dropdown | EconomicsTab | Missing (hardcoded) |
| Regime probability bars (3-component) | SummaryTab, `/api/regime` | Missing (label only) |
| Compare mode (multi-pin + radar chart) | Frontend spec Compare Mode | Missing |
| Map heatmap layers (composite, gas KDE, LMP contour) | Map spec new layers | Missing |
| ML model file loading with rule-based fallback | All scoring modules | Missing (rules only) |

---

## AI Analyst System

### Backend: LangGraph Agent (`backend/agent/graph.py`)

Full StateGraph with explicit intent routing:

```
parse_intent
    ↓ classifies: stress_test | compare | timing | explanation
    ↓
[stress_test_node] → perturb params → rerun pipeline → compute rank delta
[compare_node]     → evaluate N coordinates → rank → format table
[timing_node]      → get_regime → get_news → conditional web_search → synthesize
[explanation_node] → load scorecard → run SHAP → narrate attribution
    ↓
synthesize_node → Claude streaming narrative with inline citations
    ↓
SSE token stream → POST /api/agent
```

**State schema:**
```python
class AgentState(TypedDict):
    query: str
    intent: str                  # stress_test | compare | timing | explanation
    context: dict                # scorecard, map_bounds, regime — sent by frontend
    tool_results: list[dict]
    citations: list[str]         # news titles, node names, coordinates cited
    response_tokens: list[str]
```

**Tools (all nodes can access):**
- `evaluate_site(lat, lon)` → scorecard dict
- `compare_sites(coords: list[tuple])` → ranked scorecard list
- `get_news_digest()` → cached Tavily items (30-min cache)
- `get_lmp_forecast(node: str, horizon: int = 72)` → {p10, p50, p90, method}
- `run_monte_carlo(gas_price, lmp_p50, wacc, years)` → {p10_npv, p50_npv, p90_npv}
- `web_search(query: str)` → Tavily search results (agent-triggered, not on every call)

**Web search policy:** The `timing_node` calls `web_search` only when the agent's `parse_intent` output includes `needs_web_search: true` — set when query contains forward-looking language ("will", "forecast", "policy", "regulation") or when news digest is stale (>30 min).

**New endpoint:**
```
POST /api/agent
Body: {query: str, context?: {scorecard?, bounds?, regime?}}
Response: SSE stream
  {type: "token", content: "..."}     ← streamed Claude tokens
  {type: "citation", content: "..."}  ← source name (news title, node, coord)
  {type: "done"}
  {type: "error", content: "..."}
```

### Backend: Extended Endpoints

```
GET  /api/regime
  Before: {label: str, proba: [float, float, float]}
  After:  {label: str, proba: [float, float, float], labels: ["normal","stress_scarcity","wind_curtailment"]}

GET  /api/forecast?node=HB_WEST&horizon=72
  Returns: {p10: float[], p50: float[], p90: float[], method: str, node: str, btm_cost_mwh: float}

GET  /api/heatmap?layer=composite&bounds=lat1,lon1,lat2,lon2&zoom=8
  Returns: GeoJSON FeatureCollection (points with score property)
  Empty FeatureCollection if no silver data — never 500.

GET  /api/compare?coords=31.9,-102.1;32.5,-101.2;33.1,-100.8
  Returns: SiteScorecard[] sorted by composite_score desc
```

---

## ML Model Integration

### Loading Strategy (all scoring modules)

Each module loads its `.pkl` at import time. If the file is missing, the module falls back to the existing rule-based formula silently. No API error is exposed.

```python
# Pattern used in land.py, gas.py, regime.py, power.py
import pickle, os

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "../../data/models")

def _load(filename):
    path = os.path.join(_MODEL_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None
```

### Model Files → Modules

| File | Module | Output when loaded |
|------|--------|-------------------|
| `land_lgbm.pkl` + `land_lgbm.shap.pkl` | `backend/scoring/land.py` | LightGBM probability + SHAP values per feature |
| `gas_kde.pkl` | `backend/scoring/gas.py` | KDE log-density → reliability score |
| `regime_gmm.pkl` | `backend/scoring/regime.py` | GMM label + `proba[3]` (unpacks 3-tuple: gmm, scaler, label_map) |
| `power_forecast_cache.pkl` | `backend/scoring/power.py` | Moirai P10/P50/P90 per node |
| `power_durability.pkl` | `backend/scoring/power.py` | Logistic regressor P(spread > 0) |

### Regime GMM unpacking (per training script note)
```python
gmm, scaler, label_map = pickle.load(f)
raw = int(gmm.predict(scaler.transform([features]))[0])
label_idx = label_map[raw]   # 0=normal, 1=stress_scarcity, 2=wind_curtailment
proba = gmm.predict_proba(scaler.transform([features]))[0]
```

---

## Frontend Components

### New: `AIAnalystPanel.jsx`

Slide-in panel from the right side, independent of ScorecardPanel. Toggled by a brain icon in Navbar. Both panels can be open simultaneously (ScorecardPanel occupies 400px right, AIAnalystPanel occupies 420px further right — or stacks on smaller screens).

**Sub-components:**

`BriefingCard.jsx`
- Fires automatically on Dashboard mount (or when panel first opens)
- Sends: `POST /api/agent` with query = "Give me a current market briefing: regime state, top-ranked site opportunity, and key risk." + current regime context
- Renders streamed response in 3 labeled sections: Regime / Opportunity / Risk
- Refresh button re-fires the briefing
- Shows `fetched_at` timestamp

`AgentChat.jsx`
- Chat input at bottom, message history scrolls up
- Each assistant message streams tokens with inline citation chips (colored pills: news = blue, site coord = green, forecast node = orange)
- User messages shown right-aligned
- "Thinking..." indicator while `parse_intent` runs (before first token)
- Error messages shown inline in red, never crash the panel

### Modified: `SummaryTab.jsx`

Add regime probability section below the regime badge:
- Three horizontal bars: Normal / Stress-Scarcity / Wind Curtailment
- Bar width = probability value, labeled with percentage
- Color: normal=green, stress=red, wind=blue
- Source: `proba` array from `GET /api/regime`

### Modified: `EconomicsTab.jsx`

Replace hardcoded node with a dropdown selector:
- Options: HB_WEST, HB_NORTH, HB_SOUTH, PALOVRDE_ASR-APND
- Selecting a node calls `GET /api/forecast?node=X` and re-renders the 72h chart
- Default: nearest node to evaluated coordinate (passed from parent)

### Modified: `Dashboard.jsx`

Add to header row:
- "Refresh Data" button (subtle, secondary style) → calls `POST /api/pipeline/run`
- Spinner while running, then "Last updated: HH:MM AM/PM" timestamp
- On error: red toast "Pipeline failed — using cached data"

### Modified: `SiteMap.jsx`

Add layer toggle controls (top-right map corner):
- Composite score heatmap (calls `GET /api/heatmap?layer=composite`)
- Gas reliability layer (calls `GET /api/heatmap?layer=gas`)
- LMP contour layer (static colored polygons from last WebSocket tick)
- Each toggle is a checkbox pill — layers stack

Add compare mode:
- Shift+click adds coordinate to compare list (max 5)
- Compare list shown as numbered pins
- "Compare Sites" button appears in map header when ≥2 pins selected
- Clears with Escape or "Clear" button

### New: `CompareMode.jsx`

Modal or full-width panel below map:
- Calls `GET /api/compare?coords=...` with all selected pins
- Side-by-side table: each site as a column, rows = composite/land/gas/power/npv_p50/regime
- `RadarChart` (Recharts) with each site as a colored polygon across 4 axes: Land / Gas / Power / Cost Efficiency
- "Export CSV" button (client-side, no API call)
- Close button returns to normal map mode

---

## Error Handling

| Failure | Backend behavior | Frontend behavior |
|---------|-----------------|------------------|
| ML model file missing | Silent fallback to rules, log warning | No indication — scores still appear |
| Agent SSE error | Stream `{type: "error", content: msg}` | Inline red message in chat |
| Tavily/web search fails | Agent continues without search, appends "(web search unavailable)" | Shown in agent response text |
| `GET /api/heatmap` no data | Return empty GeoJSON `{features: []}` | Layer toggle grays out, tooltip "No data" |
| Pipeline trigger fails | Return `{status: "error", message: "..."}` | Red toast in Dashboard header |
| `GET /api/compare` coordinate outside region | Return scorecard with `disqualified: true` | Row shown in red in compare table |
| WebSocket LMP disconnect | Frontend auto-reconnects after 3s backoff | BottomStrip shows "Reconnecting..." |

---

## File Map

**Create:**
- `src/components/AIAnalystPanel.jsx`
- `src/components/BriefingCard.jsx`
- `src/components/AgentChat.jsx`
- `src/components/CompareMode.jsx`
- `src/hooks/useAgent.js`
- `src/hooks/useForecast.js`
- `src/hooks/useHeatmap.js`
- `src/hooks/useCompare.js`

**Modify:**
- `backend/agent/graph.py` — full LangGraph StateGraph with 4 intent nodes + 6 tools
- `backend/agent/tools.py` — add get_news_digest, get_lmp_forecast, run_monte_carlo, web_search
- `backend/scoring/land.py` — add pkl loading + SHAP output
- `backend/scoring/gas.py` — add KDE pkl loading
- `backend/scoring/regime.py` — add GMM pkl loading, extend API response with labels
- `backend/scoring/power.py` — add forecast cache + durability model loading
- `backend/main.py` — add /api/forecast, /api/heatmap, /api/compare endpoints; extend /api/regime
- `src/components/SummaryTab.jsx` — add regime probability bars
- `src/components/EconomicsTab.jsx` — add node selector dropdown
- `src/components/Dashboard.jsx` — add pipeline trigger button + timestamp
- `src/components/SiteMap.jsx` — add layer toggles + compare mode pins
- `src/components/Navbar.jsx` — add AI analyst toggle button

---

## Out of Scope (this implementation)

- GNN layers (deferred per original spec)
- ERCOT MIS direct API
- Multi-region beyond TX/CAISO
- User authentication / saved sessions
- Export to PDF / presentation format
