"""Tools available to the COLLIDE LangGraph agent."""
from langchain_core.tools import tool
from backend.pipeline.evaluate import evaluate_coordinate
from backend.scoring.cost import estimate_costs


# ── Internal accessors (not tools — used by tools below) ───────────────────

def _get_news_cache() -> dict:
    """Access the news cache from main.py without circular import."""
    try:
        from backend.main import _news_cache
        return _news_cache
    except Exception:
        return {"items": [], "fetched_at": ""}


def _get_tavily_key() -> str | None:
    try:
        from backend.config import get_settings
        return get_settings().tavily_api_key or None
    except Exception:
        return None


# ── Tools ──────────────────────────────────────────────────────────────────

@tool
def evaluate_site(lat: float, lon: float) -> dict:
    """Evaluate a (lat, lon) coordinate and return its full scorecard."""
    sc = evaluate_coordinate(lat, lon)
    return {
        'lat': sc.lat, 'lon': sc.lon,
        'composite': sc.composite_score,
        'land': sc.land_score, 'gas': sc.gas_score, 'power': sc.power_score,
        'npv_p50': sc.cost.npv_p50_m if sc.cost else 0,
        'spread_p50_mwh': sc.spread_p50_mwh,
        'spread_durability': sc.spread_durability,
        'regime': sc.regime,
        'disqualified': sc.hard_disqualified,
        'reason': sc.disqualify_reason,
    }


@tool
def compare_sites(coords: list[dict]) -> list[dict]:
    """Evaluate each {lat, lon} dict and return results sorted by composite score."""
    results = [evaluate_site.invoke({'lat': c['lat'], 'lon': c['lon']}) for c in coords]
    return sorted(results, key=lambda x: x['composite'], reverse=True)


@tool
def get_news_digest() -> list[dict]:
    """Return cached BTM energy news headlines (title, url, snippet)."""
    cache = _get_news_cache()
    return cache.get('items', [])


@tool
def get_lmp_forecast(node: str = 'HB_WEST', horizon: int = 72) -> dict:
    """Return P10/P50/P90 LMP forecast array for an ERCOT/CAISO node."""
    from backend.scoring.power import get_forecast, HEAT_RATE, OM_COST
    fc = get_forecast(node)
    waha = 1.84
    btm_cost = waha * HEAT_RATE + OM_COST
    if fc is not None:
        h = min(horizon, len(fc['p50']))
        p50 = fc['p50'][:h]
        p50_list = p50.tolist() if hasattr(p50, 'tolist') else list(p50)
        return {
            'node': node, 'horizon': h,
            'p50': p50_list,
            'spread_durability': float(fc['spread_durability']),
            'btm_cost_mwh': round(btm_cost, 2),
            'method': fc.get('method', 'cache'),
        }
    base = 42.0
    return {
        'node': node, 'horizon': horizon,
        'p50': [base] * horizon,
        'spread_durability': 0.60,
        'btm_cost_mwh': round(btm_cost, 2),
        'method': 'fallback',
    }


@tool
def run_monte_carlo(gas_price: float, lmp_p50: float, wacc: float = 0.08, years: int = 20) -> dict:
    """Run Monte Carlo NPV simulation. Returns P10/P50/P90 NPV in $M."""
    import numpy as np
    rng = np.random.default_rng(42)
    n = 10_000
    gas_samples = rng.normal(gas_price, gas_price * 0.20, n)
    lmp_samples = rng.normal(lmp_p50, lmp_p50 * 0.25, n)

    from backend.scoring.power import HEAT_RATE, OM_COST
    spread_samples = lmp_samples - (gas_samples * HEAT_RATE + OM_COST)

    annual_mwh = 100_000 * 8760   # 100MW × hours/year
    capex = 80.0                  # $M BTM capex
    annual_cf = spread_samples * annual_mwh / 1_000_000

    pv_factors = sum((1 / (1 + wacc) ** t) for t in range(1, years + 1))
    npv_samples = annual_cf * pv_factors - capex

    return {
        'npv_p10_m': round(float(np.percentile(npv_samples, 10)), 1),
        'npv_p50_m': round(float(np.percentile(npv_samples, 50)), 1),
        'npv_p90_m': round(float(np.percentile(npv_samples, 90)), 1),
        'gas_price': gas_price,
        'lmp_p50': lmp_p50,
        'wacc': wacc,
        'years': years,
    }


@tool
def web_search(query: str) -> str:
    """Search the web for current energy market news and policy. Returns formatted results."""
    key = _get_tavily_key()
    if not key:
        return "(web search unavailable — TAVILY_API_KEY not set)"
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        results = client.search(query, max_results=3)
        items = results.get('results', [])
        if not items:
            return f"No results found for: {query}"
        return '\n\n'.join(
            f"**{r['title']}**\n{r['content'][:300]}\nSource: {r['url']}"
            for r in items
        )
    except Exception as e:
        return f"(web search failed: {str(e)[:100]})"
