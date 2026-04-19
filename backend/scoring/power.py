"""BTM Power Economics scorer.

BTM spread = LMP − (waha_price × 8.5 MMBtu/MWh + $3 O&M)
Positive spread → generate from gas; negative → import from grid.
"""
from backend.features.vector import FeatureVector
from backend.scoring.regime import RegimeState

HEAT_RATE = 8.5   # CCGT, must match sub_c.py
OM_COST   = 3.0   # $/MWh


def btm_spread(lmp_mwh: float, waha_price: float) -> float:
    return lmp_mwh - (waha_price * HEAT_RATE + OM_COST)


def score_power(fv: FeatureVector, regime: RegimeState) -> dict:
    spread = btm_spread(fv.lmp_mwh, fv.waha_price)

    # Regime adjusts expected spread durability
    regime_durability = {'normal': 0.60, 'stress_scarcity': 0.75, 'wind_curtailment': 0.35}
    spread_durability = regime_durability.get(regime.label, 0.60)

    # Score: $20/MWh positive spread = 1.0; negative = 0
    spread_score     = min(max(spread / 20.0, 0.0), 1.0)
    durability_score = spread_durability

    power_score = round(spread_score * 0.60 + durability_score * 0.40, 4)

    return {
        'power_score':       power_score,
        'spread_p50_mwh':    round(spread, 2),
        'spread_durability': round(spread_durability, 3),
    }
