"""Land & Lease Viability scorer for arbitrary coordinates.

Baseline: rule-based weighted formula with SHAP-style per-feature attribution.
Upgrade: loads LightGBM model from data/models/land_lgbm.pkl when available.
"""
from pathlib import Path
from backend.features.vector import FeatureVector, DISQUALIFY_FEMA, MIN_ACRES

_WEIGHTS = {
    'water':      0.15,
    'fiber':      0.12,
    'pipeline':   0.10,
    'substation': 0.08,
    'highway':    0.07,
    'ownership':  0.18,
    'fema':       0.10,
    'seismic':    0.08,
    'wildfire':   0.07,
    'epa':        0.05,
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 0.001

_FEMA_SCORES = {'X': 1.0, 'X500': 0.7, 'D': 0.4, 'A': 0.0, 'AE': 0.0, 'V': 0.0}
_OWNERSHIP_SCORES = {'private': 1.0, 'state': 0.6, 'blm_federal': 0.3}

_MODEL_PATH = Path('data/models/land_lgbm.pkl')


def check_hard_disqualifiers(fv: FeatureVector) -> str | None:
    if fv.fema_zone in DISQUALIFY_FEMA:
        return f"FEMA flood zone {fv.fema_zone} — unbuildable"
    if fv.is_federal_wilderness:
        return "Federal wilderness designation — no development permitted"
    if fv.acres_available < MIN_ACRES:
        return f"Only {fv.acres_available:.0f} contiguous acres — minimum {MIN_ACRES:.0f} required"
    return None


def _rule_based(fv: FeatureVector) -> tuple[float, dict[str, float]]:
    raw = {
        'water':      max(0.0, 1.0 - fv.water_km / 15.0),
        'fiber':      max(0.0, 1.0 - fv.fiber_km / 10.0),
        'pipeline':   max(0.0, 1.0 - fv.pipeline_km / 20.0),
        'substation': max(0.0, 1.0 - fv.substation_km / 25.0),
        'highway':    max(0.0, 1.0 - fv.highway_km / 15.0),
        'ownership':  _OWNERSHIP_SCORES.get(fv.ownership_type, 0.5),
        'fema':       _FEMA_SCORES.get(fv.fema_zone, 0.4),
        'seismic':    1.0 - fv.seismic_hazard,
        'wildfire':   1.0 - fv.wildfire_risk,
        'epa':        1.0 if fv.epa_attainment else 0.5,
    }
    shap = {k: round(raw[k] * _WEIGHTS[k], 5) for k in raw}
    score = round(min(max(sum(shap.values()), 0.0), 1.0), 4)
    return score, shap


def score_land(fv: FeatureVector) -> tuple[float, dict[str, float]]:
    """Return (land_score, shap_dict). Loads LightGBM model if available."""
    if _MODEL_PATH.exists():
        import pickle
        import numpy as np
        with open(_MODEL_PATH, 'rb') as f:
            model, scaler = pickle.load(f)
        features = np.array([[
            fv.water_km, fv.fiber_km, fv.pipeline_km, fv.substation_km,
            fv.highway_km, _OWNERSHIP_SCORES.get(fv.ownership_type, 0.5),
            _FEMA_SCORES.get(fv.fema_zone, 0.4),
            fv.seismic_hazard, fv.wildfire_risk, float(fv.epa_attainment),
        ]])
        X = scaler.transform(features)
        score = float(model.predict_proba(X)[0, 1])
        shap_path = _MODEL_PATH.with_suffix('.shap.pkl')
        if shap_path.exists():
            with open(shap_path, 'rb') as f:
                explainer = pickle.load(f)
            sv = explainer.shap_values(X)[0]
            keys = ['water', 'fiber', 'pipeline', 'substation', 'highway',
                    'ownership', 'fema', 'seismic', 'wildfire', 'epa']
            shap = {k: round(float(v), 5) for k, v in zip(keys, sv)}
        else:
            _, shap = _rule_based(fv)
        return round(min(max(score, 0.0), 1.0), 4), shap
    return _rule_based(fv)
