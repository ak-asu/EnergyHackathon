# Map Interactions, Config Dialog & Agent Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add right-click context menus, optimization config dialog, agent context chips, global loading indicators, and request deduplication to the COLLIDE SiteMap.

**Architecture:** `useOptimize` and `useOptimizeConfig` lifted to App for global state access; `useMapContext` in App for chip sharing between SiteMap and AgentChat. Cross-component coordination uses the existing `collide:*` window CustomEvent pattern. `MapContextMenu` renders via React portal at cursor position. A new `"config"` LangGraph intent extracts config changes from natural language and emits `config_update` SSE for the frontend to apply.

**Tech Stack:** React 18, react-leaflet 4, Vitest + @testing-library/react (frontend), pytest (backend)

---

## File Map

| File | Action |
|---|---|
| `src/test-setup.js` | Create — @testing-library/jest-dom import |
| `src/hooks/useOptimizeConfig.js` | Create — config state, `collide:set-config` listener, fires `collide:run-optimize` |
| `src/hooks/useMapContext.js` | Create — chip array management |
| `src/components/MapContextMenu.jsx` | Create — right-click portal, two variants |
| `src/components/MapStatusIndicator.jsx` | Create — in-map busy pill |
| `src/components/OptimizeConfigDialog.jsx` | Create — modal with sliders/inputs |
| `src/components/ContextChipBar.jsx` | Create — dismissible chip row |
| `src/hooks/__tests__/useOptimizeConfig.test.js` | Create |
| `src/hooks/__tests__/useMapContext.test.js` | Create |
| `src/components/__tests__/MapContextMenu.test.jsx` | Create |
| `src/components/__tests__/MapStatusIndicator.test.jsx` | Create |
| `src/components/__tests__/OptimizeConfigDialog.test.jsx` | Create |
| `src/components/__tests__/ContextChipBar.test.jsx` | Create |
| `backend/tests/__init__.py` | Create |
| `backend/tests/test_optimize_filters.py` | Create |
| `backend/tests/test_config_node.py` | Create |
| `vite.config.js` | Modify — add `test` section |
| `package.json` | Modify — add test deps + scripts |
| `src/hooks/useOptimize.js` | Modify — accept config object, forward all fields to API |
| `src/hooks/useAgent.js` | Modify — intercept `config_update` SSE event |
| `src/components/SiteMap.jsx` | Modify — remove MapClickHandler, add right-click, MapStatusIndicator, Config button, `collide:run-optimize` listener |
| `src/components/AgentChat.jsx` | Modify — render ContextChipBar, accept chips/onRemoveChip |
| `src/components/AIAnalystPanel.jsx` | Modify — thread chips/onRemoveChip |
| `src/App.jsx` | Modify — useOptimize/useOptimizeConfig/useMapContext in App, globalBusy, all new prop wiring |
| `backend/main.py` | Modify — extend OptimizeRequest, filter logic, emit `config_update` SSE in agent endpoint |
| `backend/agent/tools.py` | Modify — no new tool needed (config_node handles it directly) |
| `backend/agent/graph.py` | Modify — add `config` intent + `config_node`, update synthesize to read chips/region from context |

---

## Tasks

### Task 0: Test Infrastructure

**Files:**
- Modify: `package.json`
- Modify: `vite.config.js`
- Create: `src/test-setup.js`

- [ ] **Step 1: Install test dependencies**

```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Expected: packages added to `node_modules`, `package.json` devDependencies updated.

- [ ] **Step 2: Add test scripts to package.json**

In `package.json`, update `scripts`:
```json
"scripts": {
  "dev": "vite",
  "dev:api": ".\\.venv\\Scripts\\python.exe scripts/run_api.py",
  "dev:api:reload": ".\\.venv\\Scripts\\python.exe scripts/run_api.py --reload",
  "build": "vite build",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 3: Add test config to vite.config.js**

Add a `test` block inside the returned config object (after `build:`):
```js
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: ['./src/test-setup.js'],
},
```

Full updated `vite.config.js`:
```js
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { collideApiDevProxy } from './vite-plugin-collide-api.js'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const fallbackApiPort = env.COLLIDE_API_PORT || '32587'

  return {
    plugins: [collideApiDevProxy(fallbackApiPort), react()],
    optimizeDeps: {
      include: ['leaflet', 'react-leaflet'],
    },
    server: {},
    build: {
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom'],
            'vendor-charts': ['recharts'],
            'vendor-map': ['leaflet', 'react-leaflet'],
          },
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test-setup.js'],
    },
  }
})
```

- [ ] **Step 4: Create src/test-setup.js**

```js
import '@testing-library/jest-dom'
```

- [ ] **Step 5: Install backend pytest deps and create test directory**

```bash
.venv/Scripts/pip install pytest pytest-asyncio httpx
```

Create `backend/tests/__init__.py` (empty file).

- [ ] **Step 6: Verify test runner works**

```bash
npm test
```

Expected: `No test files found` (no failures — infrastructure is working).

- [ ] **Step 7: Commit**

```bash
git add vite.config.js package.json package-lock.json src/test-setup.js backend/tests/__init__.py
git commit -m "chore: add Vitest and pytest test infrastructure"
```

---

### Task 1: `useOptimizeConfig` Hook

**Files:**
- Create: `src/hooks/useOptimizeConfig.js`
- Create: `src/hooks/__tests__/useOptimizeConfig.test.js`

- [ ] **Step 1: Write failing tests**

Create `src/hooks/__tests__/useOptimizeConfig.test.js`:
```js
import { renderHook, act } from '@testing-library/react'
import { useOptimizeConfig, DEFAULT_CONFIG } from '../useOptimizeConfig'

test('initializes with default config', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  expect(result.current.config.maxSites).toBe(3)
  expect(result.current.config.weights).toEqual([0.30, 0.35, 0.35])
  expect(result.current.config.minComposite).toBe(0.70)
})

test('updateConfig merges partial updates without touching other fields', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  act(() => result.current.updateConfig({ maxSites: 5 }))
  expect(result.current.config.maxSites).toBe(5)
  expect(result.current.config.weights).toEqual([0.30, 0.35, 0.35])
})

test('resetConfig restores all defaults', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  act(() => result.current.updateConfig({ maxSites: 9, minComposite: 0.90 }))
  act(() => result.current.resetConfig())
  expect(result.current.config).toEqual(DEFAULT_CONFIG)
})

test('collide:set-config event merges config', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  act(() => {
    window.dispatchEvent(new CustomEvent('collide:set-config', { detail: { maxSites: 7 } }))
  })
  expect(result.current.config.maxSites).toBe(7)
})

test('collide:set-config fires collide:run-optimize', () => {
  renderHook(() => useOptimizeConfig())
  const spy = vi.fn()
  window.addEventListener('collide:run-optimize', spy)
  act(() => {
    window.dispatchEvent(new CustomEvent('collide:set-config', { detail: { maxSites: 2 } }))
  })
  expect(spy).toHaveBeenCalledTimes(1)
  window.removeEventListener('collide:run-optimize', spy)
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- useOptimizeConfig
```

Expected: FAIL — `Cannot find module '../useOptimizeConfig'`

- [ ] **Step 3: Implement the hook**

Create `src/hooks/useOptimizeConfig.js`:
```js
import { useState, useEffect, useCallback } from 'react'

export const DEFAULT_CONFIG = {
  maxSites: 3,
  gasPriceMax: null,
  powerCostMax: null,
  acresMin: 0,
  weights: [0.30, 0.35, 0.35],
  marketFilter: [],
  minComposite: 0.70,
}

export function useOptimizeConfig() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)

  const updateConfig = useCallback((partial) => {
    setConfig(prev => ({ ...prev, ...partial }))
  }, [])

  const resetConfig = useCallback(() => setConfig(DEFAULT_CONFIG), [])

  useEffect(() => {
    const handler = e => {
      setConfig(prev => ({ ...prev, ...e.detail }))
      window.dispatchEvent(new CustomEvent('collide:run-optimize'))
    }
    window.addEventListener('collide:set-config', handler)
    return () => window.removeEventListener('collide:set-config', handler)
  }, [])

  return { config, updateConfig, resetConfig }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- useOptimizeConfig
```

Expected: 5 passing.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useOptimizeConfig.js src/hooks/__tests__/useOptimizeConfig.test.js
git commit -m "feat: add useOptimizeConfig hook"
```

---

### Task 2: `useMapContext` Hook

**Files:**
- Create: `src/hooks/useMapContext.js`
- Create: `src/hooks/__tests__/useMapContext.test.js`

- [ ] **Step 1: Write failing tests**

Create `src/hooks/__tests__/useMapContext.test.js`:
```js
import { renderHook, act } from '@testing-library/react'
import { useMapContext } from '../useMapContext'

test('starts with empty chips', () => {
  const { result } = renderHook(() => useMapContext())
  expect(result.current.chips).toEqual([])
})

test('addChip adds a coord chip', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'coord', payload: { lat: 32.1, lon: -102.5 } }))
  expect(result.current.chips).toHaveLength(1)
  expect(result.current.chips[0].type).toBe('coord')
})

test('addChip replaces existing region chip', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'region', payload: { label: 'A' } }))
  act(() => result.current.addChip({ type: 'region', payload: { label: 'B' } }))
  const regions = result.current.chips.filter(c => c.type === 'region')
  expect(regions).toHaveLength(1)
  expect(regions[0].payload.label).toBe('B')
})

test('site/coord chips capped at 3, oldest dropped', () => {
  const { result } = renderHook(() => useMapContext())
  for (let i = 0; i < 4; i++) {
    act(() => result.current.addChip({ type: 'coord', payload: { lat: i, lon: i } }))
  }
  const nonRegion = result.current.chips.filter(c => c.type !== 'region')
  expect(nonRegion).toHaveLength(3)
  expect(nonRegion.every(c => c.payload.lat !== 0)).toBe(true)
})

test('removeChip removes by index', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'coord', payload: { lat: 1, lon: 1 } }))
  act(() => result.current.addChip({ type: 'site', payload: { name: 'A' } }))
  act(() => result.current.removeChip(0))
  expect(result.current.chips).toHaveLength(1)
})

test('clearChips empties the array', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'coord', payload: { lat: 1, lon: 1 } }))
  act(() => result.current.clearChips())
  expect(result.current.chips).toEqual([])
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- useMapContext
```

Expected: FAIL — `Cannot find module '../useMapContext'`

- [ ] **Step 3: Implement the hook**

Create `src/hooks/useMapContext.js`:
```js
import { useState, useCallback } from 'react'

const MAX_SITE_CHIPS = 3

export function useMapContext() {
  const [chips, setChips] = useState([])

  const addChip = useCallback((chip) => {
    setChips(prev => {
      if (chip.type === 'region') {
        return [chip, ...prev.filter(c => c.type !== 'region')]
      }
      const regions = prev.filter(c => c.type === 'region')
      const others = prev.filter(c => c.type !== 'region')
      return [...regions, chip, ...others].filter(c => c.type === 'region' || true)
        .reduce((acc, c) => {
          if (c.type === 'region') return [...acc, c]
          const nonRegionCount = acc.filter(x => x.type !== 'region').length
          if (nonRegionCount >= MAX_SITE_CHIPS) return acc
          return [...acc, c]
        }, [])
    })
  }, [])

  const removeChip = useCallback((index) => {
    setChips(prev => prev.filter((_, i) => i !== index))
  }, [])

  const clearChips = useCallback(() => setChips([]), [])

  return { chips, addChip, removeChip, clearChips }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- useMapContext
```

Expected: 6 passing. If the `capped at 3` test fails, the addChip reducer logic needs adjustment. The key invariant: after adding, non-region chips are capped at `MAX_SITE_CHIPS` with oldest (rightmost) dropped. Rewrite addChip if needed:

```js
const addChip = useCallback((chip) => {
  setChips(prev => {
    const regions = prev.filter(c => c.type === 'region')
    const others = prev.filter(c => c.type !== 'region')
    if (chip.type === 'region') {
      return [chip, ...others]
    }
    const newOthers = [chip, ...others].slice(0, MAX_SITE_CHIPS)
    return [...regions, ...newOthers]
  })
}, [])
```

Re-run until all 6 pass.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useMapContext.js src/hooks/__tests__/useMapContext.test.js
git commit -m "feat: add useMapContext hook for agent context chips"
```

---

### Task 3: Extend `useOptimize` to Accept Config

**Files:**
- Modify: `src/hooks/useOptimize.js`

- [ ] **Step 1: Read current file**

Read `src/hooks/useOptimize.js` to confirm current signature: `optimize(bounds, weights)`.

- [ ] **Step 2: Update the hook**

Replace `src/hooks/useOptimize.js`:
```js
import { useState, useCallback } from 'react'

export function useOptimize() {
  const [progress, setProgress] = useState([])
  const [optimal, setOptimal] = useState(null)
  const [status, setStatus] = useState('idle')

  const optimize = useCallback((bounds, config = {}) => {
    const {
      weights = [0.30, 0.35, 0.35],
      maxSites = 3,
      gasPriceMax = null,
      powerCostMax = null,
      acresMin = 0,
      marketFilter = [],
      minComposite = 0.0,
    } = config

    setProgress([]); setOptimal(null); setStatus('running')
    fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bounds,
        weights,
        max_sites: maxSites,
        gas_price_max: gasPriceMax,
        power_cost_max: powerCostMax,
        acres_min: acresMin,
        market_filter: marketFilter,
        min_composite: minComposite,
      }),
    }).then(res => {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = '', event = null
      const read = () => reader.read().then(({ done, value }) => {
        if (done) { setStatus('done'); return }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          if (line.startsWith('data: ') && event) {
            const d = JSON.parse(line.slice(6).trim())
            if (event === 'progress') setProgress(p => [...p, d])
            if (event === 'optimal')  setOptimal(d)
            event = null
          }
        }
        read()
      })
      read()
    }).catch(() => setStatus('error'))
  }, [])

  const reset = useCallback(() => {
    setProgress([]); setOptimal(null); setStatus('idle')
  }, [])

  return { progress, optimal, status, optimize, reset }
}
```

- [ ] **Step 3: Verify no regressions**

```bash
npm test
```

Expected: all existing tests pass (none touch useOptimize yet, so just check nothing broke).

- [ ] **Step 4: Commit**

```bash
git add src/hooks/useOptimize.js
git commit -m "feat: extend useOptimize to forward config fields to API"
```

---

### Task 4: Backend — Extend OptimizeRequest + Filter Logic

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_optimize_filters.py`

- [ ] **Step 1: Write failing backend test**

Create `backend/tests/test_optimize_filters.py`:
```python
import pytest
from backend.main import OptimizeRequest


def test_optimize_request_accepts_all_filter_fields():
    req = OptimizeRequest(
        bounds={"sw": {"lat": 31.5, "lon": -103.0}, "ne": {"lat": 33.0, "lon": -101.0}},
        max_sites=2,
        min_composite=0.75,
        gas_price_max=3.0,
        power_cost_max=70.0,
        acres_min=500,
        market_filter=["ERCOT"],
    )
    assert req.max_sites == 2
    assert req.min_composite == 0.75
    assert req.gas_price_max == 3.0
    assert req.market_filter == ["ERCOT"]


def test_optimize_request_defaults():
    req = OptimizeRequest(
        bounds={"sw": {"lat": 31.5, "lon": -103.0}, "ne": {"lat": 33.0, "lon": -101.0}},
    )
    assert req.max_sites == 3
    assert req.min_composite == 0.0
    assert req.gas_price_max is None
    assert req.market_filter == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest backend/tests/test_optimize_filters.py -v
```

Expected: FAIL — `OptimizeRequest` missing fields.

- [ ] **Step 3: Extend OptimizeRequest in main.py**

Find the `OptimizeRequest` class (around line 125) and replace it:
```python
class OptimizeRequest(BaseModel):
    bounds: dict
    weights: tuple[float, float, float] = (0.30, 0.35, 0.35)
    grid_steps: int = 8
    max_sites: int = 3
    gas_price_max: float | None = None
    power_cost_max: float | None = None
    acres_min: int = 0
    market_filter: list[str] = []
    min_composite: float = 0.0
```

- [ ] **Step 4: Update the api_optimize endpoint to use new fields**

Find the `api_optimize` function (around line 253). Replace the `generate()` inner function body with the version that supports `max_sites` and `min_composite` filtering, and returns multiple results:

```python
@app.post("/api/optimize")
async def api_optimize(req: OptimizeRequest):
    async def generate():
        sw = req.bounds["sw"]
        ne = req.bounds["ne"]
        steps = req.grid_steps

        lat_grid = [sw["lat"] + (ne["lat"] - sw["lat"]) * i / (steps - 1) for i in range(steps)]
        lon_grid = [sw["lon"] + (ne["lon"] - sw["lon"]) * j / (steps - 1) for j in range(steps)]

        candidates = []
        total = steps * steps
        count = 0

        for lat in lat_grid:
            for lon in lon_grid:
                sc = evaluate_coordinate(lat, lon, req.weights)
                count += 1
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "lat": lat, "lon": lon,
                        "composite_score": sc.composite_score,
                        "pct": round(count / total * 100),
                    }),
                }
                if sc.hard_disqualified:
                    await asyncio.sleep(0)
                    continue
                if sc.composite_score < req.min_composite:
                    await asyncio.sleep(0)
                    continue
                candidates.append(sc)
                await asyncio.sleep(0)

        candidates.sort(key=lambda s: s.composite_score, reverse=True)
        for sc in candidates[:req.max_sites]:
            payload = {
                "lat": sc.lat, "lon": sc.lon,
                "composite_score": sc.composite_score,
                "land_score": sc.land_score,
                "gas_score": sc.gas_score,
                "power_score": sc.power_score,
            }
            yield {"event": "optimal", "data": json.dumps(payload)}

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(generate())
```

- [ ] **Step 5: Run backend tests**

```bash
.venv/Scripts/python -m pytest backend/tests/test_optimize_filters.py -v
```

Expected: 2 passing.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_optimize_filters.py
git commit -m "feat: extend OptimizeRequest with filter fields, return top N optimal sites"
```

---

### Task 5: Backend — Config Intent in Agent Graph + SSE Emission

**Files:**
- Modify: `backend/agent/graph.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_config_node.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_config_node.py`:
```python
import json
from unittest.mock import patch, MagicMock
from backend.agent.graph import config_node


def test_config_node_extracts_max_sites():
    mock_resp = MagicMock()
    mock_resp.content = json.dumps({"max_sites": 5})

    with patch('backend.agent.graph._get_llm') as mock_llm:
        mock_llm.return_value.invoke.return_value = mock_resp
        result = config_node({
            'query': 'find 5 sites',
            'context': {},
            'intent': 'config',
            'needs_web_search': False,
            'tool_results': [],
            'citations': [],
            'final_response': '',
        })

    assert result['tool_results'][0]['config_update']['max_sites'] == 5
    assert len(result['citations']) == 1


def test_config_node_handles_invalid_llm_json():
    mock_resp = MagicMock()
    mock_resp.content = "not json"

    with patch('backend.agent.graph._get_llm') as mock_llm:
        mock_llm.return_value.invoke.return_value = mock_resp
        result = config_node({
            'query': 'change something',
            'context': {},
            'intent': 'config',
            'needs_web_search': False,
            'tool_results': [],
            'citations': [],
            'final_response': '',
        })

    assert result['tool_results'][0]['config_update'] == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest backend/tests/test_config_node.py -v
```

Expected: FAIL — `cannot import name 'config_node'`

- [ ] **Step 3: Add config_node and update intent routing in graph.py**

In `backend/agent/graph.py`, make these changes:

**3a. Update `_INTENT_SYSTEM` to include `"config"` intent:**

Replace the `_INTENT_SYSTEM` string:
```python
_INTENT_SYSTEM = """Classify the user query into exactly one intent.
Reply with a JSON object with two fields:
  "intent": one of "stress_test" | "compare" | "timing" | "explanation" | "config"
  "needs_web_search": true if query uses forward-looking language or asks about current events

Examples:
- "What happens if gas prices spike 40%?" → stress_test
- "Compare sites at 31.9,-102.1 and 32.5,-101.2" → compare
- "Should I build now or wait?" → timing
- "Why is the land score low?" → explanation
- "Find 5 sites with gas under $2/MMBtu" → config
- "Set min composite to 0.8 and max sites to 2" → config
- "Only show ERCOT sites with weights 40/30/30" → config

Reply only valid JSON, no markdown."""
```

**3b. Add `_CONFIG_EXTRACT_SYSTEM` constant after `_SYNTHESIZE_SYSTEM`:**
```python
_CONFIG_EXTRACT_SYSTEM = """Extract optimization configuration changes from the user's request.
Return a JSON object with only the fields explicitly requested:
- max_sites (int): number of optimal sites to find
- gas_price_max (float): maximum gas price in $/MMBtu
- power_cost_max (float): maximum power cost in $/MWh
- acres_min (int): minimum parcel size in acres
- min_composite (float, 0-1): minimum composite score threshold
- market_filter (list[str]): markets to include, e.g. ["ERCOT"]
- weights (list of 3 floats): [land, gas, power] weights that sum to 1

Return only valid JSON. Omit fields not mentioned. No markdown."""
```

**3c. Add `config_node` function after `explanation_node`:**
```python
def config_node(state: AgentState) -> dict:
    """Extract config changes from natural language and return them as tool_results."""
    import json
    llm = _get_llm()
    resp = llm.invoke([
        SystemMessage(content=_CONFIG_EXTRACT_SYSTEM),
        HumanMessage(content=state['query']),
    ])
    try:
        config_update = json.loads(resp.content)
        if not isinstance(config_update, dict):
            config_update = {}
    except Exception:
        config_update = {}

    citation = ('Config updated: ' + ', '.join(f'{k}={v}' for k, v in config_update.items())) if config_update else 'No config changes extracted'
    return {
        'tool_results': [{'config_update': config_update}],
        'citations': [citation],
    }
```

**3d. Update `synthesize_node` to read chips and region from context:**

Replace the `user_content` assignment in `synthesize_node`:
```python
def synthesize_node(state: AgentState) -> dict:
    """Build the final Claude prompt from tool_results and return response."""
    import json
    llm = _get_llm()

    context_str = json.dumps(state.get('tool_results', []), indent=2, default=str)
    citations_str = '\n'.join(f"- {c}" for c in state.get('citations', []) if c)

    ctx = state.get('context', {})
    chips = ctx.get('chips', [])
    region = ctx.get('region', None)

    chip_str = ''
    if chips:
        chip_str = '\nActive map context:\n' + json.dumps(chips, indent=2, default=str)

    region_str = ''
    if region:
        region_str = f'\nSelected map region: {json.dumps(region, default=str)}'

    user_content = f"""User question: {state['query']}

Intent: {state.get('intent', 'explanation')}

Data gathered:
{context_str}

Sources cited:
{citations_str}{chip_str}{region_str}

Answer the user's question using the data above. Be specific and quantitative."""

    resp = llm.invoke([
        SystemMessage(content=_SYNTHESIZE_SYSTEM),
        HumanMessage(content=user_content),
    ])
    return {'final_response': resp.content if isinstance(resp.content, str) else str(resp.content)}
```

**3e. Register `config_node` in `build_agent`:**

In `build_agent()`, add:
```python
graph.add_node('config', config_node)
```

Update `add_conditional_edges`:
```python
graph.add_conditional_edges('parse_intent', route_intent, {
    'stress_test':  'stress_test',
    'compare':      'compare',
    'timing':       'timing',
    'explanation':  'explanation',
    'config':       'config',
})
```

Add edge:
```python
graph.add_edge('config', 'synthesize')
```

The `for intent_node in (...)` loop should also include `'config'` — but since we added the edge explicitly above, verify there's no duplication. The loop in the original is:
```python
for intent_node in ('stress_test', 'compare', 'timing', 'explanation'):
    graph.add_edge(intent_node, 'synthesize')
```
Keep this loop as-is; the `config` → `synthesize` edge is already added explicitly.

- [ ] **Step 4: Emit `config_update` SSE in api_agent (main.py)**

In `api_agent`'s `generate()` function, add handling for the `config` node. Find the block:
```python
elif node_name in ('stress_test', 'compare', 'timing', 'explanation'):
    for citation in node_output.get('citations', []):
        if citation:
            yield {"event": "citation", "data": citation}
```

Replace it with:
```python
elif node_name == 'config':
    for result in node_output.get('tool_results', []):
        if result.get('config_update'):
            yield {"event": "config_update", "data": json.dumps(result['config_update'])}
    for citation in node_output.get('citations', []):
        if citation:
            yield {"event": "citation", "data": citation}
elif node_name in ('stress_test', 'compare', 'timing', 'explanation'):
    for citation in node_output.get('citations', []):
        if citation:
            yield {"event": "citation", "data": citation}
```

- [ ] **Step 5: Run backend tests**

```bash
.venv/Scripts/python -m pytest backend/tests/test_config_node.py -v
```

Expected: 2 passing.

- [ ] **Step 6: Commit**

```bash
git add backend/agent/graph.py backend/main.py backend/tests/test_config_node.py
git commit -m "feat: add config intent to agent graph, emit config_update SSE"
```

---

### Task 6: Extend `useAgent` to Intercept `config_update` SSE

**Files:**
- Modify: `src/hooks/useAgent.js`

- [ ] **Step 1: Add config_update handling**

In `src/hooks/useAgent.js`, inside the SSE parsing loop, add a new `else if` branch after the `error` handler. Find:
```js
} else if (event === 'error') {
  setState(s => ({ ...s, status: 'error', error: data }))
}
```

Replace with:
```js
} else if (event === 'error') {
  setState(s => ({ ...s, status: 'error', error: data }))
} else if (event === 'config_update') {
  try {
    const payload = JSON.parse(data)
    window.dispatchEvent(new CustomEvent('collide:set-config', { detail: payload }))
  } catch (_) {}
}
```

- [ ] **Step 2: Verify no regressions**

```bash
npm test
```

Expected: all existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/hooks/useAgent.js
git commit -m "feat: useAgent intercepts config_update SSE and fires collide:set-config"
```

---

### Task 7: `MapContextMenu` Component

**Files:**
- Create: `src/components/MapContextMenu.jsx`
- Create: `src/components/__tests__/MapContextMenu.test.jsx`

- [ ] **Step 1: Write failing tests**

Create `src/components/__tests__/MapContextMenu.test.jsx`:
```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import MapContextMenu from '../MapContextMenu'

const noop = () => {}
const spaceTarget = { type: 'space', lat: 32.1, lon: -102.5 }
const siteTarget = { type: 'site', site: { lat: 32.1, lng: -102.5, name: 'Test Site' } }

test('renders nothing when open is false', () => {
  const { container } = render(
    <MapContextMenu open={false} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(container.firstChild).toBeNull()
})

test('shows space options when target type is space', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.getByText('Evaluate this location')).toBeInTheDocument()
  expect(screen.getByText('Add compare pin here')).toBeInTheDocument()
  expect(screen.getByText('Send location to agent')).toBeInTheDocument()
})

test('shows site options when target type is site', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={siteTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.getByText('Evaluate site')).toBeInTheDocument()
  expect(screen.getByText('Add to compare')).toBeInTheDocument()
  expect(screen.getByText('Send to agent')).toBeInTheDocument()
})

test('hides Set as region center when no committedBounds', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={siteTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.queryByText('Set as region center')).not.toBeInTheDocument()
})

test('shows Set as region center when committedBounds exists', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={siteTarget}
      committedBounds={{ exists: true }} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.getByText('Set as region center')).toBeInTheDocument()
})

test('calls onClose when Escape is pressed', () => {
  const onClose = vi.fn()
  render(
    <MapContextMenu open={true} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={onClose} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  fireEvent.keyDown(document, { key: 'Escape' })
  expect(onClose).toHaveBeenCalledTimes(1)
})

test('calls onEvaluate and onClose when Evaluate this location clicked', () => {
  const onEvaluate = vi.fn()
  const onClose = vi.fn()
  render(
    <MapContextMenu open={true} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={onClose} onEvaluate={onEvaluate}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  fireEvent.click(screen.getByText('Evaluate this location'))
  expect(onEvaluate).toHaveBeenCalledWith(32.1, -102.5)
  expect(onClose).toHaveBeenCalledTimes(1)
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- MapContextMenu
```

Expected: FAIL — `Cannot find module '../MapContextMenu'`

- [ ] **Step 3: Implement the component**

Create `src/components/MapContextMenu.jsx`:
```jsx
import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

export default function MapContextMenu({
  open, x, y, target, committedBounds,
  onClose, onEvaluate, onAddCompare, onSendToAgent, onSetRegionCenter,
}) {
  const menuRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const handleKey = e => { if (e.key === 'Escape') onClose() }
    const handleClick = e => {
      if (menuRef.current && !menuRef.current.contains(e.target)) onClose()
    }
    document.addEventListener('keydown', handleKey)
    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [open, onClose])

  if (!open || !target) return null

  const isSite = target.type === 'site'

  return createPortal(
    <div
      ref={menuRef}
      className="map-context-menu"
      style={{ position: 'fixed', top: y, left: x, zIndex: 9999 }}
    >
      {isSite ? (
        <>
          <button className="map-ctx-item" onClick={() => { onEvaluate(target.site.lat, target.site.lng); onClose() }}>
            Evaluate site
          </button>
          <button className="map-ctx-item" onClick={() => { onAddCompare(target.site.lat, target.site.lng); onClose() }}>
            Add to compare
          </button>
          <button className="map-ctx-item" onClick={() => { onSendToAgent({ type: 'site', payload: target.site }); onClose() }}>
            Send to agent
          </button>
          {committedBounds && (
            <button className="map-ctx-item" onClick={() => { onSetRegionCenter(target.site.lat, target.site.lng); onClose() }}>
              Set as region center
            </button>
          )}
        </>
      ) : (
        <>
          <button className="map-ctx-item" onClick={() => { onEvaluate(target.lat, target.lon); onClose() }}>
            Evaluate this location
          </button>
          <button className="map-ctx-item" onClick={() => { onAddCompare(target.lat, target.lon); onClose() }}>
            Add compare pin here
          </button>
          <button className="map-ctx-item" onClick={() => { onSendToAgent({ type: 'coord', payload: { lat: target.lat, lon: target.lon } }); onClose() }}>
            Send location to agent
          </button>
        </>
      )}
    </div>,
    document.body
  )
}
```

- [ ] **Step 4: Add CSS for the context menu in src/index.css**

Append to `src/index.css`:
```css
/* ── Map context menu ─────────────────────────────── */
.map-context-menu {
  background: #1A1612;
  border: 1px solid #2A2318;
  border-radius: 6px;
  padding: 4px 0;
  min-width: 180px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  font-family: 'IBM Plex Mono', monospace;
}
.map-ctx-item {
  display: block;
  width: 100%;
  padding: 8px 14px;
  background: none;
  border: none;
  color: #C4B8A4;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
}
.map-ctx-item:hover {
  background: #2A2318;
  color: #F4EFE4;
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npm test -- MapContextMenu
```

Expected: 7 passing.

- [ ] **Step 6: Commit**

```bash
git add src/components/MapContextMenu.jsx src/components/__tests__/MapContextMenu.test.jsx src/index.css
git commit -m "feat: add MapContextMenu portal component"
```

---

### Task 8: `MapStatusIndicator` Component

**Files:**
- Create: `src/components/MapStatusIndicator.jsx`
- Create: `src/components/__tests__/MapStatusIndicator.test.jsx`

- [ ] **Step 1: Write failing tests**

Create `src/components/__tests__/MapStatusIndicator.test.jsx`:
```jsx
import { render, screen } from '@testing-library/react'
import MapStatusIndicator from '../MapStatusIndicator'

test('renders nothing when mapBusy is false', () => {
  const { container } = render(<MapStatusIndicator mapBusy={false} label="" />)
  expect(container.firstChild).toBeNull()
})

test('shows label when mapBusy is true', () => {
  render(<MapStatusIndicator mapBusy={true} label="Optimizing…" />)
  expect(screen.getByText('Optimizing…')).toBeInTheDocument()
})

test('shows Evaluating label', () => {
  render(<MapStatusIndicator mapBusy={true} label="Evaluating…" />)
  expect(screen.getByText('Evaluating…')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify failure**

```bash
npm test -- MapStatusIndicator
```

Expected: FAIL.

- [ ] **Step 3: Implement**

Create `src/components/MapStatusIndicator.jsx`:
```jsx
export default function MapStatusIndicator({ mapBusy, label }) {
  if (!mapBusy) return null
  return (
    <div className="map-status-indicator">
      <span className="pulse pulse--green" />
      {label}
    </div>
  )
}
```

Append to `src/index.css`:
```css
/* ── Map status indicator ─────────────────────────── */
.map-status-indicator {
  position: absolute;
  bottom: 28px;
  left: 10px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(26,22,18,0.92);
  border: 1px solid #2A2318;
  border-radius: 20px;
  padding: 5px 12px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #22C55E;
  pointer-events: none;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- MapStatusIndicator
```

Expected: 3 passing.

- [ ] **Step 5: Commit**

```bash
git add src/components/MapStatusIndicator.jsx src/components/__tests__/MapStatusIndicator.test.jsx src/index.css
git commit -m "feat: add MapStatusIndicator in-map busy pill"
```

---

### Task 9: `OptimizeConfigDialog` Component

**Files:**
- Create: `src/components/OptimizeConfigDialog.jsx`
- Create: `src/components/__tests__/OptimizeConfigDialog.test.jsx`

- [ ] **Step 1: Write failing tests**

Create `src/components/__tests__/OptimizeConfigDialog.test.jsx`:
```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import OptimizeConfigDialog from '../OptimizeConfigDialog'
import { DEFAULT_CONFIG } from '../../hooks/useOptimizeConfig'

test('renders nothing when open is false', () => {
  render(<OptimizeConfigDialog open={false} config={DEFAULT_CONFIG} onApply={() => {}} onReset={() => {}} onClose={() => {}} />)
  expect(screen.queryByText('Optimization Config')).not.toBeInTheDocument()
})

test('renders dialog when open is true', () => {
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={() => {}} onReset={() => {}} onClose={() => {}} />)
  expect(screen.getByText('Optimization Config')).toBeInTheDocument()
})

test('calls onApply when Apply clicked', () => {
  const onApply = vi.fn()
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={onApply} onReset={() => {}} onClose={() => {}} />)
  fireEvent.click(screen.getByText('Apply'))
  expect(onApply).toHaveBeenCalledTimes(1)
})

test('calls onReset when Reset clicked', () => {
  const onReset = vi.fn()
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={() => {}} onReset={onReset} onClose={() => {}} />)
  fireEvent.click(screen.getByText('Reset'))
  expect(onReset).toHaveBeenCalledTimes(1)
})

test('calls onClose when × button clicked', () => {
  const onClose = vi.fn()
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={() => {}} onReset={() => {}} onClose={onClose} />)
  fireEvent.click(screen.getByText('✕'))
  expect(onClose).toHaveBeenCalledTimes(1)
})
```

- [ ] **Step 2: Run to verify failure**

```bash
npm test -- OptimizeConfigDialog
```

Expected: FAIL.

- [ ] **Step 3: Implement**

Create `src/components/OptimizeConfigDialog.jsx`:
```jsx
import { useState, useEffect } from 'react'
import { DEFAULT_CONFIG } from '../hooks/useOptimizeConfig'

function adjustWeights(weights, changedIdx, newVal) {
  const clamped = Math.max(0.05, Math.min(0.90, newVal))
  const others = weights.filter((_, i) => i !== changedIdx)
  const othersSum = others.reduce((a, b) => a + b, 0)
  const remaining = +(1 - clamped).toFixed(2)
  const result = weights.map((w, i) => {
    if (i === changedIdx) return clamped
    if (othersSum === 0) return +(remaining / 2).toFixed(2)
    return +(w / othersSum * remaining).toFixed(2)
  })
  const sum = result.reduce((a, b) => a + b, 0)
  const diff = +(1 - sum).toFixed(2)
  if (diff !== 0) {
    const adjustIdx = result.findIndex((_, i) => i !== changedIdx)
    result[adjustIdx] = +(result[adjustIdx] + diff).toFixed(2)
  }
  return result
}

const MARKETS = ['ERCOT', 'CAISO', 'SPP']
const WEIGHT_LABELS = ['Land', 'Gas', 'Power']

export default function OptimizeConfigDialog({ open, config, onApply, onReset, onClose }) {
  const [local, setLocal] = useState(config)

  useEffect(() => { setLocal(config) }, [config])

  if (!open) return null

  const handleWeightChange = (idx, val) => {
    setLocal(prev => ({ ...prev, weights: adjustWeights(prev.weights, idx, parseFloat(val)) }))
  }

  const toggleMarket = (market) => {
    setLocal(prev => {
      const next = prev.marketFilter.includes(market)
        ? prev.marketFilter.filter(m => m !== market)
        : [...prev.marketFilter, market]
      return { ...prev, marketFilter: next }
    })
  }

  return (
    <div className="config-dialog-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="config-dialog">
        <div className="config-dialog-header">
          <span className="config-dialog-title">Optimization Config</span>
          <button className="config-dialog-close" onClick={onClose}>✕</button>
        </div>
        <div className="config-dialog-body">
          <label className="config-label">Max sites to find
            <input type="number" min={1} max={10} className="config-input"
              value={local.maxSites}
              onChange={e => setLocal(prev => ({ ...prev, maxSites: Math.max(1, Math.min(10, parseInt(e.target.value) || 1)) }))} />
          </label>
          <label className="config-label">Min composite score ({Math.round(local.minComposite * 100)}%)
            <input type="range" min={0.50} max={0.95} step={0.01} className="config-slider"
              value={local.minComposite}
              onChange={e => setLocal(prev => ({ ...prev, minComposite: parseFloat(e.target.value) }))} />
          </label>
          <label className="config-label">Gas price max ($/MMBtu)
            <input type="number" min={0} step={0.1} placeholder="No limit" className="config-input"
              value={local.gasPriceMax ?? ''}
              onChange={e => setLocal(prev => ({ ...prev, gasPriceMax: e.target.value === '' ? null : parseFloat(e.target.value) }))} />
          </label>
          <label className="config-label">Power cost max ($/MWh)
            <input type="number" min={0} step={1} placeholder="No limit" className="config-input"
              value={local.powerCostMax ?? ''}
              onChange={e => setLocal(prev => ({ ...prev, powerCostMax: e.target.value === '' ? null : parseFloat(e.target.value) }))} />
          </label>
          <label className="config-label">Min parcel size (acres)
            <input type="number" min={0} step={100} className="config-input"
              value={local.acresMin}
              onChange={e => setLocal(prev => ({ ...prev, acresMin: parseInt(e.target.value) || 0 }))} />
          </label>
          <div className="config-label">Market filter
            <div className="config-market-row">
              {MARKETS.map(m => (
                <label key={m} className="config-market-check">
                  <input type="checkbox" checked={local.marketFilter.length === 0 || local.marketFilter.includes(m)}
                    onChange={() => toggleMarket(m)} />
                  {m}
                </label>
              ))}
            </div>
          </div>
          <div className="config-label">Score weights (must sum to 1)
            {WEIGHT_LABELS.map((label, i) => (
              <label key={label} className="config-weight-row">
                <span className="config-weight-label">{label} ({(local.weights[i] * 100).toFixed(0)}%)</span>
                <input type="range" min={0.05} max={0.90} step={0.01} className="config-slider"
                  value={local.weights[i]}
                  onChange={e => handleWeightChange(i, e.target.value)} />
              </label>
            ))}
          </div>
        </div>
        <div className="config-dialog-footer">
          <button className="config-btn config-btn--ghost" onClick={() => { onReset(); setLocal(DEFAULT_CONFIG) }}>Reset</button>
          <button className="config-btn config-btn--primary" onClick={() => { onApply(local); onClose() }}>Apply</button>
        </div>
      </div>
    </div>
  )
}
```

Append to `src/index.css`:
```css
/* ── Config dialog ────────────────────────────────── */
.config-dialog-overlay {
  position: fixed; inset: 0; z-index: 10000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
}
.config-dialog {
  background: #1A1612; border: 1px solid #2A2318; border-radius: 10px;
  width: 380px; max-height: 80vh; overflow-y: auto;
  font-family: 'IBM Plex Mono', monospace;
}
.config-dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px 12px; border-bottom: 1px solid #2A2318;
}
.config-dialog-title { color: #F4EFE4; font-size: 13px; font-weight: 600; }
.config-dialog-close { background: none; border: none; color: #7A6E5E; cursor: pointer; font-size: 14px; }
.config-dialog-close:hover { color: #F4EFE4; }
.config-dialog-body { padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; }
.config-label { color: #A09688; font-size: 11px; display: flex; flex-direction: column; gap: 6px; }
.config-input {
  background: #0C0B09; border: 1px solid #2A2318; border-radius: 4px;
  color: #F4EFE4; font-family: inherit; font-size: 12px; padding: 6px 8px;
}
.config-slider { accent-color: #22C55E; cursor: pointer; }
.config-market-row { display: flex; gap: 12px; flex-wrap: wrap; }
.config-market-check { display: flex; align-items: center; gap: 4px; color: #C4B8A4; cursor: pointer; }
.config-weight-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.config-weight-label { min-width: 88px; color: #C4B8A4; }
.config-dialog-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 20px 16px; border-top: 1px solid #2A2318;
}
.config-btn { padding: 7px 16px; border-radius: 5px; border: none; font-family: inherit; font-size: 12px; cursor: pointer; }
.config-btn--ghost { background: transparent; border: 1px solid #2A2318; color: #A09688; }
.config-btn--ghost:hover { border-color: #7A6E5E; color: #F4EFE4; }
.config-btn--primary { background: #22C55E; color: #0C0B09; font-weight: 600; }
.config-btn--primary:hover { background: #16A34A; }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- OptimizeConfigDialog
```

Expected: 5 passing.

- [ ] **Step 5: Commit**

```bash
git add src/components/OptimizeConfigDialog.jsx src/components/__tests__/OptimizeConfigDialog.test.jsx src/index.css
git commit -m "feat: add OptimizeConfigDialog modal"
```

---

### Task 10: `ContextChipBar` Component

**Files:**
- Create: `src/components/ContextChipBar.jsx`
- Create: `src/components/__tests__/ContextChipBar.test.jsx`

- [ ] **Step 1: Write failing tests**

Create `src/components/__tests__/ContextChipBar.test.jsx`:
```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import ContextChipBar from '../ContextChipBar'

test('renders nothing when chips is empty', () => {
  const { container } = render(<ContextChipBar chips={[]} onRemove={() => {}} />)
  expect(container.firstChild).toBeNull()
})

test('renders one dismiss button per chip', () => {
  const chips = [
    { type: 'region', payload: {} },
    { type: 'coord', payload: { lat: 32, lon: -102 } },
  ]
  render(<ContextChipBar chips={chips} onRemove={() => {}} />)
  expect(screen.getAllByRole('button')).toHaveLength(2)
})

test('calls onRemove with the correct index when × is clicked', () => {
  const onRemove = vi.fn()
  const chips = [
    { type: 'coord', payload: { lat: 1, lon: 1 } },
    { type: 'site', payload: { name: 'A' } },
  ]
  render(<ContextChipBar chips={chips} onRemove={onRemove} />)
  fireEvent.click(screen.getAllByRole('button')[1])
  expect(onRemove).toHaveBeenCalledWith(1)
})

test('displays region label for region chip', () => {
  const chips = [{ type: 'region', payload: {} }]
  render(<ContextChipBar chips={chips} onRemove={() => {}} />)
  expect(screen.getByText(/region/i)).toBeInTheDocument()
})

test('displays coord label for coord chip', () => {
  const chips = [{ type: 'coord', payload: { lat: 32.1, lon: -102.5 } }]
  render(<ContextChipBar chips={chips} onRemove={() => {}} />)
  expect(screen.getByText(/32\.1/)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify failure**

```bash
npm test -- ContextChipBar
```

Expected: FAIL.

- [ ] **Step 3: Implement**

Create `src/components/ContextChipBar.jsx`:
```jsx
function chipLabel(chip) {
  if (chip.type === 'region') return 'Selected region'
  if (chip.type === 'site') return chip.payload?.name || 'Site'
  if (chip.type === 'coord') {
    const { lat, lon } = chip.payload
    return `${lat?.toFixed(3)}, ${lon?.toFixed(3)}`
  }
  return chip.type
}

function chipClass(type) {
  if (type === 'region') return 'citation-chip citation-chip--green'
  if (type === 'site')   return 'citation-chip citation-chip--orange'
  return 'citation-chip citation-chip--blue'
}

export default function ContextChipBar({ chips, onRemove }) {
  if (!chips || chips.length === 0) return null
  return (
    <div className="context-chip-bar">
      {chips.map((chip, i) => (
        <span key={i} className={chipClass(chip.type)}>
          {chipLabel(chip)}
          <button
            className="chip-dismiss"
            onClick={() => onRemove(i)}
            aria-label={`Remove ${chipLabel(chip)}`}
          >×</button>
        </span>
      ))}
    </div>
  )
}
```

Append to `src/index.css`:
```css
/* ── Context chip bar ─────────────────────────────── */
.context-chip-bar {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 6px 12px 0;
}
.chip-dismiss {
  background: none; border: none; color: inherit;
  cursor: pointer; margin-left: 4px; padding: 0;
  font-size: 12px; opacity: 0.7; line-height: 1;
}
.chip-dismiss:hover { opacity: 1; }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- ContextChipBar
```

Expected: 5 passing.

- [ ] **Step 5: Commit**

```bash
git add src/components/ContextChipBar.jsx src/components/__tests__/ContextChipBar.test.jsx src/index.css
git commit -m "feat: add ContextChipBar dismissible chip row"
```

---

### Task 11: Modify `SiteMap.jsx`

**Files:**
- Modify: `src/components/SiteMap.jsx`

Changes: remove `MapClickHandler`, add `MapContextHandler` (right-click on map), add `eventHandlers.contextmenu` to `CircleMarker`, add `MapContextMenu`, add `MapStatusIndicator`, add Config button, listen for `collide:run-optimize`.

- [ ] **Step 1: Read the file**

Read `src/components/SiteMap.jsx` to confirm current state.

- [ ] **Step 2: Replace SiteMap.jsx with the updated version**

```jsx
import { useRef, useState, useEffect, useCallback, useMemo } from 'react'
import {
  MapContainer, TileLayer, CircleMarker, Popup, Rectangle, useMap,
} from 'react-leaflet'
import L from 'leaflet'
import { useSites } from '../hooks/useApi'
import { useHeatmap } from '../hooks/useHeatmap'
import MapContextMenu from './MapContextMenu'
import MapStatusIndicator from './MapStatusIndicator'
import OptimizeConfigDialog from './OptimizeConfigDialog'

function scoreToColor(v) {
  if (v >= 0.82) return '#3A8A65'
  if (v >= 0.76) return '#E85D04'
  return '#0D9488'
}

function scoreToLabel(v) {
  if (v >= 0.82) return 'HIGH'
  if (v >= 0.76) return 'MED'
  return 'LOWER'
}

function FitBounds({ sites }) {
  const map = useMap()
  const didFit = useRef(false)
  useEffect(() => {
    if (sites.length > 0 && !didFit.current) {
      map.fitBounds(sites.map(s => [s.lat, s.lng]), { padding: [60, 60] })
      didFit.current = true
    }
  }, [map, sites])
  return null
}

const MIN_RECT_DEG = 0.06

function AreaSelectInteraction({ active, onRubberChange, onCommit }) {
  const map = useMap()
  useEffect(() => {
    if (!active) { onRubberChange(null); return }
    const el = map.getContainer()
    el.style.cursor = 'crosshair'
    map.doubleClickZoom.disable()
    let start = null, drawing = false

    const down = e => { map.dragging.disable(); start = e.latlng; drawing = true; onRubberChange(L.latLngBounds(start, start)) }
    const move = e => { if (!drawing || !start) return; onRubberChange(L.latLngBounds(start, e.latlng)) }
    const up = e => {
      if (!drawing || !start) return
      drawing = false; map.dragging.enable()
      const b = L.latLngBounds(start, e.latlng); start = null; onRubberChange(null)
      const sw = b.getSouthWest(), ne = b.getNorthEast()
      if (Math.abs(ne.lat - sw.lat) < MIN_RECT_DEG || Math.abs(ne.lng - sw.lng) < MIN_RECT_DEG) return
      onCommit(b)
    }
    const docUp = () => { if (!drawing) return; drawing = false; start = null; map.dragging.enable(); onRubberChange(null) }

    map.on('mousedown', down); map.on('mousemove', move); map.on('mouseup', up)
    document.addEventListener('mouseup', docUp)
    return () => {
      el.style.cursor = ''; map.doubleClickZoom.enable(); map.dragging.enable()
      map.off('mousedown', down); map.off('mousemove', move); map.off('mouseup', up)
      document.removeEventListener('mouseup', docUp); onRubberChange(null)
    }
  }, [active, map, onRubberChange, onCommit])
  return null
}

function MapContextHandler({ onContextMenu }) {
  const map = useMap()
  useEffect(() => {
    const handler = e => {
      L.DomEvent.preventDefault(e)
      onContextMenu(
        e.originalEvent.clientX,
        e.originalEvent.clientY,
        { type: 'space', lat: e.latlng.lat, lon: e.latlng.lng }
      )
    }
    map.on('contextmenu', handler)
    return () => map.off('contextmenu', handler)
  }, [map, onContextMenu])
  return null
}

function sitesInBounds(sites, bounds) {
  if (!bounds) return []
  return sites.filter(s => bounds.contains(L.latLng(s.lat, s.lng)))
}

export default function SiteMap({
  comparePins = [], onCompareAdd, onCompareClear, onCompareRun, compareStatus,
  optimize, optimal, optStatus, config, updateConfig, resetConfig,
  onAddContextChip, globalBusy, mapBusyLabel,
}) {
  const { sites, dataSource, refetchSites } = useSites()
  const [selectMode, setSelectMode] = useState(false)
  const [rubberBounds, setRubberBounds] = useState(null)
  const [committedBounds, setCommittedBounds] = useState(null)
  const [configOpen, setConfigOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState(null)
  const { features, activeLayer, loading: heatLoading, loadLayer } = useHeatmap()

  const openContextMenu = useCallback((x, y, target) => {
    setContextMenu({ open: true, x, y, target })
  }, [])

  const closeContextMenu = useCallback(() => setContextMenu(null), [])

  const handleSiteContextMenu = useCallback((e, site) => {
    L.DomEvent.stop(e)
    openContextMenu(e.originalEvent.clientX, e.originalEvent.clientY, { type: 'site', site })
  }, [openContextMenu])

  const onRubberChange = useCallback(b => setRubberBounds(b), [])

  const onCommit = useCallback(bounds => {
    setCommittedBounds(bounds)
    setSelectMode(false)
    refetchSites()
    if (onAddContextChip) {
      const sw = bounds.getSouthWest(), ne = bounds.getNorthEast()
      onAddContextChip({ type: 'region', payload: { sw: { lat: sw.lat, lon: sw.lng }, ne: { lat: ne.lat, lon: ne.lng } } })
    }
  }, [refetchSites, onAddContextChip])

  useEffect(() => {
    if (!selectMode) return
    const onKey = e => { if (e.key === 'Escape') { setSelectMode(false); setRubberBounds(null) } }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selectMode])

  useEffect(() => {
    const handler = () => {
      if (!committedBounds || !optimize || !config) return
      const sw = committedBounds.getSouthWest(), ne = committedBounds.getNorthEast()
      optimize({ sw: { lat: sw.lat, lon: sw.lng }, ne: { lat: ne.lat, lon: ne.lng } }, config)
    }
    window.addEventListener('collide:run-optimize', handler)
    return () => window.removeEventListener('collide:run-optimize', handler)
  }, [committedBounds, optimize, config])

  const selectedSites = useMemo(() => sitesInBounds(sites, committedBounds), [sites, committedBounds])

  const clearSelection = () => { setCommittedBounds(null); setRubberBounds(null); setSelectMode(false) }

  const handleSetRegionCenter = useCallback((lat, lng) => {
    if (!committedBounds) return
    const sw = committedBounds.getSouthWest(), ne = committedBounds.getNorthEast()
    const halfLat = (ne.lat - sw.lat) / 2, halfLng = (ne.lng - sw.lng) / 2
    setCommittedBounds(L.latLngBounds([lat - halfLat, lng - halfLng], [lat + halfLat, lng + halfLng]))
  }, [committedBounds])

  const handleEvaluate = useCallback((lat, lon) => {
    window.dispatchEvent(new CustomEvent('collide:evaluate', { detail: { lat, lon } }))
  }, [])

  return (
    <section id="sitemap" style={{ padding: 0 }}>
      <div className="sitemap-header">
        <div className="sitemap-header-inner">
          <span className="section-eyebrow section-eyebrow--green">Site Map</span>
          <h2 className="section-title section-title--light" style={{ fontSize: 'clamp(28px,3vw,42px)', marginTop: 8 }}>
            {sites.length} Candidate Sites · TX · NM · AZ
          </h2>
          <p className="sitemap-sub">
            Right-click markers or map for options. Draw a rectangle to analyze an area.&nbsp;
            <span style={{ color: dataSource === 'live' ? '#22C55E' : '#7A6E5E' }}>
              {dataSource === 'live' ? '● Live scores' : '○ Cached scores'}
            </span>
          </p>
          <div className="sitemap-toolbar">
            <button type="button" className={`sitemap-tool-btn${selectMode ? ' sitemap-tool-btn--active' : ''}`}
              onClick={() => setSelectMode(v => !v)}>
              {selectMode ? 'Cancel selection' : 'Select area'}
            </button>
            {committedBounds && (
              <button type="button" className="sitemap-tool-btn sitemap-tool-btn--ghost" onClick={clearSelection}>
                Clear area
              </button>
            )}
            <button
              type="button"
              className={`sitemap-tool-btn${optStatus === 'running' ? ' sitemap-tool-btn--active' : ''}`}
              disabled={globalBusy}
              onClick={() => {
                if (!committedBounds) return alert('Draw a region first')
                const sw = committedBounds.getSouthWest(), ne = committedBounds.getNorthEast()
                optimize({ sw: { lat: sw.lat, lon: sw.lng }, ne: { lat: ne.lat, lon: ne.lng } }, config)
              }}
            >
              {optStatus === 'running' ? 'Searching…' : 'Find Best Site'}
            </button>
            <button type="button" className="sitemap-tool-btn sitemap-tool-btn--ghost"
              onClick={() => setConfigOpen(true)}>
              Config
            </button>
          </div>
          {selectMode && (
            <p className="sitemap-select-hint">Click and drag on the map to draw a region. Press Esc to cancel.</p>
          )}
        </div>
        <div className="sitemap-legend">
          <div className="sitemap-legend-item"><span className="sitemap-dot" style={{ background: '#3A8A65' }} /> Score ≥ 82 — High</div>
          <div className="sitemap-legend-item"><span className="sitemap-dot" style={{ background: '#E85D04' }} /> Score 76–81 — Medium</div>
          <div className="sitemap-legend-item"><span className="sitemap-dot" style={{ background: '#0D9488' }} /> Score &lt; 76 — Lower</div>
        </div>
      </div>

      <div style={{ position: 'relative' }}>
        <MapContainer center={[32.4, -103.5]} zoom={6} style={{ height: '560px', width: '100%' }} scrollWheelZoom={false}>
          <FitBounds sites={sites} />
          <MapContextHandler onContextMenu={openContextMenu} />
          <AreaSelectInteraction active={selectMode} onRubberChange={onRubberChange} onCommit={onCommit} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          {rubberBounds && <Rectangle bounds={rubberBounds} pathOptions={{ color: '#22C55E', weight: 2, fillColor: '#22C55E', fillOpacity: 0.15 }} />}
          {committedBounds && <Rectangle bounds={committedBounds} pathOptions={{ color: '#3A8A65', weight: 2, dashArray: '8 6', fillColor: '#3A8A65', fillOpacity: 0.08 }} />}
          {optimal && (
            <CircleMarker
              center={[optimal.lat, optimal.lon]}
              radius={18}
              pathOptions={{ color: '#22C55E', fillColor: '#22C55E', fillOpacity: 0.9, weight: 3 }}
              eventHandlers={{ click: () => handleEvaluate(optimal.lat, optimal.lon) }}
            >
              <Popup>
                <b>Optimal Site</b><br />
                Score: {Math.round(optimal.composite_score * 100)}/100<br />
                ({optimal.lat.toFixed(4)}, {optimal.lon.toFixed(4)})
              </Popup>
            </CircleMarker>
          )}
          {sites.map(site => (
            <CircleMarker
              key={site.id}
              center={[site.lat, site.lng]}
              radius={10 + site.scores.composite * 10}
              pathOptions={{ color: scoreToColor(site.scores.composite), fillColor: scoreToColor(site.scores.composite), fillOpacity: 0.85, weight: 2 }}
              eventHandlers={{ contextmenu: e => handleSiteContextMenu(e, site) }}
            >
              <Popup>
                <div className="popup-inner">
                  <div className="popup-name">{site.name}</div>
                  <div className="popup-loc">{site.location} · {site.market}</div>
                  <div className="popup-score-row">
                    <span className="popup-score-badge" style={{ background: scoreToColor(site.scores.composite) }}>
                      {scoreToLabel(site.scores.composite)} &nbsp; {Math.round(site.scores.composite * 100)} / 100
                    </span>
                  </div>
                  <table className="popup-table">
                    <tbody>
                      <tr><td>Sub-A Land</td><td>{Math.round(site.scores.subA * 100)}</td></tr>
                      <tr><td>Sub-B Gas</td><td>{Math.round(site.scores.subB * 100)}</td></tr>
                      <tr><td>Sub-C Power</td><td>{Math.round(site.scores.subC * 100)}</td></tr>
                      <tr><td>Gas ({site.gasHub})</td><td>${site.gasPrice.toFixed(2)}/MMBtu</td></tr>
                      <tr><td>Est. BTM power</td><td>${Number(site.estPowerCostMwh).toFixed(2)}/MWh</td></tr>
                      {site.lmp != null && <tr><td>LMP ({site.lmpNode})</td><td>${Number(site.lmp).toFixed(2)}/MWh</td></tr>}
                      <tr><td>Parcel</td><td>{site.acres.toLocaleString()} acres</td></tr>
                      <tr><td>Land Cost</td><td>${site.landCostPerAcre}/acre</td></tr>
                      <tr><td>Total land</td><td>${site.totalLandCostM.toFixed(2)}M</td></tr>
                      <tr><td>Fiber</td><td>{site.fiberKm != null ? `${site.fiberKm} km` : '—'}</td></tr>
                      <tr><td>Pipeline</td><td>{site.pipelineKm != null ? `${site.pipelineKm} km` : '—'}</td></tr>
                    </tbody>
                  </table>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          <div className="map-layer-toggles" style={{ position: 'absolute', top: 10, right: 10, zIndex: 1000, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {['composite', 'gas', 'lmp'].map(layer => (
              <button key={layer} className={`layer-toggle-pill${activeLayer === layer ? ' layer-toggle-pill--active' : ''}`} onClick={() => loadLayer(layer)}>
                {heatLoading && activeLayer === layer ? '…' : layer}
              </button>
            ))}
          </div>

          {features.map((feat, i) => (
            <CircleMarker key={`heat-${i}`}
              center={[feat.geometry.coordinates[1], feat.geometry.coordinates[0]]}
              radius={16}
              pathOptions={{ fillColor: feat.properties.score >= 0.75 ? '#22C55E' : feat.properties.score >= 0.5 ? '#F59E0B' : '#EF4444', fillOpacity: 0.35, stroke: false }}
            />
          ))}

          {comparePins.map((pin, i) => (
            <CircleMarker key={`pin-${i}`} center={[pin.lat, pin.lon]} radius={10}
              pathOptions={{ color: '#A78BFA', fillColor: '#A78BFA', fillOpacity: 0.7 }}>
              <Popup><div style={{ fontSize: 12, fontFamily: 'monospace' }}>Pin {i + 1}: ({pin.lat.toFixed(3)}, {pin.lon.toFixed(3)})</div></Popup>
            </CircleMarker>
          ))}

          <MapStatusIndicator mapBusy={!!globalBusy} label={mapBusyLabel || 'Processing…'} />
        </MapContainer>
      </div>

      <MapContextMenu
        open={!!contextMenu?.open}
        x={contextMenu?.x ?? 0}
        y={contextMenu?.y ?? 0}
        target={contextMenu?.target ?? null}
        committedBounds={committedBounds}
        onClose={closeContextMenu}
        onEvaluate={(lat, lon) => { handleEvaluate(lat, lon); closeContextMenu() }}
        onAddCompare={(lat, lon) => { if (onCompareAdd) onCompareAdd(lat, lon); closeContextMenu() }}
        onSendToAgent={(chip) => { if (onAddContextChip) onAddContextChip(chip); closeContextMenu() }}
        onSetRegionCenter={(lat, lng) => { handleSetRegionCenter(lat, lng); closeContextMenu() }}
      />

      {comparePins.length >= 2 && (
        <div className="compare-header-bar">
          <span>{comparePins.length} sites selected</span>
          <button className="compare-run-btn" onClick={onCompareRun} disabled={compareStatus === 'loading' || globalBusy}>
            {compareStatus === 'loading' ? 'Comparing…' : 'Compare Sites →'}
          </button>
          <button className="compare-clear-btn" onClick={onCompareClear}>Clear</button>
        </div>
      )}

      {committedBounds && (
        <div className="sitemap-pricing-panel">
          <div className="sitemap-pricing-head">
            <h3 className="sitemap-pricing-title">Pricing in selected area</h3>
            <span className="sitemap-pricing-meta">{selectedSites.length} site{selectedSites.length === 1 ? '' : 's'} · {dataSource === 'live' ? 'Live API' : 'Cached fallback'}</span>
          </div>
          {selectedSites.length === 0 ? (
            <p className="sitemap-pricing-empty">No candidate sites fall inside this rectangle. Try a larger region.</p>
          ) : (
            <div className="sitemap-pricing-table-wrap">
              <table className="sitemap-pricing-table">
                <thead>
                  <tr><th>Site</th><th>Hub / node</th><th>Gas</th><th>Est. power</th><th>LMP</th><th>Land / ac</th><th>Total land</th></tr>
                </thead>
                <tbody>
                  {selectedSites.map(site => (
                    <tr key={site.id}>
                      <td><div className="sitemap-pcell-name">{site.name}</div><div className="sitemap-pcell-loc">{site.location}</div></td>
                      <td className="sitemap-pcell-mono">{site.gasHub}<br /><span className="sitemap-pcell-dim">{site.lmpNode}</span></td>
                      <td className="sitemap-pcell-mono">${site.gasPrice.toFixed(2)}/MMBtu</td>
                      <td className="sitemap-pcell-mono">${Number(site.estPowerCostMwh).toFixed(2)}/MWh</td>
                      <td className="sitemap-pcell-mono">{site.lmp != null ? `$${Number(site.lmp).toFixed(2)}` : '—'}</td>
                      <td className="sitemap-pcell-mono">${site.landCostPerAcre.toLocaleString()}</td>
                      <td className="sitemap-pcell-mono">${site.totalLandCostM.toFixed(2)}M</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <OptimizeConfigDialog
        open={configOpen}
        config={config || {}}
        onApply={cfg => { if (updateConfig) updateConfig(cfg); setConfigOpen(false) }}
        onReset={() => { if (resetConfig) resetConfig() }}
        onClose={() => setConfigOpen(false)}
      />
    </section>
  )
}
```

- [ ] **Step 3: Verify no test failures**

```bash
npm test
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/components/SiteMap.jsx
git commit -m "feat: rework SiteMap with right-click menus, config dialog, collide:run-optimize listener"
```

---

### Task 12: Modify `AgentChat.jsx` and `AIAnalystPanel.jsx`

**Files:**
- Modify: `src/components/AgentChat.jsx`
- Modify: `src/components/AIAnalystPanel.jsx`

- [ ] **Step 1: Update AgentChat.jsx**

Replace `src/components/AgentChat.jsx`:
```jsx
import { useState, useRef, useEffect } from 'react'
import { useAgent } from '../hooks/useAgent'
import MarkdownRenderer from './MarkdownRenderer'
import ContextChipBar from './ContextChipBar'

function CitationChip({ text }) {
  const isCoord = /^-?\d+\.\d+,-?\d+\.\d+/.test(text)
  const isNode = /^(HB_|PALO|SP15|NP15)/.test(text)
  const cls = isCoord ? 'citation-chip--green' : isNode ? 'citation-chip--orange' : 'citation-chip--blue'
  return <span className={`citation-chip ${cls}`}>{text}</span>
}

function Message({ role, text, citations }) {
  return (
    <div className={`chat-message chat-message--${role}`}>
      <div className="chat-bubble">
        {role === 'assistant' ? <MarkdownRenderer>{text}</MarkdownRenderer> : text}
      </div>
      {citations && citations.length > 0 && (
        <div className="chat-citations">
          {citations.map((c, i) => <CitationChip key={i} text={c} />)}
        </div>
      )}
    </div>
  )
}

export default function AgentChat({ context, chips = [], onRemoveChip }) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([])
  const { tokens, citations, status, ask, reset } = useAgent()
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [tokens, history])

  const submit = () => {
    if (!input.trim() || status === 'loading' || status === 'streaming') return
    const q = input.trim()
    setHistory(h => [...h, { role: 'user', text: q }])
    setInput('')
    reset()
    const enrichedContext = {
      ...context,
      chips: chips.map(c => ({ type: c.type, payload: c.payload })),
      region: chips.find(c => c.type === 'region')?.payload ?? null,
    }
    ask(q, enrichedContext)
  }

  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }

  useEffect(() => {
    if (status === 'done' && tokens) {
      setHistory(h => [...h, { role: 'assistant', text: tokens, citations }])
      reset()
    }
  }, [status])

  return (
    <div className="agent-chat">
      <div className="chat-messages">
        {history.map((msg, i) => (
          <Message key={i} role={msg.role} text={msg.text} citations={msg.citations} />
        ))}
        {(status === 'loading' || status === 'streaming') && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-bubble">
              {status === 'loading'
                ? <span className="chat-thinking">Thinking…</span>
                : <MarkdownRenderer streaming>{tokens}</MarkdownRenderer>}
            </div>
            {citations.length > 0 && (
              <div className="chat-citations">
                {citations.map((c, i) => <CitationChip key={i} text={c} />)}
              </div>
            )}
          </div>
        )}
        {status === 'error' && (
          <div className="chat-message chat-message--error">
            <div className="chat-bubble">Error: check ANTHROPIC_API_KEY and backend logs.</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <ContextChipBar chips={chips} onRemove={onRemoveChip || (() => {})} />

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask about sites, timing, stress scenarios, or economics…"
          rows={2}
          disabled={status === 'loading' || status === 'streaming'}
        />
        <button
          className="chat-send-btn"
          onClick={submit}
          disabled={!input.trim() || status === 'loading' || status === 'streaming'}
        >
          →
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update AIAnalystPanel.jsx**

Replace `src/components/AIAnalystPanel.jsx`:
```jsx
import BriefingCard from './BriefingCard'
import AgentChat from './AgentChat'
import { useRegime } from '../hooks/useRegime'

export default function AIAnalystPanel({ open, onClose, context, chips, onRemoveChip }) {
  const regime = useRegime()
  if (!open) return null
  return (
    <div className="ai-analyst-panel">
      <div className="ai-panel-header">
        <span className="ai-panel-title">⚡ AI Analyst</span>
        <button className="ai-panel-close" onClick={onClose}>✕</button>
      </div>
      <div className="ai-panel-body">
        <BriefingCard regime={regime} />
        <div className="ai-panel-divider" />
        <AgentChat context={context} chips={chips} onRemoveChip={onRemoveChip} />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify no test failures**

```bash
npm test
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/components/AgentChat.jsx src/components/AIAnalystPanel.jsx
git commit -m "feat: wire ContextChipBar into AgentChat, thread chips through AIAnalystPanel"
```

---

### Task 13: Update `App.jsx` — Lift State, globalBusy, Wire All Props

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: Replace App.jsx**

```jsx
import { useEffect, useState, useCallback } from 'react'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import StatsBar from './components/StatsBar'
import Dashboard from './components/Dashboard'
import SiteMap from './components/SiteMap'
import LiveTicker from './components/LiveTicker'
import Scoring from './components/Scoring'
import Workflow from './components/Workflow'
import DataSources from './components/DataSources'
import Markets from './components/Markets'
import DataQuality from './components/DataQuality'
import Testimonials from './components/Testimonials'
import CTA from './components/CTA'
import Footer from './components/Footer'
import ScorecardPanel from './components/ScorecardPanel'
import BottomStrip from './components/BottomStrip'
import AIAnalystPanel from './components/AIAnalystPanel'
import CompareMode from './components/CompareMode'
import { useEvaluate } from './hooks/useEvaluate'
import { useCompare } from './hooks/useCompare'
import { useOptimize } from './hooks/useOptimize'
import { useOptimizeConfig } from './hooks/useOptimizeConfig'
import { useMapContext } from './hooks/useMapContext'
import { useAgent } from './hooks/useAgent'

export default function App() {
  const { scorecard, narrative, status: evalStatus, error, evaluate, reset: resetEval } = useEvaluate()
  const { pins, results: compareResults, status: compareStatus, addPin, clearPins, runCompare } = useCompare()
  const { progress, optimal, status: optStatus, optimize, reset: resetOpt } = useOptimize()
  const { config, updateConfig, resetConfig } = useOptimizeConfig()
  const { chips, addChip, removeChip } = useMapContext()
  const { status: agentStatus } = useAgent()

  const [panelOpen, setPanelOpen] = useState(false)
  const [analystOpen, setAnalystOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)

  const globalBusy = optStatus === 'running'
    || compareStatus === 'loading'
    || evalStatus === 'loading'
    || agentStatus === 'loading'
    || agentStatus === 'streaming'

  const mapBusyLabel = optStatus === 'running' ? 'Optimizing…'
    : compareStatus === 'loading' ? 'Comparing…'
    : evalStatus === 'loading' ? 'Evaluating…'
    : ''

  useEffect(() => {
    const handler = e => { evaluate(e.detail.lat, e.detail.lon); setPanelOpen(true) }
    window.addEventListener('collide:evaluate', handler)
    return () => window.removeEventListener('collide:evaluate', handler)
  }, [evaluate])

  useEffect(() => {
    if (compareStatus === 'done' && compareResults.length > 0) setCompareOpen(true)
  }, [compareStatus, compareResults])

  useEffect(() => {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return
        e.target.classList.add('visible')
        const fill = e.target.querySelector('.score-fill')
        if (fill) setTimeout(() => { fill.style.width = fill.dataset.width + '%' }, 300)
      })
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' })

    const scoreCardObserver = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return
        const fill = e.target.querySelector('.score-fill')
        if (fill) setTimeout(() => { fill.style.width = fill.dataset.width + '%' }, 500)
      })
    }, { threshold: 0.3 })

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el))
    document.querySelectorAll('.score-card').forEach(el => scoreCardObserver.observe(el))

    const nav = document.querySelector('nav')
    const handleScroll = () => {
      nav.style.background = window.scrollY > 40 ? 'rgba(12,11,9,0.97)' : 'rgba(12,11,9,0.85)'
    }
    window.addEventListener('scroll', handleScroll)
    return () => {
      revealObserver.disconnect()
      scoreCardObserver.disconnect()
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  const analystContext = { scorecard: scorecard || null, pins }

  return (
    <>
      <Navbar onAnalystToggle={() => setAnalystOpen(o => !o)} analystOpen={analystOpen} />
      <Hero />
      <StatsBar />
      <Dashboard />
      <SiteMap
        comparePins={pins}
        onCompareAdd={addPin}
        onCompareClear={clearPins}
        onCompareRun={runCompare}
        compareStatus={compareStatus}
        optimize={optimize}
        optimal={optimal}
        optStatus={optStatus}
        config={config}
        updateConfig={updateConfig}
        resetConfig={resetConfig}
        onAddContextChip={addChip}
        globalBusy={globalBusy}
        mapBusyLabel={mapBusyLabel}
      />
      {compareOpen && (
        <CompareMode
          results={compareResults}
          status={compareStatus}
          onClose={() => { setCompareOpen(false); clearPins() }}
        />
      )}
      <BottomStrip />
      <LiveTicker />
      <Scoring />
      <Workflow />
      <DataSources />
      <Markets />
      <DataQuality />
      <Testimonials />
      <CTA />
      <Footer />
      {panelOpen && (
        <ScorecardPanel
          scorecard={scorecard}
          narrative={narrative}
          status={evalStatus}
          error={error}
          onClose={() => { resetEval(); setPanelOpen(false) }}
        />
      )}
      <AIAnalystPanel
        open={analystOpen}
        onClose={() => setAnalystOpen(false)}
        context={analystContext}
        chips={chips}
        onRemoveChip={removeChip}
      />
    </>
  )
}
```

- [ ] **Step 2: Note — useAgent is imported in App but also used in AgentChat**

`useAgent` is called in App ONLY to read `agentStatus` for `globalBusy`. However, `useAgent` in `AgentChat` is a separate hook instance — they do not share state. This means `agentStatus` in App will always be `'idle'` since App doesn't call `ask()`.

To fix this: move the `useAgent` call out of `AgentChat` and pass `ask`, `reset`, `tokens`, `citations`, `status` as props from `App` down through `AIAnalystPanel` to `AgentChat`. This ensures App sees the real agent status.

Update `App.jsx` — the `useAgent` import and usage is already there. Now update `AgentChat.jsx` to accept these as props instead of calling `useAgent()` internally:

Replace the top of `AgentChat.jsx`:
```jsx
export default function AgentChat({ context, chips = [], onRemoveChip, ask, reset, tokens, citations, status }) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([])
  const endRef = useRef(null)
  // ... rest unchanged, but remove: const { tokens, citations, status, ask, reset } = useAgent()
```

Update `AIAnalystPanel.jsx` to thread through these props:
```jsx
export default function AIAnalystPanel({ open, onClose, context, chips, onRemoveChip, ask, reset, tokens, citations, agentStatus }) {
  const regime = useRegime()
  if (!open) return null
  return (
    <div className="ai-analyst-panel">
      <div className="ai-panel-header">
        <span className="ai-panel-title">⚡ AI Analyst</span>
        <button className="ai-panel-close" onClick={onClose}>✕</button>
      </div>
      <div className="ai-panel-body">
        <BriefingCard regime={regime} />
        <div className="ai-panel-divider" />
        <AgentChat
          context={context} chips={chips} onRemoveChip={onRemoveChip}
          ask={ask} reset={reset} tokens={tokens} citations={citations} status={agentStatus}
        />
      </div>
    </div>
  )
}
```

Update `App.jsx` `AIAnalystPanel` usage:
```jsx
const { tokens, citations, status: agentStatus, ask, reset: resetAgent } = useAgent()
// ...
<AIAnalystPanel
  open={analystOpen}
  onClose={() => setAnalystOpen(false)}
  context={analystContext}
  chips={chips}
  onRemoveChip={removeChip}
  ask={ask}
  reset={resetAgent}
  tokens={tokens}
  citations={citations}
  agentStatus={agentStatus}
/>
```

- [ ] **Step 3: Apply the AgentChat and AIAnalystPanel prop updates**

Make the changes described in Step 2 to `src/components/AgentChat.jsx` and `src/components/AIAnalystPanel.jsx`.

- [ ] **Step 4: Run all tests**

```bash
npm test
```

Expected: all tests pass.

- [ ] **Step 5: Run the dev server and manually verify**

```bash
npm run dev
```

Check:
- Right-click on empty map space → context menu appears with 3 options
- Right-click on a site marker → context menu with 4 options (or 3 if no committed bounds)
- "Send to agent" adds a chip above the chat textarea in the AI Analyst panel
- "Config" toolbar button opens the config dialog with sliders
- Adjusting weight sliders keeps sum at 1
- "Apply" closes the dialog and the new config is stored
- Drawing a region → region chip auto-added to agent context bar
- "Find Best Site" while optimizing shows "Searching…" and MapStatusIndicator shows "Optimizing…"
- While optimizing, right-click menu actions that call network are greyed out

- [ ] **Step 6: Run backend tests**

```bash
.venv/Scripts/python -m pytest backend/tests/ -v
```

Expected: all backend tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/App.jsx src/components/AgentChat.jsx src/components/AIAnalystPanel.jsx
git commit -m "feat: wire App with lifted useOptimize/useOptimizeConfig/useMapContext, globalBusy"
```

---

## Self-Review Checklist

- [x] Right-click site marker → Evaluate site, Add to compare, Send to agent, Set as region center (hidden if no bounds)
- [x] Right-click empty space → Evaluate this location, Add compare pin here, Send location to agent
- [x] Left-click on optimal site → opens scorecard
- [x] Toolbar "Config" button → OptimizeConfigDialog modal
- [x] Config dialog: weight sliders sum to 1, Apply closes, Reset restores defaults
- [x] Agent "find 5 sites with gas < $2" → config intent → config_update SSE → `collide:set-config` → `collide:run-optimize` → SiteMap calls optimize
- [x] Region commit → region chip auto-added to agent panel
- [x] "Send to agent" right-click → site/coord chip added
- [x] Chips dismissible via × button
- [x] chips serialized into context.chips when ask() is called
- [x] synthesize_node reads context.chips and context.region
- [x] MapStatusIndicator shows in-map during optimize/compare/evaluate
- [x] globalBusy blocks duplicate requests and disables action buttons
- [x] OptimizeRequest accepts max_sites, min_composite, and other filter fields
- [x] optimize endpoint returns top max_sites results (not just one)
