"""Monte Carlo 20-year BTM NPV estimator. 10,000 scenarios, <2s."""
import numpy as np
from backend.features.vector import FeatureVector
from backend.scoring.scorecard import CostEstimate

_LAND_COST = {'private': 2000, 'state': 800, 'blm_federal': 400}  # $/acre
_PIPELINE_COST_PER_MI = 1_200_000  # $/mile
_WATER_COST_PER_MI    = 400_000    # $/mile
_BTM_CAPEX_PER_KW     = 800        # $/kW

KM_PER_MILE = 1.60934
N_SCENARIOS = 10_000
YEARS = 20
MWH_PER_YEAR = 100 * 8760  # 100 MW × 8760 h


def estimate_costs(
    fv: FeatureVector,
    land_score: float,
    power_score: float,
    capacity_mw: float = 100.0,
    wacc: float = 0.08,
) -> CostEstimate:
    rng = np.random.default_rng(42)

    # ── Deterministic capex ───────────────────────────────────────────────
    land_cost_per_acre = _LAND_COST.get(fv.ownership_type, 2000)
    acres = 500.0  # standard 100 MW footprint
    land_m = (acres * land_cost_per_acre) / 1e6

    pipe_miles = fv.pipeline_km / KM_PER_MILE
    pipe_m = (pipe_miles * _PIPELINE_COST_PER_MI) / 1e6

    water_miles = fv.water_km / KM_PER_MILE
    water_m = (water_miles * _WATER_COST_PER_MI) / 1e6

    btm_m = (capacity_mw * 1000 * _BTM_CAPEX_PER_KW) / 1e6

    # ── Monte Carlo 20-year NPV ───────────────────────────────────────────
    gas_sigma = fv.waha_price * 0.30  # 30-day vol proxy: 30% of price
    lmp_sigma = fv.lmp_mwh * 0.20

    gas_paths = rng.normal(fv.waha_price, gas_sigma, (N_SCENARIOS, YEARS))
    lmp_paths = rng.normal(fv.lmp_mwh,   lmp_sigma, (N_SCENARIOS, YEARS))
    gas_paths = np.clip(gas_paths, 0.5, None)
    lmp_paths = np.clip(lmp_paths, 5.0, None)

    spreads = lmp_paths - (gas_paths * 8.5 + 3.0)
    annual_revenue = np.where(spreads > 0, spreads, 0) * MWH_PER_YEAR / 1e6  # $M/yr

    discount = np.array([(1 + wacc) ** (-y) for y in range(1, YEARS + 1)])
    npv = (annual_revenue * discount).sum(axis=1) - (land_m + pipe_m + water_m + btm_m)

    return CostEstimate(
        land_acquisition_m=round(land_m, 2),
        pipeline_connection_m=round(pipe_m, 2),
        water_connection_m=round(water_m, 2),
        btm_capex_m=round(btm_m, 2),
        npv_p10_m=round(float(np.percentile(npv, 10)), 2),
        npv_p50_m=round(float(np.percentile(npv, 50)), 2),
        npv_p90_m=round(float(np.percentile(npv, 90)), 2),
        wacc=wacc,
        capacity_mw=capacity_mw,
    )
