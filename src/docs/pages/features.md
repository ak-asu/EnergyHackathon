# Platform Features

A walkthrough of every major feature in COLLIDE and how to use it.

## Interactive map

The map is the main interface. Predefined candidate sites appear as coloured markers — green for high composite score, red for low.

**How to use:**
- **Left-click** any point on the map to score it immediately
- **Right-click** for a context menu: evaluate, add to compare, add to optimizer region, add context for AI Analyst
- **Scroll** to zoom; drag to pan
- Toggle heat layers from the map controls (composite / gas / LMP score)

---

## Scorecard panel

After you click a site, the scorecard panel slides in from the right.

**What you see:**
- Composite score (0–1) with animated fill bar
- Sub-scores for land, gas, and power with SHAP feature explanations
- Cost breakdown: land acquisition, pipeline connection, water, BTM capex
- NPV range: P10 / P50 / P90 over 20 years
- AI-written narrative (streams in as it generates)
- Web enrichment sources (Tavily results that adjusted the score)

The panel loads in stages — scores appear first, then web context, then the narrative — so you don't wait for the full response before seeing numbers.

---

## Compare mode

Compare up to 5 sites side by side.

**How to use:**
1. Right-click any site → **Add to compare**
2. Repeat for up to 4 more sites (each gets a coloured pin)
3. Click **Compare** in the bottom strip
4. The compare modal opens with all sites ranked by composite score

Each column shows the full scorecard for one site. Scroll horizontally to compare across multiple sites.

---

## Optimizer

Finds the best sites within a region you define — useful when you have a general area in mind but haven't picked exact coordinates.

**How to use:**
1. Click **Optimize** in the bottom strip
2. Draw a rectangle on the map to define your search area
3. In the config dialog: set max sites, scoring weights, gas price cap, power cost cap, and market filter
4. Click **Run** — the optimizer streams progress as it evaluates a grid of points

**What it returns:** Top-N candidates ranked by composite score, shown as pins on the map. Click any pin to open its full scorecard.

The grid search runs at approximately 0.1° resolution across the bounding box.

---

## AI Analyst

A conversational AI interface that can answer questions about sites, run stress tests, and explain scoring decisions.

**How to open:** Click **⚡ AI Analyst** in the top-right navbar.

**What you can ask:**

| Intent | Example |
|---|---|
| Stress test | *"What if Waha gas prices spike 40% next quarter?"* |
| Compare | *"Compare the three sites I've pinned"* |
| Timing | *"When's the best time to start construction given current LMP trends?"* |
| Explain | *"Why is the land score so low for that site?"* |
| Configure | *"Set gas weight to 50% and re-score"* |

The analyst has access to your current scorecard, pinned sites, and any context chips you've added. Responses stream in token by token and include source citations.

**Context chips:** Right-click a map feature and choose **Add to analyst context** — a chip appears in the analyst panel and the AI references that data in its answers.

---

## Live market data

The stats bar at the top shows live market data, refreshed every 30 seconds:

- Waha Hub natural gas spot price ($/MMBtu) with 24 h change
- ERCOT West Hub real-time LMP ($/MWh)
- CAISO SP15 LMP ($/MWh)
- Balancing authority demand (GW) with net generation

---

## Live ticker

The strip at the bottom shows the current market regime, reclassified every 5 minutes:

| Regime | Meaning |
|---|---|
| Scarcity | LMP above generation cost — BTM economics are strong |
| Normal | Moderate spread — BTM is competitive |
| Oversupply | LMP depressed — BTM economics are weak |

The regime probability next to the label shows how confident the classifier is.

---

## Heat layers

Toggle between three GeoJSON overlays to visualise scores spatially:

| Layer | What it shows |
|---|---|
| Composite | Overall site score across the visible area |
| Gas | Gas supply reliability score only |
| LMP | Power economics score based on current LMP |

Layers are fetched from `/api/heatmap` and rendered as a Leaflet colour gradient overlay.

---

## 72-hour LMP forecast

Open a scored site's scorecard and go to the **Economics** tab. You'll see a 72-hour LMP forecast with P10/P50/P90 confidence bands, overlaid with the BTM generation cost line.

- If the P50 forecast is above the cost line, BTM economics are projected to be positive for that window
- The shaded band narrows as the model becomes more certain (typically tighter within 24 h)
- Forecasts are regenerated every hour in the background

The forecast model is called **Moirai** (after the Greek Fates). It uses ERCOT 5-minute LMP history, weather, and load forecasts as inputs.
