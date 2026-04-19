"""BTM Power Economics scorer.

BTM spread = LMP − (waha_price × 8.5 MMBtu/MWh + $3 O&M)
Loads Moirai forecast cache and spread durability model when available.
"""
from pathlib import Path
from backend.features.vector import FeatureVector
from backend.scoring.regime import RegimeState

HEAT_RATE = 8.5   # CCGT, must match sub_c.py
OM_COST   = 3.0   # $/MWh

_CACHE_PATH = Path('data/models/power_forecast_cache.pkl')
_DUR_PATH   = Path('data/models/power_durability.pkl')

_forecast_cache: dict | None = None
_dur_model = None
_dur_scaler = None


def _load_models():
    global _forecast_cache, _dur_model, _dur_scaler
    if _CACHE_PATH.exists() and _forecast_cache is None:
        import pickle
        with open(_CACHE_PATH, 'rb') as f:
            _forecast_cache = pickle.load(f)
    if _DUR_PATH.exists() and _dur_model is None:
        import pickle
        with open(_DUR_PATH, 'rb') as f:
            _dur_model, _dur_scaler = pickle.load(f)


def btm_spread(lmp_mwh: float, waha_price: float) -> float:
    return lmp_mwh - (waha_price * HEAT_RATE + OM_COST)


def get_forecast(node: str) -> dict | None:
    """Return cached forecast dict for a node, or None if cache not loaded."""
    _load_models()
    if _forecast_cache is None:
        return None
    return _forecast_cache.get(node) or _forecast_cache.get('HB_WEST')


def score_power(fv: FeatureVector, regime: RegimeState) -> dict:
    _load_models()
    btm_cost = fv.waha_price * HEAT_RATE + OM_COST

    # Use Moirai forecast cache when available
    fc = get_forecast(fv.ercot_node)
    if fc is not None:
        import numpy as np
        spread_p50 = float(np.mean(fc['p50'])) - btm_cost
        spread_durability = float(fc['spread_durability'])
    else:
        spread_p50 = btm_spread(fv.lmp_mwh, fv.waha_price)
        regime_durability = {'normal': 0.60, 'stress_scarcity': 0.75, 'wind_curtailment': 0.35}
        spread_durability = regime_durability.get(regime.label, 0.60)

    # Override durability with ML model when available
    if _dur_model is not None:
        import numpy as np
        regime_enc = {'normal': 0, 'stress_scarcity': 1, 'wind_curtailment': 2}
        X = _dur_scaler.transform([[
            fv.lmp_mwh, fv.waha_price,
            regime_enc.get(regime.label, 0),
            0.28,           # wind_pct (not in FeatureVector — use ERCOT average)
            55.0,           # demand_mw / 1000
        ]])
        spread_durability = float(_dur_model.predict_proba(X)[0, 1])

    spread_score = min(max(spread_p50 / 20.0, 0.0), 1.0)
    power_score  = round(spread_score * 0.60 + spread_durability * 0.40, 4)

    return {
        'power_score':       power_score,
        'spread_p50_mwh':    round(spread_p50, 2),
        'spread_durability': round(spread_durability, 3),
    }
