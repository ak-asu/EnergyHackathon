# Map Interactions, Config Dialog & Agent Context — Design Spec

**Date:** 2026-04-19  
**Status:** Approved

---

## Overview

Redesign the SiteMap interaction model with right-click context menus, an optimization config dialog, agent context chips, global loading/deduplication, and minor backend extensions. All new state lives in feature hooks following the existing `useOptimize` / `useCompare` / `useAgent` pattern.

---

## 1. Map Interactions

### Left-click behavior

- Remove `MapClickHandler` that fires `collide:evaluate` on every plain map click.
- Clicking a site marker does nothing by default.
- Clicking the **optimal site marker** (green ring) opens its scorecard panel directly — it is a suggested site, so clicking it is an intentional selection action.

### Right-click context menu

A `MapContextMenu` component renders as an absolutely-positioned `div` via React portal to `document.body` at the cursor position. Leaflet's native `contextmenu` event is suppressed. The menu closes on outside-click or Escape.

Only one menu is open at a time. Two variants based on click target:

**On an existing site marker:**
- Evaluate site → fires `collide:evaluate` for that site's lat/lon, opens ScorecardPanel
- Add to compare → adds site as compare pin
- Send to agent → adds a `type: "site"` context chip in the agent panel
- Set as region center → re-centers the committed selection bounds around this site's coords (option hidden if no committed bounds exist)

**On empty map space:**
- Evaluate this location → fires `collide:evaluate` for the clicked lat/lon
- Add compare pin here → adds a compare pin at the clicked coord
- Send location to agent → adds a `type: "coord"` context chip in the agent panel

### Toolbar

Unchanged. "Select area" / "Clear area" / "Find Best Site" / new "Config" button.

---

## 2. Optimization Config Dialog

### `useOptimizeConfig` hook

Owns config state. Listens for `collide:set-config` window events (merges partial updates). If a `collide:set-config` event fires while committed bounds exist, fires a `collide:run-optimize` window event. `SiteMap` listens for `collide:run-optimize` and calls `optimize()` directly — this avoids the hook needing a direct reference to `optimize()` and keeps composition at the component level.

Default config shape:

```js
{
  maxSites: 3,           // number of optimal sites to return
  gasPriceMax: 5.0,      // $/MMBtu ceiling (null = no limit)
  powerCostMax: 80,      // $/MWh ceiling (null = no limit)
  acresMin: 500,         // minimum parcel size in acres
  weights: [0.30, 0.35, 0.35],  // land / gas / power (must sum to 1)
  marketFilter: [],      // [] = all markets; or subset of ['ERCOT','CAISO','SPP']
  minComposite: 0.70,    // minimum composite score threshold (0–1)
}
```

### `OptimizeConfigDialog` component

Modal opened by a **"Config"** button added to the sitemap toolbar (right of "Find Best Site"). Contains:

- Weight sliders for land/gas/power — locked so they always sum to 1 (adjusting one redistributes remainder proportionally across the other two)
- Number inputs for `gasPriceMax`, `powerCostMax`, `acresMin`
- `minComposite` slider (0.50–0.95)
- `maxSites` stepper (1–10)
- `marketFilter` multi-select checkboxes (ERCOT, CAISO, SPP, All)
- **Apply** button — saves config to hook state, closes modal
- **Reset** button — restores all defaults without closing
- When reopened after agent modification, shows the agent-applied values

### Backend — `/api/optimize` extension

`OptimizeRequest` gains optional fields:

```python
max_sites: int = 3
gas_price_max: float | None = None
power_cost_max: float | None = None
acres_min: int = 0
market_filter: list[str] = []
min_composite: float = 0.0
```

The optimize loop filters candidate grid points against hard constraints before scoring. Returns up to `max_sites` results via the existing SSE stream.

---

## 3. Agent Context Chips

### `useMapContext` hook

Maintains an array of context items:

```js
{ type: "region" | "site" | "coord", payload: { ... } }
```

Rules:
- Max one `"region"` chip at a time (new one replaces old)
- Max 3 `"site"` / `"coord"` chips (oldest dropped when exceeded)
- Region chip is auto-added when the user commits a selection area
- Site/coord chips are added via right-click menu "Send to agent" actions

### `ContextChipBar` component

Renders above the `AgentChat` textarea when chips are present. Each chip is a dismissible pill (styled like existing `citation-chip`). Clicking × removes that chip.

### Agent integration

`AgentChat` receives the chip array via the existing `context` prop (passed through `App` → `AIAnalystPanel` → `AgentChat`). The `ask()` call includes chips in the context payload sent to `/api/agent/stream`.

In the backend, `parse_intent_node` and `synthesize_node` read `context.region` and `context.chips` and include them as grounding data in the synthesize system prompt.

### Agent config update via function calling

A new `set_optimize_config` tool is added to `tools.py` and `ALL_TOOLS`:

```python
@tool
def set_optimize_config(
    max_sites: int | None = None,
    gas_price_max: float | None = None,
    power_cost_max: float | None = None,
    acres_min: int | None = None,
    weights: list[float] | None = None,
    market_filter: list[str] | None = None,
    min_composite: float | None = None,
) -> dict:
    """Update optimization configuration constraints and trigger re-optimization."""
```

The agent response SSE stream includes a `config_update` event when this tool is called. Specifically: `graph.py` emits an SSE event `event: config_update` with the tool result payload before the final `synthesize_node` response. `useAgent` intercepts this event type and fires `collide:set-config` with the payload — config state is purely frontend, no backend config storage required.

---

## 4. Loading Indicators & Request Deduplication

### `MapStatusIndicator` component

Renders inside `MapContainer` at top-left (below zoom controls) as a small pill with a pulsing dot. Displays context-appropriate label:
- "Evaluating…" — scorecard evaluate in flight
- "Optimizing…" — optimize SSE stream running
- "Comparing…" — compare request in flight

Hidden when idle. `SiteMap` receives a `mapBusy` boolean prop.

### `globalBusy` state in `App`

`optStatus` and `optimal` are lifted from `SiteMap`-local state into `App` (passed down as props to `SiteMap`) so `globalBusy` can reference them. `globalBusy` is `true` when any of: `optStatus === 'running'`, `compareStatus === 'loading'`, evaluate in flight, or `agentStatus === 'loading' | 'streaming'`.

When `globalBusy` is true:
- Right-click menu actions that trigger network calls are visually disabled
- "Find Best Site" and "Compare Sites →" buttons are disabled
- Agent send button is disabled
- Incoming `collide:set-config` events are queued (max depth 1, last-write-wins); processed once `globalBusy` clears

### Agent chat indicator

No change to existing "Thinking…" / streaming bubble. When agent triggers a config update + optimize, the thinking bubble shows "Running optimization…" until `optimal` is set.

---

## 5. New Files & Changed Files

| File | Change |
|---|---|
| `src/components/MapContextMenu.jsx` | New — right-click menu component (portal) |
| `src/components/OptimizeConfigDialog.jsx` | New — modal config dialog |
| `src/components/ContextChipBar.jsx` | New — chip bar above agent chat textarea |
| `src/components/MapStatusIndicator.jsx` | New — in-map loading pill |
| `src/hooks/useOptimizeConfig.js` | New — config state + event listener |
| `src/hooks/useMapContext.js` | New — context chip state |
| `src/components/SiteMap.jsx` | Modified — remove MapClickHandler, add right-click, pass mapBusy, add Config button |
| `src/components/AgentChat.jsx` | Modified — render ContextChipBar, pass chips to ask() |
| `src/components/AIAnalystPanel.jsx` | Modified — pass mapContext chips to AgentChat |
| `src/App.jsx` | Modified — globalBusy, wire new hooks, pass context |
| `src/hooks/useOptimize.js` | Modified — accept config fields, forward to API |
| `src/hooks/useAgent.js` | Modified — intercept config_update SSE event |
| `backend/main.py` | Modified — extend OptimizeRequest model + filter logic |
| `backend/agent/tools.py` | Modified — add set_optimize_config tool |
| `backend/agent/graph.py` | Modified — read context.region/chips in synthesize node |
