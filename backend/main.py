"""COLLIDE Platform — FastAPI scoring engine."""
import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sse_starlette.sse import EventSourceResponse

from backend.config import get_settings
from backend.data.sites import CANDIDATE_SITES
from backend.ingest.eia_gas import fetch_gas_prices
from backend.ingest.caiso_lmp import fetch_all_nodes
from backend.ingest.eia_demand import fetch_all_bas
from backend.ingest.gridstatus import fetch_ercot_snapshot
from backend.scoring.engine import score_all, score_site
from backend.scoring.sub_b import GAS_HUB_PRICES
from backend.pipeline.runner import run_pipeline
from backend.pipeline.evaluate import (
    evaluate_coordinate, stream_narration,
    get_cached_regime, set_cached_regime,
)
from backend.scoring.regime import classify_regime


settings = get_settings()
scheduler = AsyncIOScheduler()
_news_cache: dict = {"items": [], "fetched_at": ""}


# ── Background jobs ────────────────────────────────────────────────────────

async def _refresh_regime():
    snapshot = await fetch_ercot_snapshot(settings.gridstatus_api_key)
    fm = snapshot['fuel_mix']
    lmp = snapshot['lmp']
    lmp_mean = sum(lmp.values()) / max(len(lmp), 1)
    regime = classify_regime(
        lmp_mean=lmp_mean, lmp_std=lmp_mean * 0.25,
        wind_pct=fm.get('wind', 0.28),
        demand_mw=55000, reserve_margin=0.18,
    )
    set_cached_regime(regime)


async def _refresh_news():
    global _news_cache
    api_key = settings.tavily_api_key
    if not api_key:
        return
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search("BTM natural gas data center energy Texas", max_results=3)
        _news_cache = {
            "items": [{"title": r["title"], "url": r["url"], "snippet": r["content"][:200]}
                      for r in results.get("results", [])],
            "fetched_at": __import__('datetime').datetime.utcnow().isoformat(),
        }
    except Exception:
        pass


app = FastAPI(title="COLLIDE Scoring API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    scheduler.add_job(_refresh_regime, 'interval', seconds=settings.regime_refresh_secs)
    scheduler.add_job(_refresh_news,   'interval', seconds=settings.news_refresh_secs)
    scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()


# ── Response models ────────────────────────────────────────────────────────

class ScoreResponse(BaseModel):
    id: str
    name: str
    location: str
    state: str
    market: str
    lat: float
    lng: float
    acres: int
    land_cost_per_acre: int
    fiber_km: float
    water_km: float
    pipeline_km: float
    gas_hub: str
    gas_price: float
    lmp_node: str
    lmp: float | None
    est_power_cost_mwh: float
    total_land_cost_m: float
    scores: dict[str, float]
    rank: int


class MarketResponse(BaseModel):
    gas: dict[str, Any]
    lmp: dict[str, Any]
    demand: dict[str, Any]


class EvaluateRequest(BaseModel):
    lat: float
    lon: float
    weights: tuple[float, float, float] = (0.30, 0.35, 0.35)


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


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_response(s, waha: float | None) -> ScoreResponse:
    gp = waha if s.site.gas_hub == "Waha" else GAS_HUB_PRICES.get(s.site.gas_hub, 3.41)
    return ScoreResponse(
        id=s.site.id,
        name=s.site.name,
        location=s.site.location,
        state=s.site.state,
        market=s.site.market,
        lat=s.site.lat,
        lng=s.site.lng,
        acres=s.site.acres,
        land_cost_per_acre=s.site.land_cost_per_acre,
        fiber_km=s.site.fiber_km,
        water_km=s.site.water_km,
        pipeline_km=s.site.pipeline_km,
        gas_hub=s.site.gas_hub,
        gas_price=gp,
        lmp_node=s.site.lmp_node,
        lmp=s.site.lmp,
        est_power_cost_mwh=s.est_power_cost_mwh,
        total_land_cost_m=round(s.site.acres * s.site.land_cost_per_acre / 1_000_000, 2),
        scores={"subA": s.sub_a, "subB": s.sub_b, "subC": s.sub_c, "composite": s.composite},
        rank=s.rank,
    )


async def _fetch_market_inputs(api_key: str) -> tuple[dict, dict]:
    gas_data, lmp_data = await asyncio.gather(
        fetch_gas_prices(api_key),
        fetch_all_nodes(),
    )
    return gas_data, lmp_data


# ── Existing endpoints (unchanged) ─────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "collide-scoring-api"}


@app.get("/api/sites", response_model=list[ScoreResponse])
async def get_sites():
    """Return all candidate sites ranked by composite score using live market inputs."""
    gas_data, lmp_data = await _fetch_market_inputs(settings.eia_api_key)
    waha     = gas_data.get("waha_hub")
    palo_lmp = lmp_data.get("PALOVRDE_ASR-APND", {}).get("lmp_mwh")

    scored = score_all(live_gas_price=waha, live_lmp=palo_lmp)
    return [_build_response(s, waha) for s in scored]


@app.get("/api/sites/{site_id}", response_model=ScoreResponse)
async def get_site(site_id: str):
    """Return scored detail for a single candidate site."""
    site = next((s for s in CANDIDATE_SITES if s.id == site_id), None)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")

    gas_data, lmp_data = await _fetch_market_inputs(settings.eia_api_key)
    waha     = gas_data.get("waha_hub")
    palo_lmp = lmp_data.get("PALOVRDE_ASR-APND", {}).get("lmp_mwh")
    s        = score_site(site, waha, palo_lmp)
    return _build_response(s, waha)


@app.get("/api/market", response_model=MarketResponse)
async def get_market():
    """Return live gas prices, LMPs, and BA demand."""
    gas, lmp, demand = await asyncio.gather(
        fetch_gas_prices(settings.eia_api_key),
        fetch_all_nodes(),
        fetch_all_bas(settings.eia_api_key),
    )
    return MarketResponse(gas=gas, lmp=lmp, demand=demand)


@app.post("/api/pipeline/run")
async def trigger_pipeline() -> dict:
    """Trigger a full ingest → validate → silver lake → score pipeline run."""
    return await run_pipeline(settings.eia_api_key)


# ── New endpoints ──────────────────────────────────────────────────────────

@app.post("/api/evaluate")
async def api_evaluate(req: EvaluateRequest):
    async def generate():
        sc = evaluate_coordinate(req.lat, req.lon, req.weights)
        payload = {
            "lat": sc.lat, "lon": sc.lon,
            "hard_disqualified": sc.hard_disqualified,
            "disqualify_reason": sc.disqualify_reason,
            "land_score": sc.land_score, "gas_score": sc.gas_score,
            "power_score": sc.power_score, "composite_score": sc.composite_score,
            "land_shap": sc.land_shap,
            "spread_p50_mwh": sc.spread_p50_mwh,
            "spread_durability": sc.spread_durability,
            "regime": sc.regime, "regime_proba": sc.regime_proba,
            "cost": {
                "land_acquisition_m": sc.cost.land_acquisition_m if sc.cost else 0,
                "pipeline_connection_m": sc.cost.pipeline_connection_m if sc.cost else 0,
                "water_connection_m": sc.cost.water_connection_m if sc.cost else 0,
                "btm_capex_m": sc.cost.btm_capex_m if sc.cost else 0,
                "npv_p10_m": sc.cost.npv_p10_m if sc.cost else 0,
                "npv_p50_m": sc.cost.npv_p50_m if sc.cost else 0,
                "npv_p90_m": sc.cost.npv_p90_m if sc.cost else 0,
            } if sc.cost else None,
        }
        yield {"event": "scorecard", "data": json.dumps(payload)}

        if not sc.hard_disqualified:
            async for chunk in stream_narration(sc, settings.anthropic_api_key):
                yield {"event": "narrative", "data": json.dumps(chunk)}

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(generate())


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


@app.get("/api/regime")
async def api_regime():
    r = get_cached_regime()
    return {"label": r.label, "proba": r.proba, "labels": r.labels}


# ── /api/forecast ──────────────────────────────────────────────────────────

class ForecastResponse(BaseModel):
    node: str
    horizon: int
    p10: list[float]
    p50: list[float]
    p90: list[float]
    btm_cost_mwh: float
    method: str


@app.get("/api/forecast", response_model=ForecastResponse)
async def api_forecast(node: str = "HB_WEST", horizon: int = 72):
    """Return Moirai P10/P50/P90 LMP forecast for a node (served from cache)."""
    from backend.scoring.power import get_forecast, HEAT_RATE, OM_COST
    fc = get_forecast(node)
    waha_price = 1.84
    btm_cost = waha_price * HEAT_RATE + OM_COST
    if fc is not None:
        h = min(horizon, len(fc['p50']))
        return ForecastResponse(
            node=node, horizon=h,
            p10=fc['p10'][:h].tolist() if hasattr(fc['p10'], 'tolist') else list(fc['p10'][:h]),
            p50=fc['p50'][:h].tolist() if hasattr(fc['p50'], 'tolist') else list(fc['p50'][:h]),
            p90=fc['p90'][:h].tolist() if hasattr(fc['p90'], 'tolist') else list(fc['p90'][:h]),
            btm_cost_mwh=round(btm_cost, 2),
            method=fc.get('method', 'cache'),
        )
    base = 42.0
    flat_p50 = [base] * horizon
    return ForecastResponse(
        node=node, horizon=horizon,
        p10=[base - 8] * horizon, p50=flat_p50, p90=[base + 8] * horizon,
        btm_cost_mwh=round(btm_cost, 2), method='fallback',
    )


# ── /api/heatmap ────────────────────────────────────────────────────────────

VALID_LAYERS = {'composite', 'gas', 'lmp'}


@app.get("/api/heatmap")
async def api_heatmap(layer: str = "composite", bounds: str = "", zoom: int = 8):
    """Return GeoJSON FeatureCollection of scored points for a map heat layer."""
    if layer not in VALID_LAYERS:
        return {"type": "FeatureCollection", "features": []}

    gas_data, lmp_data = await _fetch_market_inputs(settings.eia_api_key)
    waha     = gas_data.get("waha_hub")
    palo_lmp = lmp_data.get("PALOVRDE_ASR-APND", {}).get("lmp_mwh")
    scored   = score_all(live_gas_price=waha, live_lmp=palo_lmp)

    score_key = {
        'composite': lambda s: s.composite,
        'gas':       lambda s: s.sub_b,
        'lmp':       lambda s: min(max(s.sub_c, 0.0), 1.0),
    }[layer]

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s.site.lng, s.site.lat]},
            "properties": {
                "score": round(score_key(s), 4),
                "layer": layer,
                "name": s.site.name,
            },
        }
        for s in scored
    ]
    return {"type": "FeatureCollection", "features": features}


# ── /api/compare ────────────────────────────────────────────────────────────

@app.get("/api/compare")
async def api_compare(coords: str):
    """Evaluate N coordinates and return ranked scorecards.

    coords: semicolon-separated 'lat,lon' pairs, e.g. '31.9,-102.1;32.5,-101.2'
    """
    pairs = []
    for part in coords.split(';'):
        part = part.strip()
        if not part:
            continue
        try:
            lat_s, lon_s = part.split(',')
            pairs.append((float(lat_s.strip()), float(lon_s.strip())))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid coord pair: '{part}'")

    if not pairs:
        raise HTTPException(status_code=422, detail="No valid coordinate pairs provided")
    if len(pairs) > 5:
        raise HTTPException(status_code=422, detail="Maximum 5 coordinates per compare request")

    results = []
    for lat, lon in pairs:
        sc = evaluate_coordinate(lat, lon)
        results.append({
            "lat": sc.lat, "lon": sc.lon,
            "composite_score": sc.composite_score,
            "land_score": sc.land_score,
            "gas_score": sc.gas_score,
            "power_score": sc.power_score,
            "regime": sc.regime,
            "spread_p50_mwh": sc.spread_p50_mwh,
            "spread_durability": sc.spread_durability,
            "disqualified": sc.hard_disqualified,
            "disqualify_reason": sc.disqualify_reason,
            "cost": {
                "npv_p10_m": sc.cost.npv_p10_m if sc.cost else 0,
                "npv_p50_m": sc.cost.npv_p50_m if sc.cost else 0,
                "npv_p90_m": sc.cost.npv_p90_m if sc.cost else 0,
                "btm_capex_m": sc.cost.btm_capex_m if sc.cost else 0,
                "land_acquisition_m": sc.cost.land_acquisition_m if sc.cost else 0,
                "pipeline_connection_m": sc.cost.pipeline_connection_m if sc.cost else 0,
                "water_connection_m": sc.cost.water_connection_m if sc.cost else 0,
            } if sc.cost else None,
        })

    results.sort(key=lambda x: x['composite_score'], reverse=True)
    return results


@app.get("/api/news")
async def api_news():
    return _news_cache


class AgentRequest(BaseModel):
    query: str
    context: dict = {}   # {scorecard?, bounds?, regime?} from frontend


@app.post("/api/agent")
async def api_agent(req: AgentRequest):
    async def generate():
        from backend.agent.graph import get_agent
        agent = get_agent()
        initial_state = {
            'query': req.query,
            'context': req.context,
            'intent': '',
            'needs_web_search': False,
            'tool_results': [],
            'citations': [],
            'final_response': '',
        }
        try:
            async for event in agent.astream(initial_state):
                for node_name, node_output in event.items():
                    if node_name == 'synthesize' and node_output.get('final_response'):
                        response_text = node_output['final_response']
                        chunk_size = 4
                        for i in range(0, len(response_text), chunk_size):
                            yield {"event": "token", "data": json.dumps(response_text[i:i+chunk_size])}
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
            yield {"event": "done", "data": "{}"}
        except Exception as e:
            yield {"event": "error", "data": str(e)[:200]}
    return EventSourceResponse(generate())


@app.websocket("/api/lmp/stream")
async def ws_lmp(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            snapshot = await fetch_ercot_snapshot(settings.gridstatus_api_key)
            await websocket.send_json(snapshot['lmp'])
            await asyncio.sleep(300)  # 5-min cadence
    except (WebSocketDisconnect, Exception):
        pass
