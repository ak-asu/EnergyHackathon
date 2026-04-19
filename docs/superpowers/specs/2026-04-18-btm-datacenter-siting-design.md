# BTM Data Center Site Selection Platform — Design Spec
**Date:** 2026-04-18  
**Hackathon:** ASU Collide Energy Hackathon (1-day, 4 expert builders)  
**Repo:** BhavyaShah1234/EnergyHackathon

---

## Problem Statement

AI data centers need massive, immediately available electricity. Public grid interconnection queues stretch 3–7 years. The solution is Behind-The-Meter (BTM) natural gas generation — build a private gas power plant on-site, bypass the grid queue entirely.

Siting a BTM data center requires three constraints solved simultaneously: (A) viable land parcel, (B) reliable gas supply, (C) BTM generation cheaper than grid import. No existing tool evaluates all three together. This platform does.

**The core gap we fill:** A unified, real-time engine that jointly scores land + gas reliability + power economics at any coordinate in a given region, with verifiable, explainable outputs.

---

## Two Interaction Modes

The user is given a **fixed bounded region** with pre-known infrastructure (power grids, gas sources, water sources, land legality, geography).

**Mode 1 — Evaluate a coordinate:** User clicks any (lat, lon) → system returns full scorecard: composite score, per-dimension breakdown, estimated 20-year development cost, 72-hour LMP + BTM spread forecast, AI-generated executive narrative.

**Mode 2 — Find optimal coordinate:** User clicks "Find Best Site" (or draws a polygon sub-region) → system runs Mode 1 across a grid of candidate points, finds the coordinate that maximizes composite suitability, animates the search on the map, returns the winner with full scorecard.

Mode 2 is Mode 1 parallelized over a grid — no architectural difference. Claude narration is called only once, for the winning coordinate, not for every grid point.

---

## Data Sources

### Live (silver parquet / DuckDB — already operational)

| Source | Dataset | Feeds |
|---|---|---|
| EIA-930 (AZPS, CISO, ERCO) | Grid demand, net generation, interchange | Regime classifier, Moirai features |
| EIA NG Spot (Henry Hub, Waha) | Daily gas spot prices | BTM spread formula |
| CAISO OASIS LMP | 5-min nodal LMP (Palo Verde, SP15, NP15) | Power economics |
| NOAA Forecast + Obs (Phoenix) | Hourly weather | Moirai features |
| BLM SMA (AZ/NM/TX) | Land ownership, acreage | Land scorer |
| FCC BDC Fiber | Fiber/FTTP coverage by census block | Land scorer |
| USGS NHD Waterbodies | Water body polygons | Distance feature |
| FEMA NFHL Floodplain | Flood zone classification | Hard filter + land scorer |
| EIA Gas Pipelines (WECC-SW + ERCOT) | Interstate/intrastate routes + `geometry_wkt` | Gas scorer, `pipeline_km` / `interstate_pipeline_km` features |

### Must add before hackathon

| Source | Why critical | How |
|---|---|---|
| **gridstatus.io ERCOT LMP** | Unblocks power economics while ERCOT MIS token pending | gridstatus.io API (free tier) |
| **gridstatus.io ERCOT fuel mix** | Wind%/solar%/gas% for regime classifier | gridstatus.io API |
| **gridstatus.io ERCOT interconnection queue** | "When to build" timing signal | gridstatus.io API |
| **PHMSA incident CSV** | Gas reliability model training data | ~~Free bulk download~~ **Akamai-blocked for automated clients** — manually download from phmsa.dot.gov and place at `data/raw/phmsa/`; ingestor reads local files |
| **Texas Railroad Commission GIS** | Texas-specific gas distribution | Free REST API |
| **Tavily API** | Live news: gas prices, energy policy, demand signals | API key |

> **EIA gas pipeline shapefiles** removed from this table — `pipelines_infra` is already live in silver (`ingestion/pipeline/sources/pipelines_infra.py`). Includes `geometry_wkt` (OGC LineString) for distance queries. See ingestion README for full schema.

### Static rasters (pre-downloaded, no API key needed)
- **USGS National Seismic Hazard Map** — peak ground acceleration raster, free download → interpolated to point in feature extraction
- **USFS National Fire Hazard Severity Zones** — wildfire risk raster, free download → interpolated to point

### Excluded (out of scope for hackathon)
ERCOT MIS (pending token — gridstatus.io covers this), PHMSA NPMS full topology (government-restricted), NREL EVI-Pro, Regrid commercial parcels, FERC filings.

---

## Scoring Factors

### Sub-A: Land & Lease Viability

Hard disqualifiers (applied before scoring):
- No contiguous 50-acre area within 500m radius of clicked coordinate (checked via BLM geometry — no viable data center footprint)
- FEMA flood zone A, AE, or V at coordinate (uninsurable / unbuildable)
- Federal wilderness / national park designation at coordinate

Scored features (LightGBM, output land_score ∈ [0,1]):
- Distance to nearest water body (cooling — inverse score)
- Distance to nearest fiber/FTTP route (latency risk)
- Distance to nearest natural gas pipeline
- Distance to nearest substation (grid backup)
- Distance to nearest highway (construction access)
- BLM ownership type (private > state > BLM federal for acquisition speed)
- FEMA flood zone gradient for non-disqualified zones (Zone X = 1.0, Zone X500 = 0.7, Zone D = 0.4)
- Air quality / EPA attainment area flag
- Seismic hazard index (USGS National Seismic Hazard raster, interpolated to point)
- Wildfire risk index (USFS National Fire Hazard Severity Zone raster, interpolated to point)

### Sub-B: Gas Supply Reliability

Spatial KDE heatmap on PHMSA incident locations, interpolated to (lat, lon):
- Incident density within 10km radius (weighted by cause: corrosion > material failure > excavation damage)
- Distance to nearest EIA interstate pipeline — query silver `pipelines_infra` table using `geometry_wkt` (WKT LineString, pipe_type ∈ {Interstate, Intrastate}); already live
- Distance to nearest TRC distribution line (still must-add for Texas)
- Distance to Waha Hub (West Texas primary supply point)
- Output: gas_score ∈ [0,1] via spatial interpolation from scored grid

> **PHMSA note:** Automated ingestion is Akamai-blocked. Files must be manually placed at `data/raw/phmsa/`; the PHMSA ingestor reads from disk, not a live API.

### Sub-C: Power Economics

BTM spread at any coordinate:
- `spread = LMP($/MWh) − (waha_price × 8.5 MMBtu/MWh + $3 O&M)` (heat rate 8.5 = CCGT, consistent across all scoring modules — existing sub_c.py uses 7.5 and must be updated)
- Positive spread → generate from gas turbine; negative → import from grid
- **Waha price** → silver `eia_ng` table, `series = 'RNGC4'`, field `price_usd_per_mmbtu`; Henry Hub = `RNGWHHD`
- LMP assigned via inverse-distance weighting from nearest 3 ERCOT buses (TX region) or CAISO buses (AZ/NM region), determined by coordinate's state; silver `caiso_lmp` field = `price_usd_per_mwh`, filter `lmp_component = 'LMP'`
- 72-hour forecast via Moirai-2.0 → spread forecast with P10/P50/P90
- Spread durability: % of trailing 90 days with positive spread
- Output: power_score ∈ [0,1] based on spread durability + forecast P50

### Market Regime (feeds into power economics + UI)

GMM (3-cluster) on: LMP level, LMP volatility, wind%, solar%, EIA-930 demand, reserve margin.  
Labels: `normal` | `stress_scarcity` | `wind_curtailment`  
Used as: categorical feature for Moirai-2.0 + plain-English UI badge.

---

## ML Models

### Model A: Land Scorer
- **Baseline (already exists):** Rule-based formula in `backend/scoring/sub_a.py` — acres, cost, fiber_km, water_km, ownership. Runs immediately with no training.
- **Upgrade:** LightGBM classifier + SHAP, replacing formula weights with learned weights. Training: positive class = known TX/AZ data center sites (geocoded); negative class = random coordinates failing hard filters. ~200 labeled examples sufficient.
- **Inference:** ~5ms per coordinate (tabular features, no heavy compute)
- **Explainability:** SHAP values returned per coordinate → waterfall chart in UI
- **Hackathon strategy:** Ship baseline first, upgrade to LightGBM if time allows.

### Model B: Gas Reliability Scorer
- **Algorithm:** Gaussian KDE on PHMSA incident coordinates, weighted by cause severity
- **Features:** Distance to nearest gas source (EIA + TRC), incident density within 10km, pipeline type (intrastate/interstate)
- **Inference:** Spatial interpolation from pre-computed raster grid (~1ms)
- **Validation:** Overlay KDE hotspots against publicly known Winter Storm Uri failure areas (Feb 2021 PHMSA incidents) — high-density zones must overlap

### Model C: Market Regime Classifier
- **Algorithm:** Gaussian Mixture Model, 3 components, EM-fit
- **Inputs:** Rolling 7-day LMP statistics (mean, σ), wind%, EIA-930 demand, reserve margin
- **Cadence:** Re-evaluated every 5 minutes against live EIA-930 + gridstatus.io data
- **Output:** Regime label + probability distribution over 3 states

### Model D: Power Economics Forecaster
- **Algorithm:** Moirai-2.0 (`Salesforce/moirai-1.0-R-large`, HuggingFace)
- **Why Moirai-2.0 over TimesFM/PatchTST:** 2024-2025 benchmarks show TimesFM fails to beat seasonal naive on actual electricity price datasets. Moirai-2.0 natively supports exogenous features and ranks top under MASE/CRPS on energy benchmarks.
- **Inputs:** 90-day LMP history at nearest ERCOT/CAISO node, Waha gas price, EIA-930 load forecast, wind%, NOAA temperature forecast, regime label (categorical)
- **Output:** 72-hour LMP + BTM spread forecast, P10/P50/P90 prediction intervals
- **Inference cadence:** Pre-computed hourly for active region nodes; served from cache

### Model E: Composite Scorer (TOPSIS)
- **Algorithm:** TOPSIS normalization over [land_score, gas_score, power_score]
- **Weights:** ML-learned from historical site success proxies; user-overridable via sliders
- **Output:** composite_score ∈ [0,1] + dimension attribution

### Model F: Monte Carlo Cost Simulator
- **Not a trained model** — parameterized numpy simulator, 10,000 scenarios, <2s
- **Inputs:** Gas price distribution (μ=Waha current, σ=30d vol), LMP distribution (from Moirai intervals), demand scenario
- **Output:** P10/P50/P90 BTM spread over 20 years → NPV distribution at configurable WACC

---

## GNN Assessment

| Application | Verdict | Reason |
|---|---|---|
| LMP forecasting (GCN on ERCOT topology) | **Post-hackathon YES** | Proven 5-15% MAPE improvement; requires full ERCOT bus-line topology + per-node historical LMP; wire after hackathon |
| Pipeline reliability (GNN on network) | **Post-hackathon, if data improves** | 92% accuracy in literature but requires segment-level material/age/pressure; PHMSA public data too sparse |
| Land scoring (SC-GCN on parcel adjacency) | **Post-hackathon YES** | Proven ~5-8% accuracy gain for neighborhood effects; requires parcel shapefile graph construction |

None of the three GNN applications are feasible within the hackathon day without pre-built graph infrastructure.

---

## System Architecture

### Layer 0 — Data Lake (existing)
Raw → Bronze → Silver parquet, DuckDB catalog, Pandera-validated, provenance-traced. Owned by data engineer. New sources (gridstatus.io, PHMSA, EIA pipelines) follow same `BaseIngestor` pattern.

### Layer 1 — Feature Extraction
`extract_features(lat, lon) → FeatureVector`  
Pure DuckDB spatial queries:
- Nearest-neighbor lookups: water body, fiber node, gas pipeline, ERCOT bus, substation, highway
- Point-in-polygon: FEMA flood zone, BLM ownership type, EPA attainment area
- Raster interpolation: seismic hazard, wildfire risk (pre-rasterized USGS/USFS layers)
- Returns structured FeatureVector in ~50ms

### Layer 2 — Sequential Scoring Pipeline
```
evaluate_coordinate(lat, lon, weights) → SiteScorecard
  features   = extract_features(lat, lon)
  land       = score_land(features)          # LightGBM → land_score + SHAP
  gas        = score_gas(lat, lon)           # KDE interpolation → gas_score
  regime     = get_regime()                  # cached GMM state, refreshed every 5min
  power      = forecast_power(features.ercot_node, regime)  # Moirai-2.0 cache
  cost       = estimate_costs(features, land, gas, power)    # rule-based + Monte Carlo
  composite  = topsis(land, gas, power, weights)
  return SiteScorecard(...)
```

No agent wrapping. Deterministic, fully auditable, ~200ms end-to-end (excluding LLM narration).

### Layer 3 — LLM Narration (Claude API)
Called once per scorecard, after the pipeline completes. Streamed via SSE.  
Single prompt: structured system prompt with all scorecard fields → 3-paragraph executive summary:
1. Site overview: what makes it strong/weak
2. Key risk: which dimension is the binding constraint and why
3. Timing recommendation: based on regime + news digest

### Layer 4 — LangGraph Interactive Agent
Invoked **only** from the AI assistant panel in the UI. Not part of core scoring.

StateGraph nodes:
- `parse_intent` → classifies user query (stress_test | comparison | timing | explanation)
- `run_stress_test` → reruns pipeline with perturbed params, computes rank delta
- `compare_sites` → runs pipeline at multiple coordinates, formats comparison table
- `synthesize` → Claude narration of agent findings, streamed

Tools available to agent: `evaluate_coordinate`, `get_lmp_forecast`, `get_news_digest`, `run_monte_carlo`

### Layer 5 — FastAPI Backend

Existing endpoints (keep, do not break):
```
GET  /api/health                                           → {status, service}
GET  /api/sites                                            → SiteResponse[] (all 8 sites scored)
GET  /api/sites/{site_id}                                  → SiteResponse (single site)
GET  /api/market                                           → MarketResponse (gas, LMP, demand)
POST /api/pipeline/run                                     → pipeline run summary
```

New endpoints to add:
```
POST /api/evaluate              {lat, lon, weights?}       → SSE stream: SiteScorecard
POST /api/optimize              {bounds, weights?}         → SSE stream: progress + OptimalResult
GET  /api/heatmap               {bounds, layer, zoom}      → GeoJSON points for leaflet.heat
GET  /api/forecast              {node, horizon?}           → ForecastResult
GET  /api/regime                                           → RegimeState
GET  /api/news                                             → NewsDigest (cached 30min)
POST /api/stress-test           {lat, lon, scenario}       → SSE stream: StressTestResult
GET  /api/compare               {coords[]}                 → SiteScorecard[]
WS   /api/lmp/stream                                       → real-time LMP ticks (5-min)
```

Background jobs (APScheduler):
- 5min: refresh LMP + EIA-930 → update regime GMM state
- 1hr: rerun Moirai-2.0 cache for active region nodes
- 30min: refresh Tavily news digest

### Layer 6 — Frontend (Vite + React)

Single-page application. 15 components already scaffolded (hero, dashboard, scoring cards, workflow, data sources, markets, quality, footer). Map and scorecard panel are the primary additions.

**Map (react-leaflet + leaflet.heat)**
Already in use: react-leaflet 4.2 with CircleMarkers, Rectangles, Popups, click handlers.
New layers to add (toggleable):
- Composite heatmap: `leaflet.heat` plugin, points weighted by TOPSIS score, color gradient
- LMP contour surface: L.polygon grid colored by interpolated $/MWh, updated every 5min via WebSocket
- Gas reliability heatmap: KDE density pre-rendered as heat layer (red/yellow/green)
- Infrastructure overlays: gas pipeline routes, substations, fiber routes, water bodies (GeoJSON L.geoJSON layers)
- Mode 2 optimal coordinate marker (pulsing L.circleMarker with score badge popup)
- Mode 2 search animation: grid polygon cells highlight in sweep pattern as `/api/optimize` SSE streams progress

Interactions:
- Click anywhere → fires Mode 1 → scorecard panel slides in from right
- "Find Best Site" button → Mode 2 fires, sweep animation plays, optimal pin drops
- Draw polygon tool → constrains Mode 2 search area
- Hover on hex → mini-tooltip: composite score + dominant factor

**Scorecard Panel (right side, opens on Mode 1)**  
Three tabs:

*Summary tab:*
- Large color-coded gauge: composite score
- Horizontal bars: land | gas | power scores with SHAP attribution labels
- Estimated 20-year NPV: P10 / P50 / P90 ranges
- Claude narrative streaming in below (typewriter effect)
- Regime badge: colored pill showing current market state

*Economics tab:*
- 72-hour LMP forecast: Recharts AreaChart, confidence bands shaded
- BTM spread overlay: green fill (positive spread = generate), red fill (negative = import)
- Sensitivity sliders: Gas price ±$2/MMBtu, LMP multiplier 0.5×–3×, WACC 6–12%
- Sliders recompute NPV and charts live via Monte Carlo pre-computed distributions (no API call)

*Risk tab:*
- One-click stress test buttons: "Uri Equivalent", "Gas +40%", "3-Day Wind Curtailment", "LMP ×2"
- Each shows: rank change (↑2 / ↓3), NPV impact ($M), which dimension breaks first
- Breakeven chart: gas price vs. BTM spread (line crosses zero at breakeven)
- SHAP waterfall chart: factor-level attribution for composite score

**Bottom Strip (persistent)**
- Live LMP ticker: scrolling price updates for active ERCOT/CAISO nodes (WebSocket)
- Regime indicator: pulsing dot + label ("Wind Curtailment — grid cheap now")
- ERCOT fuel mix donut: real-time wind% / solar% / gas% / other%
- News cards: 3 Tavily headlines, auto-refreshed every 30min

**Compare Mode**
- Click multiple coordinates → "Compare" button appears in header
- Side-by-side scorecard table: all dimensions, estimated costs, NPV P50
- Radar chart: each site as a polygon across land / gas / power / timing axes

---

## Cost Estimation Formula

| Component | Estimate Basis |
|---|---|
| Land acquisition | Ownership proxy: private ~$2k/acre, state ~$800/acre, BLM ~$400/acre |
| Gas pipeline connection | Distance to nearest gas source × $1.2M/mile (industry rule of thumb) |
| Water connection | Distance to nearest water body × $400k/mile |
| BTM generation capex | $800/kW × 100MW default → $80M fixed (user-configurable MW) |
| Ongoing power cost | BTM spread P50 × annual MWh consumption |
| 20-year NPV | DCF at user-set WACC (default 8%) over P10/P50/P90 spread scenarios |

All cost components surfaced individually in scorecard. Confidence ranges shown explicitly.

---

## Team Split

| Builder | Owns | Key deliverables |
|---|---|---|
| **Data + Features** | Add gridstatus.io (ERCOT LMP, fuel mix, queue) to silver; manually upload PHMSA CSV to `data/raw/phmsa/` + write local-file ingestor; `extract_features(lat, lon)` function wiring real DuckDB spatial queries | Feature vector schema, DuckDB spatial queries against `data/_meta/catalog.duckdb`, KDE gas scorer raster — EIA pipelines already live |
| **ML Models** | LightGBM land scorer + SHAP; Moirai-2.0 fine-tune + forecast cache; GMM regime classifier; cost estimator + Monte Carlo; TOPSIS | All model inference functions, `SiteScorecard` dataclass |
| **Backend + Agent** | FastAPI all endpoints; sequential pipeline wiring; LangGraph stress-test agent; Claude streaming narration; APScheduler background jobs | FastAPI app, `evaluate_coordinate()` pipeline, LangGraph graph |
| **Frontend** | Vite + React app; Deck.gl map + all layers; scorecard panel + Recharts charts; sensitivity sliders; Mode 2 animation; news/regime strip | Full React SPA, Deck.gl integration, WebSocket + SSE consumers |

Contract between builders: `SiteScorecard` Python dataclass (ML → Backend). Frontend is plain JavaScript — the existing `useApi.js` adapter handles snake_case → camelCase conversion and serves as the type boundary. No TypeScript or code generation required.

---

## Verification Strategy

- **LMP forecast:** Walk-forward backtest on 2024 ERCOT data, report MAPE on 72h holdout window
- **Gas reliability:** Overlay KDE hotspots against Feb 2021 Uri incident clusters — must show >70% spatial overlap
- **Land scorer:** Cross-validation AUC on holdout parcels (known TX data center locations as positive class)
- **Composite scorer:** Sanity check top-3 ranked coordinates against known VoltaGrid/Oracle West Texas BTM project locations — model should rank those areas highly
- **Cost estimates:** Cross-check 20-year NPV against published BTM data center deal economics ($0.03–0.06/kWh as viable range)

---

## Innovation Summary

What no existing tool does that this system does:

1. **Unified cross-dimensional scoring** at arbitrary coordinates — not from a fixed parcel database
2. **Mode 2 spatial optimization** — actively finds the best coordinate rather than waiting for user to guess
3. **Adversarial stress testing** — one-click scenario simulation with rank delta visualization
4. **Verifiable outputs** — SHAP attribution, confidence intervals, backtesting shown in UI
5. **Real-time intelligence synthesis** — live LMP + fuel mix + Tavily news → regime-aware narrative
6. **Explainable AI for infrastructure decisions** — every score has a plain-English "why" from Claude

---

## Out of Scope (This Hackathon)

- GNN layers (all three applications deferred — documented for post-hackathon roadmap)
- ERCOT MIS direct API (covered by gridstatus.io fallback)
- PHMSA NPMS full topology (government-restricted; KDE heatmap is the proxy)
- Regrid commercial parcel database (BLM + FCC fiber is sufficient for region-level analysis)
- Multi-region support beyond Texas/Southwest (ERCOT + CAISO only)
- User authentication / saved sessions
