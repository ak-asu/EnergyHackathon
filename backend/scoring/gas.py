"""Gas Supply Reliability scorer.

Inputs come from FeatureVector (no full object needed — just the 3 key fields).
Loads KDE model from data/models/gas_kde.pkl when available.
"""
from pathlib import Path

_KDE_PATH = Path('data/models/gas_kde.pkl')

_INCIDENT_WEIGHT = 0.40
_PIPELINE_WEIGHT = 0.35
_WAHA_WEIGHT     = 0.25


def score_gas(
    incident_density: float,
    interstate_pipeline_km: float,
    waha_distance_km: float,
) -> float:
    """Return gas reliability score 0–1.

    Args:
        incident_density: PHMSA KDE density at coordinate (incidents/km²)
        interstate_pipeline_km: distance to nearest interstate pipeline
        waha_distance_km: distance to Waha Hub (supply security proxy)
    """
    if _KDE_PATH.exists():
        import pickle
        with open(_KDE_PATH, 'rb') as f:
            kde = pickle.load(f)
        import numpy as np
        density = float(kde.score_samples([[0.0, 0.0]])[0])  # placeholder: use lat/lon
        incident_score = max(0.0, 1.0 - min(density * 50, 1.0))
    else:
        incident_score = max(0.0, 1.0 - min(incident_density * 200, 1.0))

    pipeline_score = max(0.0, 1.0 - interstate_pipeline_km / 100.0)
    waha_score     = max(0.0, 1.0 - waha_distance_km / 400.0)

    raw = (
        incident_score * _INCIDENT_WEIGHT +
        pipeline_score * _PIPELINE_WEIGHT +
        waha_score     * _WAHA_WEIGHT
    )
    return round(min(max(raw, 0.0), 1.0), 4)
