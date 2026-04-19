"""Tools available to the LangGraph site-analysis agent."""
from langchain_core.tools import tool
from backend.pipeline.evaluate import evaluate_coordinate
from backend.scoring.cost import estimate_costs


@tool
def evaluate_site(lat: float, lon: float) -> dict:
    """Evaluate a (lat, lon) coordinate and return its full scorecard."""
    sc = evaluate_coordinate(lat, lon)
    return {
        'lat': sc.lat, 'lon': sc.lon,
        'composite': sc.composite_score,
        'land': sc.land_score, 'gas': sc.gas_score, 'power': sc.power_score,
        'npv_p50': sc.cost.npv_p50_m if sc.cost else 0,
        'disqualified': sc.hard_disqualified,
        'reason': sc.disqualify_reason,
    }


@tool
def compare_sites(coords: list[dict]) -> list[dict]:
    """Run evaluate_site for each {lat, lon} dict in coords and return sorted results."""
    results = [evaluate_site.invoke({'lat': c['lat'], 'lon': c['lon']}) for c in coords]
    return sorted(results, key=lambda x: x['composite'], reverse=True)
